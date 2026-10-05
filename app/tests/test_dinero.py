from decimal import Decimal

from firebox.dinero import Linea, calcular, redondear


def test_reloj_con_iva_19():
    t = calcular([Linea("REL-8314", "Reloj Curren 8314", 1, Decimal("169900"), Decimal("19"))])
    assert t.subtotal == Decimal("169900.00")
    assert t.iva == Decimal("32281.00")
    assert t.total == Decimal("202181.00")


def test_caso_validado_por_la_dian_gravado_exento_excluido():
    # Factura real SETP990014918 (11-ago-2026): la DIAN certificó base gravable 15.000, IVA 1.900 y total 19.900.
    t = calcular([
        Linea("A", "Gravado 19 %", 1, Decimal("10000"), Decimal("19")),
        Linea("B", "Exento", 1, Decimal("5000"), Decimal("0")),
        Linea("C", "Excluido", 1, Decimal("3000"), None),
    ])
    assert t.subtotal == Decimal("18000.00")
    assert t.base_gravable == Decimal("15000.00")
    assert t.iva == Decimal("1900.00")
    assert t.total == Decimal("19900.00")


def test_redondeo_bancario_y_no_hacia_arriba():
    # 10,50 × 5 % = 0,525 → half-even da 0,52 (half-up daría 0,53)
    assert redondear(Decimal("0.525")) == Decimal("0.52")
    t = calcular([Linea("X", "Algo", 1, Decimal("10.50"), Decimal("5"))])
    assert t.iva == Decimal("0.52")


def test_cantidad_multiplica_antes_de_impuesto():
    t = calcular([Linea("REL-8314", "Reloj", 2, Decimal("169900"), Decimal("19"))])
    assert t.total == Decimal("404362.00")
