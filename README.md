# Pasaportes y TAM (demo web)

Flujo: PDFs de pasaportes → separa por pasajero → lee la MRZ → tabla editable →
TAM en portal SIMULADO (captcha manual) → ZIP `CODIGO/PASAPORTES` + `CODIGO/TAMS`.

## Probar en tu PC
    pip install -r requirements.txt
    (instalar Tesseract OCR: Windows = instalador UB-Mannheim y agregarlo al PATH)
    streamlit run app.py

## Publicar para la exposición (Streamlit Community Cloud, gratis)
1. Sube esta carpeta a un repositorio de GitHub (app.py en la raíz).
2. En share.streamlit.io elige el repo y `app.py`. No hace falta `packages.txt`.
3. Abre el link desde otra PC y prueba con "Usar pasaportes de ejemplo".

## Notas
- Solo datos FICTICIOS en la web. La TAM generada es de demostración, sin validez.
- La conexión con el portal real de Migraciones irá en la versión de escritorio.
- `make_samples.py` genera `pasaportes_prueba.pdf` (8 pasaportes ficticios con MRZ válida).

## Windows (VS Code)
1. Descomprime y abre la carpeta en VS Code (Archivo → Abrir carpeta).
2. Terminal de VS Code: `pip install -r requirements.txt`
3. No hace falta instalar nada más: el lector OCR (RapidOCR) se instala con pip.
   `C:\Program Files\Tesseract-OCR`; sin él, los pasaportes se completan a mano.
4. `streamlit run app.py` → se abre en el navegador.
