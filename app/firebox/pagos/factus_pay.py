"""Cliente de Factus Pay (recaudos con QR Bre-B).

Medido en sandbox (25-sep y 05-oct-2026): POST /auth → {token} que no vence (5 intentos/min); crear recaudo responde
200 con status "ready" y el QR ya generado (la documentación dice 201/started: se aceptan ambos); repetir la referencia
devuelve el mismo recaudo. Monto entre 10.000 y 12.000.000 COP.
"""
import base64
from dataclasses import dataclass
from decimal import Decimal

import httpx

from firebox.config import USER_AGENT, requerido

MONTO_MINIMO = Decimal("10000")
MONTO_MAXIMO = Decimal("12000000")


class ErrorFactusPay(Exception):
    def __init__(self, estado: int, detalle):
        super().__init__(f"Factus Pay respondió {estado}: {detalle}")
        self.estado = estado
        self.detalle = detalle


@dataclass(frozen=True)
class Recaudo:
    referencia: str
    monto: Decimal
    estado: str
    qr_png: bytes | None


def monto_permitido(total: Decimal) -> bool:
    return MONTO_MINIMO <= total <= MONTO_MAXIMO


def _a_recaudo(datos: dict) -> Recaudo:
    qr = datos.get("qr")
    png = base64.b64decode(qr.split(",", 1)[1]) if qr else None
    return Recaudo(datos["reference_code"], Decimal(str(datos["amount"])), datos["status"], png)


class ClienteFactusPay:
    def __init__(self, base_url: str, correo: str, clave: str):
        self._base = base_url.rstrip("/")
        self._correo, self._clave = correo, clave
        self._token: str | None = None
        self._http = httpx.Client(timeout=60, headers={"Accept": "application/json", "User-Agent": USER_AGENT})

    @classmethod
    def desde_entorno(cls) -> "ClienteFactusPay":
        return cls(requerido("FACTUS_PAY_BASE_URL"), requerido("FACTUS_PAY_EMAIL"), requerido("FACTUS_PAY_PASSWORD"))

    def _obtener_token(self) -> str:
        if not self._token:
            r = self._http.post(f"{self._base}/auth", json={"email": self._correo, "password": self._clave})
            if r.status_code != 200:
                raise ErrorFactusPay(r.status_code, "no se pudo autenticar")
            self._token = r.json()["token"]
        return self._token

    def _pedir(self, metodo: str, ruta: str, **kwargs) -> dict:
        r = self._http.request(metodo, f"{self._base}{ruta}",
                               headers={"Authorization": f"Bearer {self._obtener_token()}"}, **kwargs)
        if r.status_code >= 400:
            try:
                detalle = r.json()
            except ValueError:
                detalle = r.text[:300]
            raise ErrorFactusPay(r.status_code, detalle)
        return r.json()

    def crear_recaudo(self, referencia: str, monto: Decimal) -> Recaudo:
        if not monto_permitido(monto):
            raise ErrorFactusPay(422, f"monto {monto} fuera del rango {MONTO_MINIMO}-{MONTO_MAXIMO}")
        valor = int(monto) if monto == monto.to_integral_value() else float(monto)
        recaudo = _a_recaudo(self._pedir("POST", "/v1/collections", json={"reference_code": referencia, "amount": valor})["data"])
        if recaudo.qr_png is None:  # documentación: puede llegar "started" sin QR
            recaudo = self.consultar(referencia)
        return recaudo

    def consultar(self, referencia: str) -> Recaudo:
        return _a_recaudo(self._pedir("GET", f"/v1/collections/{referencia}")["data"])
