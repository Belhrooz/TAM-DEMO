"""Lectura y validación de la zona MRZ (TD3, pasaportes)."""
import re

_VAL = {**{str(i): i for i in range(10)},
        **{chr(65 + i): 10 + i for i in range(26)}, "<": 0}
_W = (7, 3, 1)

PAISES = {
    "PER": "PERUANA", "USA": "ESTADOUNIDENSE", "GBR": "BRITÁNICA", "ESP": "ESPAÑOLA",
    "ARG": "ARGENTINA", "CHL": "CHILENA", "COL": "COLOMBIANA", "BRA": "BRASILEÑA",
    "MEX": "MEXICANA", "FRA": "FRANCESA", "DEU": "ALEMANA", "CAN": "CANADIENSE",
    "AUS": "AUSTRALIANA", "ITA": "ITALIANA", "ECU": "ECUATORIANA", "BOL": "BOLIVIANA",
    "NLD": "NEERLANDESA", "CHE": "SUIZA", "JPN": "JAPONESA", "CHN": "CHINA",
}


def digito(campo: str) -> str:
    total = sum(_VAL.get(c, 0) * _W[i % 3] for i, c in enumerate(campo))
    return str(total % 10)


def _limpiar(linea: str) -> str:
    return re.sub(r"[^A-Z0-9<]", "", linea.upper().replace(" ", ""))


_A_DIG = str.maketrans("OQDILZSBG", "001112586")
_A_LET = str.maketrans("0125869", "OIZSBGQ")


def reparar_l2(l2: str) -> str:
    """Campos que solo pueden ser dígitos o letras: corrige las confusiones típicas del OCR."""
    c = list(l2)
    for i in [9, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26, 27, 42, 43]:
        c[i] = c[i].translate(_A_DIG)
    for i in (10, 11, 12):
        c[i] = c[i].translate(_A_LET)
    return "".join(c)


def parsear_td3(l1: str, l2: str) -> dict | None:
    l1, l2 = _limpiar(l1), _limpiar(l2)
    if len(l1) < 10 or len(l2) < 43:
        return None
    l1, l2 = l1.ljust(44, "<")[:44], reparar_l2(l2.ljust(44, "<")[:44])
    if l1[0] != "P":
        return None
    nombre = l1[5:].split("<<", 1)
    apellidos = nombre[0].replace("<", " ").strip()
    nombres = nombre[1].replace("<", " ").strip() if len(nombre) > 1 else ""
    numero = l2[0:9].replace("<", "")
    checks = [
        digito(l2[0:9]) == l2[9],
        digito(l2[13:19]) == l2[19],
        digito(l2[21:27]) == l2[27],
        digito(l2[0:10] + l2[13:20] + l2[21:43]) == l2[43],
    ]
    return {
        "numero": numero,
        "nacionalidad": l2[10:13],
        "apellidos": apellidos,
        "nombres": nombres,
        "valido": all(checks),
        # el nombre no tiene dígito verificador: se marca si parece un error típico del OCR
        "revisar_nombre": bool(re.search(r"\d", l1[5:])) or (len(nombre) > 1 and nombres.endswith("K")),
    }


def buscar_en_texto(texto: str) -> dict | None:
    """Busca dos líneas MRZ consecutivas dentro de un texto."""
    lineas = [_limpiar(x) for x in texto.splitlines()]
    lineas = [x for x in lineas if len(x) >= 10]
    for i in range(len(lineas) - 1):
        if lineas[i].startswith("P") and "<" in lineas[i] and len(lineas[i + 1]) >= 43:
            r = parsear_td3(lineas[i], lineas[i + 1])
            if r:
                return r
    return None


_PARTICULAS = {"DE", "DEL", "LA", "LAS", "LOS", "DA", "DO", "DOS", "DI", "VAN", "VON",
               "DER", "O", "MC", "MAC", "SAN", "ST", "LE"}


def nombre_archivo(d: dict) -> str:
    """JUAN PEREZ = primer nombre + primer apellido (respeta DE GROFT, O MALLEY...)."""
    n = d.get("nombres", "").split()
    a = d.get("apellidos", "").split()
    ap = []
    for tok in a:
        ap.append(tok)
        if tok not in _PARTICULAS:
            break
    return " ".join([(n[0] if n else ""), " ".join(ap)]).strip() or "SIN NOMBRE"
