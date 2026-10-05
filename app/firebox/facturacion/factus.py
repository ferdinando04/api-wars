"""Cliente de la API de Factus v2 (facturación electrónica DIAN).

Contratos medidos el 05-oct-2026 (ver docs/documentacion/07_Integraciones_Conexiones.md §5):
- OAuth2 `password` en form-urlencoded, token de 3600 s.
- User-Agent propio obligatorio (sin él: 403 de Cloudflare).
- Rango de Factura de Venta activo: documento "Factura de Venta" (prefijo SETP en sandbox).
- PDF: GET /v2/bills/{numero}/download-pdf → {file_name, pdf_base_64_encoded}.
"""
import base64
import time
from dataclasses import dataclass
from decimal import Decimal

import httpx

from firebox.config import USER_AGENT, requerido
from firebox.dinero import Linea


class ErrorFactus(Exception):
    def __init__(self, estado: int, detalle):
        super().__init__(f"Factus respondió {estado}: {detalle}")
        self.estado = estado
        self.detalle = detalle


@dataclass(frozen=True)
class FacturaEmitida:
    numero: str
    cufe: str | None
    total: Decimal
    validada: bool
    notificaciones: list
    crudo: dict


class ClienteFactus:
    def __init__(self, base_url: str, client_id: str, client_secret: str, usuario: str, clave: str):
        self._base = base_url.rstrip("/")
        self._credenciales = {"client_id": client_id, "client_secret": client_secret,
                              "username": usuario, "password": clave}
        self._token: str | None = None
        self._vence = 0.0
        self._http = httpx.Client(timeout=60, headers={"Accept": "application/json", "User-Agent": USER_AGENT})

    @classmethod
    def desde_entorno(cls) -> "ClienteFactus":
        return cls(requerido("FACTUS_BASE_URL"), requerido("FACTUS_CLIENT_ID"), requerido("FACTUS_CLIENT_SECRET"),
                   requerido("FACTUS_USERNAME"), requerido("FACTUS_PASSWORD"))

    def _obtener_token(self) -> str:
        if self._token and time.time() < self._vence - 60:
            return self._token
        r = self._http.post(f"{self._base}/oauth/token", data={"grant_type": "password", **self._credenciales})
        if r.status_code != 200:
            raise ErrorFactus(r.status_code, "no se pudo obtener el token")
        datos = r.json()
        self._token, self._vence = datos["access_token"], time.time() + int(datos.get("expires_in", 3600))
        return self._token

    def _pedir(self, metodo: str, ruta: str, **kwargs) -> dict:
        for intento in range(2):
            r = self._http.request(metodo, f"{self._base}{ruta}",
                                   headers={"Authorization": f"Bearer {self._obtener_token()}"}, **kwargs)
            if r.status_code == 401 and intento == 0:
                self._token = None  # token vencido: renovar y reintentar una vez
                continue
            if r.status_code >= 400:
                try:
                    detalle = r.json()
                except ValueError:
                    detalle = r.text[:300]
                raise ErrorFactus(r.status_code, detalle)
            return r.json()
        raise ErrorFactus(401, "token rechazado dos veces")

    def rango_factura_de_venta(self) -> int:
        datos = self._pedir("GET", "/v2/numbering-ranges")["data"]
        rangos = datos.get("data", datos) if isinstance(datos, dict) else datos
        for rango in rangos:
            if rango.get("document") == "Factura de Venta" and rango.get("is_active"):
                return int(rango["id"])
        raise ErrorFactus(404, "no hay un rango activo de Factura de Venta")

    def emitir_factura(self, cuerpo: dict) -> FacturaEmitida:
        datos = self._pedir("POST", "/v2/bills/validate", json=cuerpo)["data"]
        factura = datos.get("bill") or datos
        totales = factura.get("totals") or {}
        total = totales.get("total", factura.get("total"))
        return FacturaEmitida(
            numero=factura["number"],
            cufe=factura.get("cufe"),
            total=Decimal(str(total)),
            validada=bool(factura.get("is_validated", datos.get("is_validated"))),
            notificaciones=factura.get("errors") or datos.get("errors") or [],
            crudo=datos,
        )

    def descargar_pdf(self, numero: str) -> bytes:
        datos = self._pedir("GET", f"/v2/bills/{numero}/download-pdf")["data"]
        return base64.b64decode(datos["pdf_base_64_encoded"])


def cuerpo_factura(referencia: str, rango_id: int, lineas: list[Linea], total: Decimal, credito: bool = True,
                   vence: str | None = None) -> dict:
    """Factura estándar a consumidor final (cliente exactamente como el ejemplo oficial de Factus v2)."""
    pago = {"payment_form": "2" if credito else "1", "payment_method_code": "47", "amount": f"{total:.2f}"}
    if credito:
        pago["due_date"] = vence
    return {
        "numbering_range_id": rango_id,
        "document": "01",
        "operation_type": "10",
        "reference_code": referencia,
        "observation": "Compra por WhatsApp en Firebox",
        "payment_details": [pago],
        "customer": {"identification_document_code": "13", "identification": "22222222222", "names": "Consumidor Final"},
        "items": [
            {
                "code_reference": l.referencia,
                "name": l.nombre,
                "quantity": f"{l.cantidad}.00",
                "discount_rate": "0.00",
                "price": f"{l.precio_sin_iva:.2f}",
                "unit_measure_code": "94",
                "standard_code": "999",
                "taxes": [{"code": "01", "rate": "0.00", "is_excluded": True}] if l.excluida
                else [{"code": "01", "rate": f"{l.tarifa_iva:.2f}"}],
            }
            for l in lineas
        ],
    }
