"""Genera pasaportes FICTICIOS (PDF multipágina) con MRZ válida para pruebas y demo."""
import sys
from PIL import Image, ImageDraw, ImageFont
from core import mrz

import os
_AQUI = os.path.dirname(os.path.abspath(__file__))
FUENTES = [os.path.join(_AQUI, "fonts", "DejaVuSansMono-Bold.ttf"),
           "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
           "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"]


def _font(size):
    for f in FUENTES:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _rel(campo):
    return campo + mrz.digito(campo)


def linea_mrz(apellido, nombres, numero, nac="PER", nacimiento="900115", exp="320101", sexo="M"):
    l1 = f"P<{nac}{apellido}<<{nombres.replace(' ', '<')}".ljust(44, "<")[:44]
    num = numero.ljust(9, "<")
    cuerpo = (num + mrz.digito(num) + nac + nacimiento + mrz.digito(nacimiento) + sexo
              + exp + mrz.digito(exp) + "<" * 14 + "<")
    final = mrz.digito(cuerpo[0:10] + cuerpo[13:20] + cuerpo[21:43])
    return l1, cuerpo[:43] + final


def pagina(apellido, nombres, numero, nac="PER"):
    W, H = 1500, 1050
    img = Image.new("RGB", (W, H), (236, 232, 218))
    d = ImageDraw.Draw(img)
    d.rectangle([30, 30, W - 30, H - 30], outline=(120, 110, 90), width=4)
    d.text((70, 60), "PASAPORTE DE PRUEBA - DATOS FICTICIOS", font=_font(34), fill=(90, 40, 40))
    d.rectangle([70, 140, 420, 560], outline=(150, 150, 150), width=3)
    d.text((150, 330), "FOTO", font=_font(40), fill=(170, 170, 170))
    d.text((470, 160), f"Apellidos: {apellido}", font=_font(36), fill=(30, 30, 30))
    d.text((470, 230), f"Nombres:   {nombres}", font=_font(36), fill=(30, 30, 30))
    d.text((470, 300), f"Nº:        {numero}", font=_font(36), fill=(30, 30, 30))
    d.text((470, 370), f"Nac.:      {nac}", font=_font(36), fill=(30, 30, 30))
    l1, l2 = linea_mrz(apellido, nombres, numero, nac)
    d.rectangle([40, 780, W - 40, H - 60], fill=(255, 255, 255))
    f = _font(31)
    d.text((55, 805), l1, font=f, fill=(0, 0, 0))
    d.text((55, 890), l2, font=f, fill=(0, 0, 0))
    return img


PERSONAS = [
    ("PEREZ", "JUAN CARLOS", "P1234567", "PER"), ("LOPEZ", "MARIA ELENA", "P2345678", "PER"),
    ("CHAVEZ", "JUAN", "P3456789", "PER"), ("SMITH", "JOHN ROBERT", "5123456", "USA"),
    ("GARCIA", "ANA", "PAB12345", "ESP"), ("MULLER", "KLAUS", "C01X00T47", "DEU"),
    ("ROSSI", "LUCA", "YA1234567", "ITA"), ("DUBOIS", "CLAIRE", "19AB12345", "FRA"),
]

def pdf_bytes(n=len(PERSONAS)):
    """PDF de pasaportes ficticios. Incluye una capa de texto invisible con la MRZ,
    así la demo se lee sin necesitar Tesseract."""
    import io
    import pymupdf
    personas = [PERSONAS[i % len(PERSONAS)] for i in range(n)]
    paginas = [pagina(*p) for p in personas]
    buf = io.BytesIO()
    paginas[0].save(buf, "PDF", save_all=True, append_images=paginas[1:], resolution=150)
    doc = pymupdf.open(stream=buf.getvalue(), filetype="pdf")
    for page, (ap, nom, num, nac) in zip(doc, personas):
        l1, l2 = linea_mrz(ap, nom, num, nac)
        x = page.rect.width * 0.04
        page.insert_text((x, page.rect.height * 0.80), l1, fontname="cour", fontsize=7, render_mode=3)
        page.insert_text((x, page.rect.height * 0.87), l2, fontname="cour", fontsize=7, render_mode=3)
    return doc.tobytes()


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(PERSONAS)
    with open("pasaportes_prueba.pdf", "wb") as f:
        f.write(pdf_bytes(n))
    print("generado pasaportes_prueba.pdf con", n, "páginas")
