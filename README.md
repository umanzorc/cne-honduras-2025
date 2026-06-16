# Electoral Records Extraction & Validation — CNE Honduras 2025

> Personal project developed between December 2025 and February 2026.

---

## What is this?

The official CNE (Honduras Electoral Council) website publishes 2025 election results municipality by municipality — but offers no way to download all data at once. This project automates that extraction and goes one step further: **it uses AI to validate each scanned ballot** and detect discrepancies between the data entered into the system and what the physical document actually says.

---

## Included Data

| File | Records | Description |
|------|---------|-------------|
| `estructura_completa_cne_DEFINITIVOFEBRERO.json` | **19,167 JRVs** | Complete CNE structure — Feb 2026 |
| `resultados_jrv_detallado_con_urls_TODOS_Union.json` | **18,224 JRVs** | Results with permanent Google Drive URLs |

Each JRV (voting booth) record includes:
- Votes for all 5 political parties + null votes + blank votes
- Ballot status (correct, inconsistent, pending)
- Permanent Google Drive URL to the scanned ballot PDF
- AI validation fields (digitized data vs scanned PDF)

---

## How it works

```
CNE Website
        │
        ▼
  [1] Browser JS Script
        │   script_navegador_detallado_completo.js
        │   → ~19,000 JRVs extracted
        ▼
  [2] Upload to Google Drive
        │   subir_actas_drive_rapido.py
        │   agregar_urls_drive_rapido.py
        │   → permanent URLs added to JSON
        ▼
  [3] AI Validation
        │   validador_gemini_flash.py  (Gemini 2.0 Flash — $0-4 USD)
        │   validador_actas_dos_fases.py  (Claude Sonnet + Opus — ~99% accuracy)
        ▼
  Final JSON: vote data + AI validation + Drive URLs
```

**Why JavaScript in the browser:**  
The CNE API is protected by Nexusguard (anti-bot). Python, C#, and Selenium are all blocked. The only reliable method is running the script in the browser console, using the user's authentic session.

---

## Project structure

```
/
├── README.md
│
├── _ES_COMO_FUNCIONA.md          ← detailed technical guide (Spanish)
├── _EN_HOW_IT_WORKS.md           ← detailed technical guide (English)
│
├── _ES_CORRER_PROYECTO.md        ← run commands (Spanish)
├── _EN_HOW_TO_RUN.md             ← run commands (English)
│
├── _ES_PROYECTO.md               ← full project context (Spanish)
├── _EN_PROJECT.md                ← full project context (English)
│
├── script_navegador_detallado_completo.js   ← full extraction per JRV
├── script_navegador.js                      ← fast extraction per municipality
├── script_navegador_jrvs_faltantes.js       ← extraction for missing JRVs
│
├── validador_gemini_flash.py          ← AI validation with Gemini (recommended)
├── validador_actas_dos_fases.py       ← AI validation with Claude (max precision)
│
├── subir_actas_drive_rapido.py        ← async PDF uploader to Google Drive
├── agregar_urls_drive_rapido.py       ← adds Drive URLs to JSON
├── compartir_drive_anonimo.py         ← makes Drive files publicly accessible
├── limpiar_urls_drive.py              ← cleans identifying parameters from URLs
├── transferir_drive_a_drive.py        ← transfers files between Drive accounts
│
├── generar_exclusiones.py             ← incremental extraction support
├── json_to_excel_formateado.py        ← export results to Excel
├── convertir_excel_a_json.py          ← convert Excel back to JSON
│
├── estructura_completa_cne_DEFINITIVOFEBRERO.json    ← 19,167 JRVs
├── resultados_jrv_detallado_con_urls_TODOS_Union.json ← 18,224 JRVs + URLs
│
└── EjemploActas/                      ← sample ballot images
    ├── EjemploActa1.png
    └── ...
```

---

## Quick start

**Step 1** — Open the CNE site in Chrome/Edge and run in the console:
```javascript
// Paste script_navegador_detallado_completo.js in the console, then:
await extraerTodosLosDatosDetallados()
```

**Step 2** — Upload to Drive:
```bash
python subir_actas_drive_rapido.py
python agregar_urls_drive_rapido.py
python compartir_drive_anonimo.py
```

**Step 3** — Validate with AI:
```bash
export GOOGLE_API_KEY='your-key'
python validador_gemini_flash.py
```

See `_EN_HOW_TO_RUN.md` for full instructions.

---

## Technologies

- **Extraction**: JavaScript (browser console)
- **AI Validation**: Google Gemini 2.0 Flash · Claude Sonnet 4 · Claude Opus 4
- **Storage**: Google Drive API (Python)
- **Languages**: JavaScript · Python

---

## Important notes

- `credentials.json` and `token.json` are **not included** (personal Google credentials).
- The Gemini API key is set as an environment variable, not hardcoded.
- Data comes from the official public CNE website.

---

## Context

Honduras held general elections in November 2025. The CNE published results on its website but without a public bulk-download API. This project was built to analyze data at a granular level (per voting booth) and verify its integrity by comparing digital records against the physical scanned documents.

---

*Developed by: Carlos Umanzor*  
*Period: December 2025*
