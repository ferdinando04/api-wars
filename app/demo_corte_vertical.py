"""Demo de punta a punta de Firebox desde la terminal (la misma venta que hace el botón del panel).

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
from decimal import Decimal

from firebox.dinero import Linea
from firebox.ventas import VentaRechazada, vender, vigilar

TIENDA = "Relojes NovaMarket"
PRODUCTO = Linea("REL-8314", "Reloj Curren 8314 negro", 1, Decimal("169900"), Decimal("19"))


def main() -> int:
    args = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    args.add_argument("--para", help="número de WhatsApp del cliente, solo dígitos con 57 (ej. 573001234567)")
    args.add_argument("--sin-whatsapp", action="store_true", help="no envía nada por WhatsApp")
    args.add_argument("--espera", type=int, default=10, help="minutos vigilando el pago (por defecto 10)")
    a = args.parse_args()
    if not a.sin_whatsapp and not a.para:
        args.error("indica --para o usa --sin-whatsapp")

    inicio = time.time()

    def paso(texto: str) -> None:
        print(f"[{time.time() - inicio:6.1f} s] {texto}", flush=True)

    para = None if a.sin_whatsapp else a.para
    try:
        venta = vender([PRODUCTO], TIENDA, para=para, avisar=paso)
    except VentaRechazada as e:
        paso(f"ALTO: {e}")
        return 1
    return 0 if vigilar(venta, para=para, minutos=a.espera, avisar=paso) else 2


if __name__ == "__main__":
    sys.exit(main())
