"""Portal de Migraciones SIMULADO: captcha, consulta y TAM de demostración."""
import hashlib
import io
import os
import random
from datetime import date, timedelta

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts", "DejaVuSans-Bold.ttf")


def generar_captcha():
    texto = "".join(random.choice(_CHARS) for _ in range(5))
    img = Image.new("RGB", (220, 70), (240, 240, 240))
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype(_FONT, 38)
    except OSError:
        f = ImageFont.load_default()
    for i, c in enumerate(texto):
        d.text((14 + i * 38, 10 + random.randint(-4, 8)), c, font=f,
               fill=(random.randint(0, 90), random.randint(0, 90), random.randint(0, 90)))
    for _ in range(6):
        d.line([(random.randint(0, 220), random.randint(0, 70)),
                (random.randint(0, 220), random.randint(0, 70))],
               fill=(random.randint(80, 160),) * 3, width=2)
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return texto, buf.getvalue()


def consultar(numero: str, desde: date, hasta: date) -> date:
    """Simula el portal: devuelve una fecha de ingreso dentro del rango pedido."""
    dias = max((hasta - desde).days, 0)
    h = int(hashlib.sha256(numero.encode()).hexdigest(), 16)
    return desde + timedelta(days=h % (dias + 1))


def generar_tam_pdf(p: dict, fecha_ingreso: date) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, h - 60, "TARJETA ANDINA DE MIGRACIÓN VIRTUAL")
    c.setFont("Helvetica", 10)
    c.drawString(50, h - 78, "Documento de demostración - sin validez oficial")
    filas = [
        ("Nombres y apellidos", p["nombre"]),
        ("Tipo de documento", p.get("tipo", "PASAPORTE")),
        ("Número de documento", p["numero"]),
        ("Nacionalidad", p["nacionalidad"]),
        ("Fecha de ingreso", fecha_ingreso.strftime("%d/%m/%Y")),
    ]
    y = h - 130
    for k, v in filas:
        c.setFont("Helvetica-Bold", 11); c.drawString(50, y, k + ":")
        c.setFont("Helvetica", 11); c.drawString(210, y, str(v))
        y -= 26
    c.saveState()
    c.setFillColorRGB(0.85, 0.85, 0.85)
    c.setFont("Helvetica-Bold", 70)
    c.translate(w / 2, h / 2)
    c.rotate(35)
    c.drawCentredString(0, 0, "DEMOSTRACIÓN")
    c.restoreState()
    c.showPage()
    c.save()
    return buf.getvalue()
