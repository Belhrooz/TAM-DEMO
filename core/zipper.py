"""Arma el ZIP: CODIGO/PASAPORTES/NOMBRE.pdf y CODIGO/TAMS/TAM NOMBRE.pdf."""
import io
import re
import zipfile


def _seguro(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "", s).strip() or "SIN NOMBRE"


def _nombres(pasajeros):
    usados, out = set(), []
    for p in pasajeros:
        if not p.get("incluir", True) or not p.get("pdf") or not p.get("nombre"):
            continue
        nombre = _seguro(p["nombre"])
        if nombre.upper() in usados:  # homónimos: se distinguen por Nº de pasaporte
            nombre = f"{nombre} {_seguro(p['numero'])}"
        usados.add(nombre.upper())
        out.append((p, nombre))
    return out


def listar(codigo: str, pasajeros: list[dict]) -> list[str]:
    codigo = _seguro(codigo)
    rutas = []
    for p, n in _nombres(pasajeros):
        rutas.append(f"{codigo}/PASAPORTES/{n}.pdf")
        if p.get("tam"):
            rutas.append(f"{codigo}/TAMS/TAM {n}.pdf")
    return rutas


def construir_zip(codigo: str, pasajeros: list[dict]) -> bytes:
    codigo = _seguro(codigo)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{codigo}/PASAPORTES/", "")
        z.writestr(f"{codigo}/TAMS/", "")
        for p, n in _nombres(pasajeros):
            z.writestr(f"{codigo}/PASAPORTES/{n}.pdf", p["pdf"])
            if p.get("tam"):
                z.writestr(f"{codigo}/TAMS/TAM {n}.pdf", p["tam"])
    return buf.getvalue()
