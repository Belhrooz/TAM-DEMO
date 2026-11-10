"""Separar PDFs/imágenes y leer pasaportes (uno o dos por página) y TAM ya emitidas."""
import io
import os
import re
import shutil
import subprocess
import tempfile

import pymupdf
from PIL import Image, ImageOps

from . import mrz

_WL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<"
_ZOOM = 2.5


def _tesseract():
    """Busca Tesseract en el PATH o en las rutas habituales de Windows."""
    ruta = shutil.which("tesseract")
    if ruta:
        return ruta
    for r in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
              r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if os.path.exists(r):
            return r
    return None


def expandir(archivos):
    """archivos: lista de (nombre, bytes). Devuelve un item por página/imagen."""
    items = []
    for nombre, datos in archivos:
        ext = os.path.splitext(nombre)[1].lower()
        try:
            if ext == ".pdf":
                doc = pymupdf.open(stream=datos, filetype="pdf")
                for i in range(len(doc)):
                    one = pymupdf.open()
                    one.insert_pdf(doc, from_page=i, to_page=i)
                    items.append({"origen": f"{nombre} (pág. {i + 1})", "pdf": one.tobytes()})
            else:
                img = pymupdf.open(stream=datos, filetype=ext.lstrip(".") or "png")
                items.append({"origen": nombre, "pdf": img.convert_to_pdf()})
        except Exception as e:
            items.append({"origen": f"{nombre} (error: {e})", "pdf": None})
    return items


def _img(pdf_bytes, zoom=_ZOOM):
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def miniatura(pdf_bytes, zoom=0.6):
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    return doc[0].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")


def _pdf_de_imagen(img):
    pdf = pymupdf.open()
    page = pdf.new_page(width=img.width / _ZOOM, height=img.height / _ZOOM)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=88)
    page.insert_image(page.rect, stream=buf.getvalue())
    return pdf.tobytes()


