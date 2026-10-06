"""Una venta de punta a punta: factura (Factus v2) → recaudo con QR (Factus Pay) → un solo PDF → WhatsApp → confirmación del pago.

La usan el script de demo y el botón "Nueva venta de prueba" del panel. `avisar` recibe cada paso en texto (para la terminal o el panel).
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import time

from firebox.canal.whatsapp import CanalWhatsApp
from firebox.dinero import Linea, calcular, en_texto
from firebox.documentos.pdf import pagina_pago, unir
from firebox.facturacion.factus import ClienteFactus, ErrorFactus, FacturaEmitida, cuerpo_factura
from firebox.pagos.factus_pay import ClienteFactusPay, Recaudo, monto_permitido

SALIDA = Path(__file__).resolve().parents[1] / "salida"
Aviso = Callable[[str], None]


class VentaRechazada(Exception):
    """La venta no se puede facturar (monto fuera del rango de Factus Pay o totales que no cuadran)."""


@dataclass(frozen=True)
class Venta:
    tienda: str
    factura: FacturaEmitida
    recaudo: Recaudo
    documento: Path


def vender(lineas: list[Linea], tienda: str, para: str | None = None, avisar: Aviso = lambda _: None) -> Venta:
    totales = calcular(lineas)
    avisar(f"Carrito: {' + '.join(f'{l.cantidad} × {l.nombre}' for l in lineas)} | subtotal {en_texto(totales.subtotal)} + IVA "
           f"{en_texto(totales.iva)} = TOTAL {en_texto(totales.total)}")
    if not monto_permitido(totales.total):
        raise VentaRechazada(f"El total {en_texto(totales.total)} está fuera del rango de Factus Pay: no se factura.")

    factus = ClienteFactus.desde_entorno()
    rango = factus.rango_factura_de_venta()
    referencia = f"FB-{datetime.now():%Y%m%d%H%M%S%f}"[:24]
    manana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        factura = factus.emitir_factura(cuerpo_factura(referencia, rango, lineas, totales.total, credito=True, vence=manana))
    except ErrorFactus as e:
        if e.estado != 422:
            raise
        avisar(f"Factus rechazó la factura a crédito ({e.detalle}); se reintenta de contado.")
        factura = factus.emitir_factura(cuerpo_factura(referencia, rango, lineas, totales.total, credito=False))
    avisar(f"Factura {factura.numero} emitida | validada DIAN: {factura.validada} | CUFE: {(factura.cufe or '')[:16]}…")
    if factura.total != totales.total:
        raise VentaRechazada(f"Total de Factus {factura.total} ≠ total calculado {totales.total}. No se cobra.")

    pdf_factura = factus.descargar_pdf(factura.numero)
    avisar(f"PDF de la factura descargado ({len(pdf_factura) // 1024} KB)")

    recaudo = ClienteFactusPay.desde_entorno().crear_recaudo(factura.numero, factura.total)
    avisar(f"Recaudo en Factus Pay: referencia {recaudo.referencia} | {en_texto(recaudo.monto)} | estado {recaudo.estado}")

    vence = (datetime.now() + timedelta(hours=24)).strftime("%d/%m/%Y %I:%M %p")
    documento = unir(pdf_factura, pagina_pago(tienda, factura.numero, en_texto(factura.total), recaudo.qr_png, vence))
    SALIDA.mkdir(exist_ok=True)
    ruta = SALIDA / f"Factura-{factura.numero}.pdf"
    ruta.write_bytes(documento)
    (SALIDA / f"QR-{factura.numero}.png").write_bytes(recaudo.qr_png)
    avisar(f"Documento único (factura + Paga aquí) guardado en {ruta}")

    if para:
        canal = CanalWhatsApp.desde_entorno()
        canal.enviar_texto(para, f"🧾 ¡Gracias por tu compra en {tienda}!\nTu factura electrónica *{factura.numero}* "
                                 f"por *{en_texto(factura.total)}* está lista y validada ante la DIAN.")
        canal.enviar_documento(para, canal.subir_medio(documento, "application/pdf", ruta.name), ruta.name,
                               "Tu factura con la página de pago incluida")
        canal.enviar_imagen(para, canal.subir_medio(recaudo.qr_png, "image/png", f"QR-{factura.numero}.png"),
                            f"Escanea este QR con la app de tu banco (Bre-B) para pagar {en_texto(factura.total)}.")
        avisar("Factura, PDF y QR enviados por WhatsApp")
    return Venta(tienda=tienda, factura=factura, recaudo=recaudo, documento=ruta)


def vigilar(venta: Venta, para: str | None = None, minutos: float = 10, cada: float = 5, avisar: Aviso = lambda _: None) -> bool:
    """Consulta el recaudo hasta que esté pagado (Factus Pay no tiene webhook). Devuelve True si se pagó a tiempo."""
    pay = ClienteFactusPay.desde_entorno()
    avisar(f"Vigilando el pago (cada {cada:g} s, hasta {minutos:g} min). Paga el QR en el simulador de Factus Pay…")
    limite = time.time() + minutos * 60
    while time.time() < limite:
        if pay.consultar(venta.recaudo.referencia).estado == "paid":
            avisar(f"✅ PAGADO: factura {venta.factura.numero}")
            if para:
                CanalWhatsApp.desde_entorno().enviar_texto(
                    para, f"✅ Pago recibido. Tu factura *{venta.factura.numero}* quedó pagada.\n¡Gracias por comprar en {venta.tienda}!")
                avisar("Confirmación enviada por WhatsApp")
            return True
        time.sleep(cada)
    avisar("Se acabó el tiempo de espera sin pago.")
    return False
