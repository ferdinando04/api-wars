"""Documento único que recibe el cliente: la factura de Factus + una página final "Paga aquí" con el QR de Factus Pay."""
import io

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

NARANJA = HexColor("#F2611D")
GRIS = HexColor("#4B5563")


def pagina_pago(tienda: str, numero_factura: str, total_texto: str, qr_png: bytes, vence_texto: str) -> bytes:
    salida = io.BytesIO()
    c = canvas.Canvas(salida, pagesize=letter)
    ancho, alto = letter
    c.setFillColor(NARANJA)
    c.rect(0, alto - 90, ancho, 90, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 26)
    c.drawString(50, alto - 58, "Paga aquí")
    c.setFont("Helvetica", 12)
    c.drawRightString(ancho - 50, alto - 55, f"{tienda} · Firebox")

    c.setFillColor(HexColor("#111827"))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, alto - 140, f"Factura electrónica {numero_factura}")
    c.setFont("Helvetica-Bold", 30)
    c.drawString(50, alto - 185, total_texto)

    lado = 260
    c.drawImage(ImageReader(io.BytesIO(qr_png)), (ancho - lado) / 2, alto - 230 - lado, lado, lado)

    c.setFillColor(GRIS)
    c.setFont("Helvetica", 12)
    texto = c.beginText(50, alto - 530)
    for linea in (
        "1. Abre la app de tu banco o billetera y busca la opción de pagar con QR (Bre-B).",
        "2. Escanea este código: el monto ya está incluido y no se puede modificar.",
        "3. Confirma el pago. Firebox te avisará por WhatsApp cuando se reciba.",
        "",
        f"Referencia del pago: {numero_factura}",
        f"Este código vence: {vence_texto}",
        "",
        "Cobro procesado por Factus Pay. Ambiente de pruebas (sandbox): sin validez fiscal ni dinero real.",
    ):
        texto.textLine(linea)
    c.drawText(texto)
    c.showPage()
    c.save()
    return salida.getvalue()


def unir(*pdfs: bytes) -> bytes:
    escritor = PdfWriter()
    for documento in pdfs:
        for pagina in PdfReader(io.BytesIO(documento)).pages:
            escritor.add_page(pagina)
    salida = io.BytesIO()
    escritor.write(salida)
    return salida.getvalue()