def _tess(exe, franja):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        franja.save(f.name)
        ruta = f.name
    try:
        return subprocess.run([exe, ruta, "stdout", "--psm", "6", "-c",
                               f"tessedit_char_whitelist={_WL}"],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""
    finally:
        os.unlink(ruta)


def _variantes(g):
    w, h = g.size
    for giro in (0, -2.5, 2.5, -5, 5):
        base = g if giro == 0 else g.rotate(giro, resample=Image.BICUBIC, fillcolor=255)
        for frac in (0.25, 0.35, 0.5):
            franja = ImageOps.autocontrast(base.crop((0, int(h * (1 - frac)), w, h)))
            yield franja
            yield franja.point(lambda v: 255 if v > 135 else 0)


def _ocr_tesseract(img):
    """OCR de la franja inferior (donde está la MRZ). Prueba varias alturas, binarizado y
    pequeños giros. Acepta un número solo cuando DOS lecturas válidas coinciden (un dígito de
    control puede validar por casualidad con una lectura errónea). Si solo hay una lectura
    válida la usa; si ninguna valida, devuelve la primera (se marcará para revisión)."""
    from collections import Counter
    exe = _tesseract()
    if not exe:
        return None
    g = img.convert("L")
    validas, primera = [], None
    for franja in _variantes(g):
        r = mrz.buscar_en_texto(_tess(exe, franja))
        if not r:
            continue
        primera = primera or r
        if r["valido"]:
            validas.append(r)
            cuenta = Counter(x["numero"] for x in validas)
            numero, veces = cuenta.most_common(1)[0]
            if veces >= 2:
                return next(x for x in validas if x["numero"] == numero)
    if validas:
        numero = Counter(x["numero"] for x in validas).most_common(1)[0][0]
        r = next(x for x in validas if x["numero"] == numero)
        if len(validas) == 1:
            r = {**r, "revisar_nombre": True}  # una sola lectura: que la persona confirme
        return r
    return primera


_RAPID = None


def _motor():
    """RapidOCR: se instala solo con pip (sin programas externos)."""
    global _RAPID
    if _RAPID is None:
        try:
            from rapidocr import RapidOCR
            _RAPID = RapidOCR()
        except Exception:
            _RAPID = False
    return _RAPID or None


def hay_ocr():
    return bool(_motor() or _tesseract())


def _ocr_rapid(img):
    import numpy as np
    eng = _motor()
    if not eng:
        return None
    w, h = img.size
    primera = None
    for ini in (0.62, 0.5, 0.72):
        franja = img.convert("RGB").crop((0, int(h * ini), w, h))
        try:
            out = eng(np.asarray(franja))
        except Exception:
            continue
        txts = list(out.txts) if getattr(out, "txts", None) else []
        r = mrz.buscar_en_texto("\n".join(txts))
        if r and r["valido"]:
            return r
        primera = primera or r
    return primera


def _ocr_franja(img):
    """RapidOCR primero; Tesseract (si está instalado) como respaldo."""
    r = _ocr_rapid(img)
    if r and r["valido"]:
        return r
    r2 = _ocr_tesseract(img) if _tesseract() else None
    if r2 and r2["valido"]:
        return r2
    return r or r2


def _columna_vacia(img):
    """Si la página trae dos pasaportes lado a lado, devuelve la x que los separa:
    el centro del tramo más largo SIN texto oscuro en la franja inferior (donde va la MRZ)."""
    import numpy as np
    w, h = img.size
    if w < h * 1.2:
        return None
    a = np.asarray(img.convert("L"), dtype="float32")[int(h * 0.70):int(h * 0.98)]
    oscuro = (a < 110).sum(axis=0)
    vacio = oscuro <= 3
    lo, hi = int(w * 0.30), int(w * 0.70)
    mejor, ini = (0, None), None
    for x in range(lo, hi):
        if vacio[x]:
            ini = x if ini is None else ini
            if x - ini + 1 > mejor[0]:
                mejor = (x - ini + 1, ini)
        else:
            ini = None
    largo, desde = mejor
    return desde + largo // 2 if largo >= w * 0.007 else None


def _parsear_tam(texto):
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    for i, l in enumerate(lineas):
        if l.startswith("INSPECTOR SALIDA"):
            v = lineas[i + 1:]
            if len(v) >= 6:
                f = re.search(r"(\d{2}/\d{2}/\d{4})\s*\n-{3,}", texto)
                return {"apellidos": v[0], "nombres": v[1], "numero": v[5].upper(),
                        "ingreso": f.group(1) if f else ""}
    return None


def analizar(pdf_bytes):
    """Analiza UNA página. Devuelve una lista de hallazgos:
    {"tipo": "pasaporte"|"tam"|"manual", "datos": dict|None, "pdf": bytes}"""
    if not pdf_bytes:
        return [{"tipo": "manual", "datos": None, "pdf": None}]
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    texto = doc[0].get_text()

    if "TARJETA ANDINA" in texto.upper():
        d = _parsear_tam(texto)
        if d:
            return [{"tipo": "tam", "datos": d, "pdf": pdf_bytes}]

    r = mrz.buscar_en_texto(texto)  # PDFs con capa de texto
    if r:
        return [{"tipo": "pasaporte", "datos": r, "pdf": pdf_bytes}]

    img = _img(pdf_bytes)
    corte = _columna_vacia(img)
    if corte:  # dos pasaportes en la misma página
        out = []
        for caja in ((0, 0, corte, img.height), (corte, 0, img.width, img.height)):
            mitad = img.crop(caja)
            out.append({"tipo": "pasaporte" if (d := _ocr_franja(mitad)) else "manual",
                        "datos": d, "pdf": _pdf_de_imagen(mitad)})
        return out

    r = _ocr_franja(img)
    return [{"tipo": "pasaporte" if r else "manual", "datos": r, "pdf": pdf_bytes}]
