"""Cliente de Factus Pay (recaudos con QR Bre-B).

Medido en sandbox (25-sep y 05-oct-2026): POST /auth → {token} que no vence (5 intentos/min); crear recaudo responde
200 con status "ready" y el QR ya generado (la documentación dice 201/started: se aceptan ambos); repetir la referencia
devuelve el mismo recaudo. Monto entre 10.000 y 12.000.000 COP.
"""
import base64
import threading
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


_COMPARTIDO: "ClienteFactusPay | None" = None
_CANDADO_COMPARTIDO = threading.Lock()


class ClienteFactusPay:
    """Medido el 06-oct-2026: cada POST /auth INVALIDA el token anterior de la misma cuenta (401 «Unauthenticated.»).
    Por eso todo el proceso usa una sola instancia (`desde_entorno`) y, ante un 401, se re-autentica UNA vez y reintenta."""

    def __init__(self, base_url: str, correo: str, clave: str, http: httpx.Client | None = None):
        self._base = base_url.rstrip("/")
        self._correo, self._clave = correo, clave
        self._token: str | None = None
        self._candado = threading.Lock()
        self._http = http or httpx.Client(timeout=60, headers={"Accept": "application/json", "User-Agent": USER_AGENT})

    @classmethod
    def desde_entorno(cls) -> "ClienteFactusPay":
        """La sesión compartida del proceso (una sola, para no invalidarse entre el panel, las ventas y el vigilante)."""
        global _COMPARTIDO
        with _CANDADO_COMPARTIDO:
            if _COMPARTIDO is None:
                _COMPARTIDO = cls(requerido("FACTUS_PAY_BASE_URL"), requerido("FACTUS_PAY_EMAIL"), requerido("FACTUS_PAY_PASSWORD"))
            return _COMPARTIDO

    def _obtener_token(self, renovar: bool = False, vencido: str | None = None) -> str:
        with self._candado:
            # si otro hilo ya renovó el token que falló, se usa el nuevo sin volver a llamar a /auth (límite: 5 por minuto)
            if renovar and self._token and self._token != vencido:
                return self._token
            if renovar or not self._token:
                r = self._http.post(f"{self._base}/auth", json={"email": self._correo, "password": self._clave})
                if r.status_code != 200:
                    raise ErrorFactusPay(r.status_code, "no se pudo autenticar")
                self._token = r.json()["token"]
            return self._token

    def _pedir(self, metodo: str, ruta: str, **kwargs) -> dict:
        token = self._obtener_token()
        r = self._http.request(metodo, f"{self._base}{ruta}", headers={"Authorization": f"Bearer {token}"}, **kwargs)
        if r.status_code == 401:  # otra sesión de la misma cuenta invalidó el token: renovar y reintentar una vez
            token = self._obtener_token(renovar=True, vencido=token)
            r = self._http.request(metodo, f"{self._base}{ruta}", headers={"Authorization": f"Bearer {token}"}, **kwargs)
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

    def listar(self, pagina: int = 1) -> list[dict]:
        """Recaudos de la cuenta, del más reciente al más viejo (15 por página): reference_code, amount, status, created_at, qr."""
        return self._pedir("GET", "/v1/collections", params={"page": pagina})["data"]
