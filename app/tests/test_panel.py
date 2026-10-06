from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from firebox import web

RECAUDOS = [
    {"reference_code": "SETP990023179", "amount": 202181, "status": "paid", "created_at": "2026-10-05T16:59:49.000000Z", "qr": None},
    {"reference_code": "SETP990023178", "amount": 202181, "status": "ready", "created_at": "2026-10-05T16:59:49.000000Z", "qr": None},
    {"reference_code": "SETP990023180", "amount": 10000.5, "status": "ready", "created_at": "2026-10-05T16:59:49.000000Z", "qr": None},
]


class PayFalso:
    def listar(self, pagina: int = 1):
        return RECAUDOS


class FactusFalso:
    def ver_factura(self, numero: str):
        return {"cufe": "c0480313a5de09b6ffff", "is_validated": True, "validated_at": "05-10-2026 12:46:07 PM"}


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(web, "credenciales_panel", lambda: ("firebox", "clave-de-prueba"))
    monkeypatch.setattr(web, "_detalles", {})
    web.app.dependency_overrides[web.cliente_pay] = lambda: PayFalso()
    web.app.dependency_overrides[web.cliente_factus] = lambda: FactusFalso()
    yield TestClient(web.app)
    web.app.dependency_overrides.clear()


def test_resumen_suma_con_decimal():
    _, r = web.resumir(RECAUDOS)
    assert r.ventas == 3
    assert r.facturado == Decimal("414362.50")
    assert r.cobrado == Decimal("202181.00")
    assert r.pendiente == Decimal("212181.50")


def test_tabla_muestra_estados_y_totales(cliente):
    html = cliente.get("/panel/tabla", auth=("firebox", "clave-de-prueba")).text
    assert "Pagado" in html and "Esperando pago" in html
    assert "SETP990023179" in html
    assert "$202.181" in html          # cobrado
    assert "$414.362,50" in html       # facturado


def test_fecha_y_cufe_vienen_de_factus_y_lo_reciente_va_arriba(cliente):
    html = cliente.get("/panel/tabla", auth=("firebox", "clave-de-prueba")).text
    assert "05/10 12:46 PM" in html                     # validated_at de Factus, no la fecha fija de Factus Pay
    assert "CUFE c0480313a5" in html and "✓ DIAN" in html
    assert html.index("SETP990023180") < html.index("SETP990023179") < html.index("SETP990023178")


def test_sin_clave_no_entra(cliente):
    assert cliente.get("/panel/tabla").status_code == 401
    assert cliente.get("/panel/tabla", auth=("firebox", "otra")).status_code == 401


def test_factura_con_numero_raro_no_llega_a_factus(cliente):
    r = cliente.get("/panel/factura/..%2F..%2Fsecreto.pdf", auth=("firebox", "clave-de-prueba"))
    assert r.status_code in (400, 404)
