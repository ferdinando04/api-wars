"""Servidor de Firebox: panel del vendedor (Jinja2 + HTMX) y API documentada en /docs.

El panel lee las ventas en vivo de Factus Pay (cada recaudo lleva como referencia el número de su factura), completa cada fila con
el detalle de la factura en Factus (CUFE, IVA, cliente, fecha de validación), suma con Decimal, vigila el estado de las tres
conexiones (Factus, Factus Pay, WhatsApp) y permite descargar PDF/XML, ver el QR, consultar un pago al instante, exportar CSV y
lanzar una venta de prueba completa.

Arranque (solo en este equipo):  uvicorn firebox.web:app --host 127.0.0.1 --port 8800
Clave del panel: PANEL_USUARIO / PANEL_CLAVE en el .env.
"""
import csv
import io
import re
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from firebox.canal.whatsapp import CanalWhatsApp
from firebox.config import entorno
from firebox.dinero import CERO, Linea, en_texto
from firebox.facturacion.factus import ClienteFactus
from firebox.pagos.factus_pay import ClienteFactusPay

app = FastAPI(title="Firebox", description="Tienda en WhatsApp con factura electrónica (Factus v2) y cobro con QR (Factus Pay).")
plantillas = Jinja2Templates(directory=str(Path(__file__).parent / "panel" / "plantillas"))
plantillas.env.filters["pesos"] = en_texto

BOGOTA = timezone(timedelta(hours=-5))
ESTADOS = {"paid": ("Pagado", "pagado"), "ready": ("Esperando pago", "pendiente"), "started": ("Creando QR", "pendiente"),
           "failed": ("Fallido", "fallido"), "rejected": ("Rechazado", "fallido")}
NUMERO_FACTURA = re.compile(r"^[A-Z]{1,6}\d{1,15}$")
NUMERO_WHATSAPP = re.compile(r"^57\d{10}$")
TIENDA = "Relojes NovaMarket"
PRODUCTO_DEMO = Linea("REL-8314", "Reloj Curren 8314 negro", 1, Decimal("169900"), Decimal("19"))

# --- sesión del panel (HTTP Basic con la clave del .env) ---
_seguridad = HTTPBasic()


def credenciales_panel() -> tuple[str, str]:
    e = entorno()
    return e.get("PANEL_USUARIO", "firebox"), e.get("PANEL_CLAVE", "")


def exigir_sesion(c: HTTPBasicCredentials = Depends(_seguridad)) -> str:
    usuario, clave = credenciales_panel()
    ok = bool(clave) and secrets.compare_digest(c.username.encode(), usuario.encode()) and secrets.compare_digest(
        c.password.encode(), clave.encode())
    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario o clave incorrectos", headers={"WWW-Authenticate": "Basic"})
    return c.username


# --- clientes (se reemplazan en las pruebas) ---
_detalles: dict[str, dict] = {}  # una factura validada no cambia: se consulta una sola vez (límite de Factus: 80/min)


def cliente_pay() -> ClienteFactusPay:
    return ClienteFactusPay.desde_entorno()  # la sesión compartida: cada /auth invalida el token anterior (medido 06-oct)


_factus: ClienteFactus | None = None


def cliente_factus() -> ClienteFactus:
    global _factus
    if _factus is None:
        _factus = ClienteFactus.desde_entorno()
    return _factus


def detalles_de(factus: ClienteFactus, numeros: list[str]) -> dict[str, dict]:
    for n in numeros:
        if n not in _detalles and NUMERO_FACTURA.match(n):
            try:
                d = factus.ver_factura(n)
                tot = d.get("totals") or {}
                _detalles[n] = {"cufe": d.get("cufe") or "", "validada": bool(d.get("is_validated")), "validada_en": d.get("validated_at") or "",
                                "iva": tot.get("tax_amount", "0"), "cliente": (d.get("customer") or {}).get("names") or "",
                                "url": (d.get("links") or {}).get("public_url") or ""}
            except Exception:
                continue  # sin detalle se muestra la fila igual; se reintenta en la próxima actualización
    return {n: _detalles[n] for n in numeros if n in _detalles}


# --- resumen de ventas ---
@dataclass(frozen=True)
class Fila:
    referencia: str
    monto: Decimal
    estado: str
    clase: str
    fecha: str
    cufe: str = ""
    validada: bool = False
    iva: Decimal = CERO
    cliente: str = ""
    url: str = ""


@dataclass(frozen=True)
class Resumen:
    ventas: int
    facturado: Decimal
    cobrado: Decimal
    pendiente: Decimal
    iva: Decimal = CERO
    pagadas: int = 0
    por_cobrar: int = 0

    @property
    def tasa_cobro(self) -> int:
        """% del valor facturado que ya se cobró (entero, redondeo bancario)."""
        if not self.facturado:
            return 0
        return int((self.cobrado * 100 / self.facturado).quantize(Decimal("1"), rounding=ROUND_HALF_EVEN))

    @property
    def ticket_promedio(self) -> Decimal:
        return (self.facturado / self.ventas).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN) if self.ventas else CERO


