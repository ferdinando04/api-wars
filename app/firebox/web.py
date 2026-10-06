"""Servidor de Firebox: panel del vendedor (Jinja2 + HTMX) y API documentada en /docs.

El panel lee las ventas en vivo de Factus Pay (cada recaudo lleva como referencia el número de su factura), suma con Decimal y
descarga el PDF de cada factura desde Factus. "Nueva venta de prueba" corre la venta completa de `ventas.py` en segundo plano.

Arranque (solo en este equipo):  uvicorn firebox.web:app --host 127.0.0.1 --port 8800
Clave del panel: PANEL_USUARIO / PANEL_CLAVE en el .env.
"""
import re
import secrets
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

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
_pay: ClienteFactusPay | None = None
_factus: ClienteFactus | None = None
_detalles: dict[str, dict] = {}  # una factura validada no cambia: se consulta una sola vez (límite de Factus: 80/min)


def cliente_pay() -> ClienteFactusPay:
    global _pay
    if _pay is None:
        _pay = ClienteFactusPay.desde_entorno()
    return _pay


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
                _detalles[n] = {"cufe": d.get("cufe") or "", "validada": bool(d.get("is_validated")), "validada_en": d.get("validated_at") or ""}
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


@dataclass(frozen=True)
class Resumen:
    ventas: int
    facturado: Decimal
    cobrado: Decimal
    pendiente: Decimal


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
                          d.get("cufe", ""), d.get("validada", False)))
    facturado = sum((f.monto for f in filas), CERO)
    cobrado = sum((f.monto for f in filas if f.clase == "pagado"), CERO)
    pendiente = sum((f.monto for f in filas if f.clase == "pendiente"), CERO)
    return filas, Resumen(len(filas), facturado, cobrado, pendiente)


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
        filas, resumen, error = [], Resumen(0, CERO, CERO, CERO), f"No se pudo leer Factus Pay: {type(e).__name__}"
    return plantillas.TemplateResponse(request, "_tabla.html", {"filas": filas, "r": resumen, "error": error,
                                                                "hora": datetime.now(BOGOTA).strftime("%I:%M:%S %p")})


@app.get("/panel/actividad", response_class=HTMLResponse, include_in_schema=False)
def actividad(request: Request, _: str = Depends(exigir_sesion)):
    return plantillas.TemplateResponse(request, "_actividad.html", {"actividad": list(ACTIVIDAD)})


@app.get("/panel/factura/{numero}.pdf", include_in_schema=False)
def factura_pdf(numero: str, _: str = Depends(exigir_sesion)) -> Response:
    if not NUMERO_FACTURA.match(numero):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Número de factura inválido")
    pdf = ClienteFactus.desde_entorno().descargar_pdf(numero)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="Factura-{numero}.pdf"'})


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
