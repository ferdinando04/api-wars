"""Cálculo de dinero de Firebox.

Constitución, principio I: solo `Decimal`, redondeo ROUND_HALF_EVEN (bancario, el de la DIAN), impuesto por línea,
redondear y luego sumar. Las líneas excluidas no suman IVA ni base gravable.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

CENTAVO = Decimal("0.01")
CERO = Decimal("0.00")


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True)
class Linea:
    referencia: str
    nombre: str
    cantidad: int
    precio_sin_iva: Decimal
    tarifa_iva: Decimal | None  # None = excluido; Decimal("0") = exento

    @property
    def excluida(self) -> bool:
        return self.tarifa_iva is None

    @property
    def base(self) -> Decimal:
        return redondear(self.precio_sin_iva * self.cantidad)

    @property
    def iva(self) -> Decimal:
        if self.excluida:
            return CERO
        return redondear(self.base * self.tarifa_iva / Decimal("100"))


@dataclass(frozen=True)
class Totales:
    subtotal: Decimal
    base_gravable: Decimal
    iva: Decimal
    total: Decimal


def calcular(lineas: list[Linea]) -> Totales:
    subtotal = sum((l.base for l in lineas), CERO)
    base_gravable = sum((l.base for l in lineas if not l.excluida), CERO)
    iva = sum((l.iva for l in lineas), CERO)
    return Totales(subtotal=subtotal, base_gravable=base_gravable, iva=iva, total=subtotal + iva)


def en_texto(valor: Decimal) -> str:
    """$202.181 o $10,52 (formato colombiano)."""
    entero, _, dec = f"{redondear(valor):,.2f}".partition(".")
    entero = entero.replace(",", ".")
    return f"${entero}" if dec == "00" else f"${entero},{dec}"