def _fecha(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(BOGOTA).strftime("%d/%m %I:%M %p")
    except ValueError:
        return iso


def _fecha_factus(texto: str) -> str:
    """'05-10-2026 12:46:07 PM' (hora de Bogotá, como la entrega Factus) → '05/10 12:46 PM'."""
    try:
        return datetime.strptime(texto, "%d-%m-%Y %I:%M:%S %p").strftime("%d/%m %I:%M %p")
    except ValueError:
        return texto


def resumir(recaudos: list[dict], detalles: dict[str, dict] | None = None) -> tuple[list[Fila], Resumen]:
    detalles = detalles or {}
    filas = []
    # la factura más reciente arriba: los números de factura son consecutivos (la fecha de Factus Pay sale fija en el sandbox)
    for r in sorted(recaudos, key=lambda x: x.get("reference_code", ""), reverse=True):
        estado, clase = ESTADOS.get(r.get("status", ""), (r.get("status", "?"), "pendiente"))
        d = detalles.get(r["reference_code"], {})
        fecha = _fecha_factus(d["validada_en"]) if d.get("validada_en") else _fecha(r.get("created_at", ""))
        filas.append(Fila(r["reference_code"], Decimal(str(r["amount"])).quantize(Decimal("0.01")), estado, clase, fecha,
                          d.get("cufe", ""), d.get("validada", False), Decimal(str(d.get("iva", "0"))), d.get("cliente", ""), d.get("url", "")))
    facturado = sum((f.monto for f in filas), CERO)
    cobrado = sum((f.monto for f in filas if f.clase == "pagado"), CERO)
    pendiente = sum((f.monto for f in filas if f.clase == "pendiente"), CERO)
    iva = sum((f.iva for f in filas), CERO)
    return filas, Resumen(len(filas), facturado, cobrado, pendiente, iva,
                          sum(1 for f in filas if f.clase == "pagado"), sum(1 for f in filas if f.clase == "pendiente"))


# --- actividad de las ventas de prueba (en memoria, para mostrar el paso a paso en el panel) ---
ACTIVIDAD: deque[tuple[str, str]] = deque(maxlen=14)


def _anotar(texto: str) -> None:
    ACTIVIDAD.appendleft((datetime.now(BOGOTA).strftime("%I:%M:%S %p"), texto.replace(str(Path.cwd()), "")))


def _venta_en_segundo_plano(para: str) -> None:
    from firebox.ventas import VentaRechazada, vender, vigilar
    try:
        venta = vender([PRODUCTO_DEMO], TIENDA, para=para, avisar=_anotar)
        vigilar(venta, para=para, minutos=10, avisar=_anotar)
    except VentaRechazada as e:
        _anotar(f"Venta rechazada: {e}")
    except Exception as e:  # el panel muestra el error; nunca un secreto (los clientes no los incluyen en sus mensajes)
        _anotar(f"Error: {type(e).__name__}: {str(e)[:160]}")


# --- estado de las conexiones (se mide de verdad: una llamada liviana a cada API, con su tiempo) ---
def _medir(nombre: str, funcion) -> dict:
    inicio = time.perf_counter()
    try:
        detalle = funcion()
        return {"nombre": nombre, "ok": True, "ms": round((time.perf_counter() - inicio) * 1000), "detalle": detalle}
    except Exception as e:
        return {"nombre": nombre, "ok": False, "ms": round((time.perf_counter() - inicio) * 1000), "detalle": f"{type(e).__name__}: {str(e)[:90]}"}


def medir_conexiones() -> list[dict]:
    def factus():
        return f"rango de facturas {cliente_factus().rango_factura_de_venta()} activo · token OAuth vigente"

    def pay():
        return f"{len(cliente_pay().listar())} recaudos en la cuenta · sesión única"

    def whatsapp():
        e = CanalWhatsApp.desde_entorno().estado_numero()
        return f"{e.get('display_phone_number')} · {e.get('status')} · {e.get('platform_type')} · nombre {e.get('name_status')}"

    return [_medir("Factus API v2", factus), _medir("Factus Pay", pay), _medir("WhatsApp Cloud API", whatsapp)]


# --- rutas ---
@app.get("/", include_in_schema=False)
def inicio() -> RedirectResponse:
    return RedirectResponse("/panel")


@app.get("/salud", tags=["sistema"])
def salud() -> dict:
    return {"ok": True}


@app.get("/panel", response_class=HTMLResponse, include_in_schema=False)
def panel(request: Request, _: str = Depends(exigir_sesion)):
    return plantillas.TemplateResponse(request, "panel.html", {"tienda": TIENDA, "producto": PRODUCTO_DEMO})


@app.get("/panel/tabla", response_class=HTMLResponse, include_in_schema=False)
def tabla(request: Request, _: str = Depends(exigir_sesion), pay: ClienteFactusPay = Depends(cliente_pay),
          factus: ClienteFactus = Depends(cliente_factus)):
    try:
        recaudos = pay.listar()
        filas, resumen = resumir(recaudos, detalles_de(factus, [r["reference_code"] for r in recaudos]))
        error = None
    except Exception as e:
        filas, resumen, error = [], Resumen(0, CERO, CERO, CERO), f"No se pudo leer Factus Pay: {type(e).__name__} {getattr(e, 'estado', '')}"
    return plantillas.TemplateResponse(request, "_tabla.html", {"filas": filas, "r": resumen, "error": error,
                                                                "hora": datetime.now(BOGOTA).strftime("%I:%M:%S %p")})


@app.get("/panel/conexiones", response_class=HTMLResponse, include_in_schema=False)
def conexiones(request: Request, _: str = Depends(exigir_sesion)):
    return plantillas.TemplateResponse(request, "_conexiones.html", {"conexiones": medir_conexiones(),
                                                                     "hora": datetime.now(BOGOTA).strftime("%I:%M:%S %p")})


@app.get("/panel/actividad", response_class=HTMLResponse, include_in_schema=False)
def actividad(request: Request, _: str = Depends(exigir_sesion)):
    return plantillas.TemplateResponse(request, "_actividad.html", {"actividad": list(ACTIVIDAD)})


def _validar_numero(numero: str) -> str:
    if not NUMERO_FACTURA.match(numero):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Número de factura inválido")
    return numero


@app.get("/panel/factura/{numero}.pdf", include_in_schema=False)
def factura_pdf(numero: str, _: str = Depends(exigir_sesion)) -> Response:
    pdf = cliente_factus().descargar_pdf(_validar_numero(numero))
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="Factura-{numero}.pdf"'})


@app.get("/panel/factura/{numero}.xml", include_in_schema=False)
def factura_xml(numero: str, _: str = Depends(exigir_sesion)) -> Response:
    xml = cliente_factus().descargar_xml(_validar_numero(numero))
    return Response(xml, media_type="application/xml", headers={"Content-Disposition": f'attachment; filename="Factura-{numero}.xml"'})


@app.get("/panel/qr/{numero}.png", include_in_schema=False)
def qr(numero: str, _: str = Depends(exigir_sesion)) -> Response:
    recaudo = cliente_pay().consultar(_validar_numero(numero))
    if not recaudo.qr_png:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese recaudo no tiene QR")
    return Response(recaudo.qr_png, media_type="image/png")


@app.post("/panel/consultar/{numero}", response_class=HTMLResponse, include_in_schema=False)
def consultar(numero: str, _: str = Depends(exigir_sesion)):
    inicio = time.perf_counter()
    recaudo = cliente_pay().consultar(_validar_numero(numero))
    estado, clase = ESTADOS.get(recaudo.estado, (recaudo.estado, "pendiente"))
    ms = round((time.perf_counter() - inicio) * 1000)
    return HTMLResponse(f'<div class="aviso ok">{numero}: <b>{estado}</b> · {en_texto(recaudo.monto)} · consultado en Factus Pay en {ms} ms</div>')


@app.get("/panel/ventas.csv", include_in_schema=False)
def ventas_csv(_: str = Depends(exigir_sesion)) -> Response:
    recaudos = cliente_pay().listar()
    filas, _r = resumir(recaudos, detalles_de(cliente_factus(), [r["reference_code"] for r in recaudos]))
    salida = io.StringIO()
    w = csv.writer(salida, delimiter=";")
    w.writerow(["factura", "fecha", "estado", "cliente", "total", "iva", "cufe"])
    for f in filas:
        w.writerow([f.referencia, f.fecha, f.estado, f.cliente, f"{f.monto:.2f}", f"{f.iva:.2f}", f.cufe])
    return Response("﻿" + salida.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="firebox_ventas.csv"'})


@app.post("/panel/venta", response_class=HTMLResponse, include_in_schema=False)
def venta_de_prueba(para: str = Form(...), _: str = Depends(exigir_sesion)):
    para = re.sub(r"\D", "", para)
    if len(para) == 10:
        para = "57" + para
    if not NUMERO_WHATSAPP.match(para):
        return HTMLResponse('<div class="aviso error">Escribe un celular colombiano de 10 dígitos (ej. 3001234567).</div>', status_code=422)
    _anotar(f"Nueva venta de prueba para el WhatsApp …{para[-4:]}")
    threading.Thread(target=_venta_en_segundo_plano, args=(para,), daemon=True).start()
    return HTMLResponse('<div class="aviso ok">Venta en curso: mira la actividad y la tabla (se actualizan solas).</div>')
