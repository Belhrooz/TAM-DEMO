import warnings
from datetime import date

import pandas as pd
import streamlit as st

from core import mrz, pasaportes, tam_demo, zipper
import make_samples

warnings.filterwarnings("ignore")
st.set_page_config(page_title="Pasaportes y TAM en automático", page_icon="🛂", layout="wide")

ss = st.session_state
ss.setdefault("pasajeros", [])
ss.setdefault("cap", None)
ss.setdefault("ultima_tam", None)
if ss.get("aviso"):
    _msg, _ico = ss.pop("aviso")
    st.toast(_msg, icon=_ico)

ESTADOS = {"ok": "✅ OK", "revisar": "⚠️ Revisar", "manual": "✍️ Completar"}

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; max-width: 1180px;}
.hero {background: linear-gradient(120deg, #0F766E 0%, #134E4A 55%, #1E293B 100%);
       color: #fff; padding: 30px 34px; border-radius: 18px; margin-bottom: 18px;}
.hero h1 {color: #fff; font-size: 2.1rem; margin: 0 0 6px 0; padding: 0;}
.hero p {color: #CCFBF1; font-size: 1.05rem; margin: 0;}
.hero .tag {display: inline-block; background: rgba(255,255,255,.16); border-radius: 999px;
            padding: 3px 12px; font-size: .78rem; margin-bottom: 10px; letter-spacing: .4px;}
.steps {display: flex; gap: 12px; margin: 4px 0 18px 0;}
.step {flex: 1; border: 1px solid #E2E8F0; background: #fff; border-radius: 14px; padding: 14px 16px;
       display: flex; gap: 12px; align-items: center;}
.step .n {width: 34px; height: 34px; border-radius: 50%; background: #E2E8F0; color: #475569;
          display: flex; align-items: center; justify-content: center; font-weight: 700; flex: none;}
.step b {display: block; color: #0F172A;} .step small {color: #64748B;}
.step.done {border-color: #99F6E4; background: #F0FDFA;}
.step.done .n {background: #0F766E; color: #fff;}
.step.active {border-color: #0F766E; box-shadow: 0 0 0 3px rgba(15,118,110,.12);}
.step.active .n {background: #0F766E; color: #fff;}
.card {border: 1px solid #E2E8F0; border-radius: 14px; padding: 18px 20px; background: #fff;}
.card h4 {margin: 0 0 8px 0;}
.tree {font-family: ui-monospace, Consolas, monospace; font-size: .86rem; line-height: 1.55;
       background: #0F172A; color: #E2E8F0; border-radius: 12px; padding: 14px 18px; overflow-x: auto;}
.tree .d {color: #5EEAD4;} .tree .t {color: #FDE68A;}
.foot {color: #64748B; font-size: .82rem; text-align: center; margin-top: 28px;}
</style>
""", unsafe_allow_html=True)


# ───────────────────────── lógica ─────────────────────────
def procesar(archivos):
    items = pasaportes.expandir(archivos)
    barra = st.progress(0.0, text="Leyendo páginas…")
    pas, tams = [], {}
    for i, it in enumerate(items):
        for h in pasaportes.analizar(it["pdf"]):
            mini = pasaportes.miniatura(h["pdf"]) if h["pdf"] and h["tipo"] != "tam" else None
            if h["tipo"] == "tam":
                tams[h["datos"]["numero"]] = h["pdf"]
            elif h["tipo"] == "pasaporte":
                r = h["datos"]
                pas.append({"origen": it["origen"], "pdf": h["pdf"], "nombre": mrz.nombre_archivo(r),
                            "numero": r["numero"], "nacionalidad": r["nacionalidad"],
                            "estado": "ok" if r["valido"] and not r["revisar_nombre"] else "revisar",
                            "incluir": True, "tam": None, "mini": mini})
            else:
                pas.append({"origen": it["origen"], "pdf": h["pdf"], "nombre": "", "numero": "",
                            "nacionalidad": "PER", "estado": "manual", "incluir": bool(h["pdf"]),
                            "tam": None, "mini": mini})
        barra.progress((i + 1) / len(items), text=f"Leyendo páginas… {i + 1}/{len(items)}")
    barra.empty()
    for p in pas:  # TAM que ya venían dentro del PDF
        if p["numero"] in tams:
            p["tam"] = tams[p["numero"]]
    ss.pasajeros = pas
    ss.cap = None
    ss.ultima_tam = None
    ss.tams_sueltas = len(tams) - sum(bool(p["tam"]) for p in pas)
    ss.aviso = (f"{len(pas)} pasaportes listos", "✅")
    st.rerun()  # refresca los pasos y la pestaña de TAM con los datos nuevos


def nuevo_captcha():
    ss.cap = tam_demo.generar_captcha()


def cargar_ejemplo():
    procesar([("pasaportes_ejemplo.pdf", make_samples.pdf_bytes())])


# ───────────────────────── barra lateral ─────────────────────────
with st.sidebar:
    st.markdown("### 🛂 Cómo funciona")
    st.markdown("1. **Sube** los PDFs o imágenes de pasaportes del file.\n"
                "2. La app **separa** cada pasaporte y lee su zona MRZ.\n"
                "3. **Revisas** la tabla y corriges lo dudoso.\n"
                "4. Se obtiene la **TAM** de cada pasajero (tú escribes el captcha).\n"
                "5. **Descargas** un ZIP ordenado por carpetas.")
    st.divider()
    st.caption("🧪 **Modo demostración.** El portal de Migraciones está simulado y las TAM generadas "
               "no tienen validez. Usa solo datos de ejemplo.")
    if not pasaportes.hay_ocr():
        st.warning("No se pudo iniciar el lector OCR: los escaneos reales se completarán a mano.")

pas_ok = bool(ss.pasajeros)
incl = [p for p in ss.pasajeros if p["incluir"] and p["nombre"] and p["numero"]]
tam_ok = pas_ok and bool(incl) and all(p["tam"] for p in incl)

# ───────────────────────── encabezado ─────────────────────────
st.markdown("""
<div class="hero">
  <span class="tag">AUTOMATIZACIÓN DE FILES</span>
  <h1>Pasaportes y TAM, en automático</h1>
  <p>Sube los pasaportes de un file, obtén la TAM de cada pasajero y descarga todo ordenado por carpetas.</p>
</div>
""", unsafe_allow_html=True)


def _cls(done, active):
    return "done" if done else ("active" if active else "")


st.markdown(f"""
<div class="steps">
  <div class="step {_cls(pas_ok, not pas_ok)}"><span class="n">{'✓' if pas_ok else '1'}</span>
    <div><b>Pasaportes</b><small>Se separan y se leen solos</small></div></div>
  <div class="step {_cls(tam_ok, pas_ok and not tam_ok)}"><span class="n">{'✓' if tam_ok else '2'}</span>
    <div><b>TAM</b><small>Un captcha por pasajero</small></div></div>
  <div class="step {_cls(False, tam_ok)}"><span class="n">3</span>
    <div><b>ZIP por file</b><small>PASAPORTES y TAMS</small></div></div>
</div>
""", unsafe_allow_html=True)

t1, t2, t3 = st.tabs(["1 · Pasaportes", "2 · TAM", "3 · Descargar"])

# ───────────────────────── 1. PASAPORTES ─────────────────────────
with t1:
    c1, c2 = st.columns([1, 3])
    codigo = c1.text_input("Código del file", value="AKB1982", key="codigo").strip().upper()
    subidos = c2.file_uploader("PDFs o imágenes de pasaportes (puede haber varios por PDF)",
                               type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True)
    b1, b2, _ = st.columns([1, 1.4, 2])
    if b1.button("Procesar archivos", type="primary", disabled=not subidos):
        procesar([(f.name, f.getvalue()) for f in subidos])
    if b2.button("Usar pasaportes de ejemplo"):
        cargar_ejemplo()

    if not ss.pasajeros:
        st.markdown("")
        e1, e2, e3 = st.columns(3)
        for col, ico, tit, txt in (
            (e1, "📄", "Separa", "Un PDF con 10, 18 o 104 pasaportes (incluso dos por página) se divide en un archivo por pasajero."),
            (e2, "🔎", "Lee la MRZ", "Extrae número, nacionalidad y nombres de la zona de lectura mecánica y valida sus dígitos de control."),
            (e3, "🗂️", "Ordena", "Nombra cada archivo como NOMBRE APELLIDO y arma las carpetas PASAPORTES y TAMS del file."),
        ):
            col.markdown(f'<div class="card"><h4>{ico} {tit}</h4>{txt}</div>', unsafe_allow_html=True)
        st.caption("👆 Sube tus archivos, o prueba con los pasaportes de ejemplo para ver el flujo completo.")
    else:
        n = len(ss.pasajeros)
        ok = sum(p["estado"] == "ok" for p in ss.pasajeros)
        con_tam = sum(bool(p["tam"]) for p in ss.pasajeros)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Pasaportes separados", n)
        m2.metric("Leídos sin dudas", ok)
        m3.metric("Para revisar", n - ok)
        m4.metric("TAM ya incluidas", con_tam)
        st.caption("Corrige en la tabla lo que haga falta: el nombre, el número y la nacionalidad se pueden editar.")
        df = pd.DataFrame([{
            "Incluir": p["incluir"], "Nombre de archivo": p["nombre"], "Nº pasaporte": p["numero"],
            "Nacionalidad": p["nacionalidad"], "Estado": ESTADOS[p["estado"]],
            "TAM": "✔ ya incluida" if p["tam"] else "pendiente", "Origen": p["origen"],
        } for p in ss.pasajeros])
        ed = st.data_editor(df, hide_index=True, width="stretch", key="tabla",
                            disabled=["Estado", "TAM", "Origen"], num_rows="fixed")
        for p, (_, row) in zip(ss.pasajeros, ed.iterrows()):
            p["incluir"] = bool(row["Incluir"])
            p["nombre"] = str(row["Nombre de archivo"]).strip().upper()
            p["numero"] = str(row["Nº pasaporte"]).strip().upper()
            p["nacionalidad"] = str(row["Nacionalidad"]).strip().upper()
            if p["estado"] == "manual" and p["nombre"] and p["numero"]:
                p["estado"] = "ok"
        if ss.get("tams_sueltas"):
            st.caption(f"{ss.tams_sueltas} TAM del PDF no coincidieron con ningún pasaporte.")
        with st.expander("🖼️ Ver los pasaportes separados", expanded=False):
            cols = st.columns(4)
            for i, p in enumerate(ss.pasajeros[:24]):
                if p.get("mini"):
                    cols[i % 4].image(p["mini"], caption=p["nombre"] or "sin nombre", width="stretch")
            if n > 24:
                st.caption(f"Mostrando 24 de {n}.")

# ───────────────────────── 2. TAM ─────────────────────────
with t2:
    st.info("🧪 **Portal simulado.** Los datos y el captcha son de demostración y la TAM generada no tiene "
            "validez. La conexión con el portal real de Migraciones vive en la versión de escritorio.")
    if not incl:
        st.markdown('<div class="card"><h4>Aún no hay pasajeros</h4>Procesa los pasaportes en la '
                    'pestaña 1 para empezar a obtener sus TAM.</div>', unsafe_allow_html=True)
    else:
        with st.container(border=True):
            d1, d2, d3 = st.columns(3)
            tipo = d1.selectbox("Tipo de documento", ["PASAPORTE", "DNI", "CARNET DE EXTRANJERÍA"])
            desde = d2.date_input("Ingreso desde", value=date(2026, 11, 1), format="DD/MM/YYYY")
            hasta = d3.date_input("Ingreso hasta", value=date(2026, 11, 9), format="DD/MM/YYYY")
        hechas = sum(bool(p["tam"]) for p in incl)
        st.progress(hechas / len(incl), text=f"TAM obtenidas: {hechas} de {len(incl)}")
        cola = [p for p in incl if not p["tam"] and not p.get("saltado")]

        izq, der = st.columns([3, 2])
        with izq:
            if not cola:
                st.success("Todas las TAM fueron procesadas. Descarga el ZIP en la pestaña 3.")
                if st.button("Reiniciar TAMs"):
                    for p in incl:
                        p["tam"] = None
                        p["saltado"] = False
                    ss.ultima_tam = None
                    st.rerun()
            else:
                p = cola[0]
                if ss.pop("cap_error", False):
                    st.error("Captcha incorrecto. Se generó uno nuevo, inténtalo otra vez.")
                if ss.cap is None:
                    nuevo_captcha()
                texto_cap, img_cap = ss.cap
                with st.container(border=True):
                    st.markdown(f"##### Pasajero {hechas + 1} de {len(incl)} · {p['nombre']}")
                    with st.form("portal", clear_on_submit=True):
                        f1, f2, f3 = st.columns(3)
                        f1.text_input("Tipo de documento", tipo, disabled=True, key=f"t_{p['numero']}")
                        f2.text_input("Número de documento", p["numero"], disabled=True, key=f"n_{p['numero']}")
                        f3.text_input("Nacionalidad", f"{p['nacionalidad']} · {mrz.PAISES.get(p['nacionalidad'], '')}",
                                      disabled=True, key=f"a_{p['numero']}")
                        k1, k2 = st.columns([1, 1])
                        k1.image(img_cap, caption="Escribe el código de la imagen y presiona Enter")
                        resp = k2.text_input("Captcha", max_chars=8)
                        enviar = st.form_submit_button("Consultar y descargar TAM", type="primary")
                if st.button("Omitir este pasajero"):
                    p["saltado"] = True
                    ss.cap = None
                    st.rerun()
                if enviar:
                    if resp.strip().upper() == texto_cap:
                        fecha = tam_demo.consultar(p["numero"], desde, hasta)
                        p["tam"] = tam_demo.generar_tam_pdf({**p, "tipo": tipo}, fecha)
                        ss.ultima_tam = (p["nombre"], p["tam"])
                        ss.cap = None
                        ss.aviso = (f"TAM descargada: {p['nombre']}", "📥")
                        st.rerun()
                    else:
                        ss.cap_error = True
                        ss.cap = None
                        st.rerun()
        with der:
            st.markdown("##### Última TAM generada")
            if ss.ultima_tam:
                st.image(pasaportes.miniatura(ss.ultima_tam[1], 0.9), caption=f"TAM {ss.ultima_tam[0]}")
            else:
                st.caption("Aquí aparecerá la TAM de cada pasajero apenas se descargue.")

# ───────────────────────── 3. ZIP ─────────────────────────
with t3:
    listos = [p for p in ss.pasajeros if p["incluir"] and p["nombre"]]
    if not listos:
        st.markdown('<div class="card"><h4>Nada que descargar todavía</h4>Cuando tengas pasaportes (y sus TAM) '
                    'aquí podrás bajar el ZIP del file.</div>', unsafe_allow_html=True)
    else:
        con_tam = sum(bool(p["tam"]) for p in listos)
        z1, z2, z3 = st.columns(3)
        z1.metric("Pasaportes", len(listos))
        z2.metric("TAM", con_tam)
        z3.metric("Pendientes de TAM", len(listos) - con_tam)
        rutas = zipper.listar(codigo, listos)
        arbol = [f'<span class="d">{codigo}/</span>']
        for r in rutas[:14]:
            parte = r.split("/", 1)[1]
            carpeta, archivo = parte.split("/", 1)
            arbol.append(f'  ├─ <span class="t">{carpeta}</span>/{archivo}')
        if len(rutas) > 14:
            arbol.append(f"  … y {len(rutas) - 14} archivos más")
        st.markdown('<div class="tree">' + "<br>".join(a.replace("  ", "&nbsp;&nbsp;") for a in arbol) + "</div>",
                    unsafe_allow_html=True)
        st.markdown("")
        st.download_button("⬇️ Descargar ZIP del file", zipper.construir_zip(codigo, listos),
                           file_name=f"{codigo}.zip", mime="application/zip", type="primary")
        if con_tam < len(listos):
            st.caption("Hay pasajeros sin TAM: el ZIP incluirá sus pasaportes y dejará sus TAM pendientes.")

st.markdown('<div class="foot">Demostración · La app procesa los archivos en memoria y no los guarda en disco</div>',
            unsafe_allow_html=True)
