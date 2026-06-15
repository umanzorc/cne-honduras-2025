# How to Run the Project

## Prerequisites

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests google-generativeai anthropic openpyxl
```

- `credentials.json` from Google Cloud Console (Drive API enabled, OAuth 2.0)
- `GOOGLE_API_KEY` set (for Gemini validation)

---

## PHASE 1 — Extract data from CNE

1. Open https://resultadosgenerales2025.cne.hn in Chrome/Edge
2. Press `F12` → **Console** tab
3. Paste the full contents of `script_navegador_detallado_completo.js`
4. Press Enter, then run:

```javascript
await extraerTodosLosDatosDetallados()
```

5. Wait (several hours). When done, download:

```javascript
descargarJSON(window.resultadosCNEDetallados)
```

**Output**: `resultados_jrv_detallado.json`

> To test with a single municipality first: `await extraerUnMunicipio("18", "003")`

---

## PHASE 2 — Upload ballots to Google Drive

```bash
# 1. Upload the PDFs (~1 hour for 20k ballots)
python subir_actas_drive_rapido.py

# 2. Add Drive URLs to the JSON (~5-10 min)
python agregar_urls_drive_rapido.py

# 3. Make files public (REQUIRED for AI validation)
python compartir_drive_anonimo.py
```

**Output**: `resultados_jrv_detallado_con_urls.json`

---

## PHASE 3 — Validate ballots with AI

```bash
# Option A: Gemini Flash (cheap, recommended)
export GOOGLE_API_KEY='your-key-here'
python validador_gemini_flash.py

# Option B: Claude Sonnet + Opus (maximum precision)
export ANTHROPIC_API_KEY='your-key-here'
python validador_actas_dos_fases.py
```

**Output**: `resultados_validados_gemini.json`

---

## Extras

```bash
# Extract only missing JRVs (if you have a partial previous extraction)
python generar_exclusiones.py
# Then load jrvs_a_excluir.js in the console before running the script

# Export results to Excel
python json_to_excel_formateado.py

# Secure publishing (transfer PDFs to an anonymous account)
python transferir_drive_a_drive.py
```

---

## Sensitive files (do NOT commit to Git)

```
credentials.json
token.json
```
