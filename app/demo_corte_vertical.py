"""Demo de punta a punta de Firebox (corte vertical para el pitch del 05-oct-2026).

Una compra de un reloj → factura electrónica validada en Factus v2 → recaudo con QR en Factus Pay → un solo PDF
(factura + "Paga aquí") enviado por WhatsApp → vigilancia del pago → confirmación por WhatsApp.

Uso:
    python demo_corte_vertical.py --para 573001234567           # demo completa
    python demo_corte_vertical.py --sin-whatsapp                 # solo Factus + Factus Pay + PDF (guarda en salida/)
Requisito para --para: ese número debe haber escrito a Firebox (+57 324 350 2241) en las últimas 24 h.
"""
import argparse
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from firebox.canal.whatsapp import CanalWhatsApp
from firebox.dinero import Linea, calcular, en_texto
from firebox.documentos.pdf import pagina_pago, unir
from firebox.facturacion.factus import ClienteFactus, ErrorFactus, cuerpo_factura
from firebox.pagos.factus_pay import ClienteFactusPay, monto_permitido

TIENDA = "Relojes NovaMarket"
PRODUCTO = Linea("REL-8314", "Reloj Curren 8314 negro", 1, Decimal("169900"), Decimal("19"))
SALIDA = Path(__file__).parent / "salida"


def paso(texto: str, inicio: float) -> None:
    print(f"[{time.time() - inicio:6.1f} s] {texto}", flush=True)


def main() -> int:
    args = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    args.add_argument("--para", help="número de WhatsApp del cliente, solo dígitos con 57 (ej. 573001234567)")
    args.add_argument("--sin-whatsapp", action="store_true", help="no envía nada por WhatsApp")
    args.add_argument("--espera", type=int, default=10, help="minutos vigilando el pago (por defecto 10)")
    a = args.parse_args()
    if not a.sin_whatsapp and not a.para:
        args.error("indica --para o usa --sin-whatsapp")

    inicio = time.time()
    lineas = [PRODUCTO]
    totales = calcular(lineas)
    paso(f"Carrito: {PRODUCTO.cantidad} × {PRODUCTO.nombre} | subtotal {en_texto(totales.subtotal)} + IVA "
         f"{en_texto(totales.iva)} = TOTAL {en_texto(totales.total)}", inicio)
    if not monto_permitido(totales.total):
        paso("El total está fuera del rango de Factus Pay: no se factura.", inicio)
        return 1

    factus = ClienteFactus.desde_entorno()
    rango = factus.rango_factura_de_venta()
    referencia = f"FB-DEMO-{datetime.now():%Y%m%d%H%M%S}"
    manana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        factura = factus.emitir_factura(cuerpo_factura(referencia, rango, lineas, totales.total, credito=True, vence=manana))
    except ErrorFactus as e:
        if e.estado != 422:
            raise
        paso(f"Factus rechazó la factura a crédito ({e.detalle}); se reintenta de contado.", inicio)
        factura = factus.emitir_factura(cuerpo_factura(referencia, rango, lineas, totales.total, credito=False))
    paso(f"Factura {factura.numero} emitida | validada DIAN: {factura.validada} | CUFE: {(factura.cufe or '')[:16]}…", inicio)
    if factura.total != totales.total:
        paso(f"ALTO: total de Factus {factura.total} ≠ total calculado {totales.total}. No se cobra.", inicio)
        return 1

    pdf_factura = factus.descargar_pdf(factura.numero)
    paso(f"PDF de la factura descargado ({len(pdf_factura) // 1024} KB)", inicio)

    pay = ClienteFactusPay.desde_entorno()
    recaudo = pay.crear_recaudo(factura.numero, factura.total)
    paso(f"Recaudo en Factus Pay: referencia {recaudo.referencia} | {en_texto(recaudo.monto)} | estado {recaudo.estado}", inicio)

    vence = (datetime.now() + timedelta(hours=24)).strftime("%d/%m/%Y %I:%M %p")
    documento = unir(pdf_factura, pagina_pago(TIENDA, factura.numero, en_texto(factura.total), recaudo.qr_png, vence))
    SALIDA.mkdir(exist_ok=True)
    ruta = SALIDA / f"Factura-{factura.numero}.pdf"
    ruta.write_bytes(documento)
    (SALIDA / f"QR-{factura.numero}.png").write_bytes(recaudo.qr_png)
    paso(f"Documento único (factura + Paga aquí) guardado en {ruta}", inicio)

    canal = None
    if not a.sin_whatsapp:
        canal = CanalWhatsApp.desde_entorno()
        canal.enviar_texto(a.para, f"🧾 ¡Gracias por tu compra en {TIENDA}!\nTu factura electrónica *{factura.numero}* "
                                   f"por *{en_texto(factura.total)}* está lista y validada ante la DIAN.")
        canal.enviar_documento(a.para, canal.subir_medio(documento, "application/pdf", ruta.name), ruta.name,
                               "Tu factura con la página de pago incluida")
        canal.enviar_imagen(a.para, canal.subir_medio(recaudo.qr_png, "image/png", f"QR-{factura.numero}.png"),
                            f"Escanea este QR con la app de tu banco (Bre-B) para pagar {en_texto(factura.total)}.")
        paso("Factura, PDF y QR enviados por WhatsApp", inicio)

    paso(f"Vigilando el pago (cada 5 s, hasta {a.espera} min). Paga el QR en el simulador de Factus Pay…", inicio)
    limite = time.time() + a.espera * 60
    while time.time() < limite:
        estado = pay.consultar(recaudo.referencia).estado
        if estado == "paid":
            paso(f"✅ PAGADO: factura {factura.numero}", inicio)
            if canal:
                canal.enviar_texto(a.para, f"✅ Pago recibido. Tu factura *{factura.numero}* quedó pagada.\n"
                                           f"¡Gracias por comprar en {TIENDA}!")
                paso("Confirmación enviada por WhatsApp", inicio)
            return 0
        time.sleep(5)
    paso("Se acabó el tiempo de espera sin pago.", inicio)
    return 2


if __name__ == "__main__":
    sys.exit(main())
