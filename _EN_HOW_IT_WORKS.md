# How It Works: Extraction and Validation of CNE Honduras 2025 Electoral Records

## What does this project do?

It extracts, validates, and backs up electoral results from the official CNE (Consejo Nacional Electoral) website of Honduras 2025. The final output is a JSON with **~19,000 JRVs** (Voting Booths) that includes:

- Votes per party at each voting booth
- Record status (correct, inconsistent, pending)
- Permanent Google Drive URL for each scanned PDF ballot
- AI cross-validation (comparing the PDF ballot against the digitized data in the CNE system)

---

## Architecture: 3 Phases

```
CNE Website
    │
    ▼
[PHASE 1] Browser JS Script
    │  script_navegador_detallado_completo.js
    │  → resultados_jrv_detallado.json
    │
    ▼
[PHASE 2] Google Drive Upload (Python)
    │  subir_actas_drive_rapido.py         → PDFs organized in Drive
    │  agregar_urls_drive_rapido.py        → Permanent URLs added to JSON
    │  compartir_drive_anonimo.py          → Files made public
    │  → resultados_jrv_detallado_con_urls.json
    │
    ▼
[PHASE 3] AI Validation (Python)
    │  validador_gemini_flash.py           → Reads each PDF with Gemini
    │  → resultados_validados_gemini.json
    │
    ▼
Final JSON: vote data + AI validation + Drive URLs
```

---

## Phase 1: Data Extraction from CNE

### Why JavaScript in the browser?
The CNE website is protected by **Nexusguard** (anti-bot). Requests from Python, C#, or Selenium are blocked. The only reliable method is to run JavaScript directly in the browser console, using the user's authentic session.

### CNE API endpoints used

**Base URL**: `https://resultadosgenerales2025-api.cne.hn`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/esc/v1/actas-documentos/01/{dept}/municipios` | GET | Municipalities in a department |
| `/esc/v1/presentacion-resultados` | POST | Votes per candidate at a JRV |
| `/esc/v1/presentacion-resultados/actas-validas` | POST | Ballot status (correct/inconsistent) |
| `/esc/v1/presentacion-resultados/votos` | POST | Null votes (997,998) and blank votes (996) |

### Extracted data structure

Each record contains the full geographic hierarchy:
```
Department → Municipality → Zone → Voting Center → JRV
```

```json
{
  "id_departamento": "08",
  "departamento": "FRANCISCO MORAZAN",
  "id_municipio": "001",
  "municipio": "TEGUCIGALPA",
  "id_zona": "01",
  "zona": "URBANA",
  "id_puesto": "042",
  "puesto": "ESCUELA REPUBLICA DE MEXICO",
  "numero_jrv": 8042,
  "votos_dc": 0,
  "votos_libre": 12,
  "votos_pinu": 1,
  "votos_liberal": 45,
  "votos_nacional": 38,
  "votos_nulos": 2,
  "votos_blanco": 1,
  "cantidad_total_actas": 1,
  "correctas": 1,
  "inconsistencias": 0,
  "error_suma": 0,
  "url_acta_pdf": "https://...s3.amazonaws.com/..."
}
```

### Available extraction scripts

| Script | Granularity | Parties | Time |
|--------|-------------|---------|------|
| `script_navegador.js` | Municipality | Nacional + Liberal | 15-20 min |
| `script_navegador_detallado_completo.js` ⭐ | JRV | All 5 + Nulls + Blank | Several hours |
| `script_navegador_jrvs_faltantes.js` | Specific JRVs | All | Variable |

### Exclusion system (incremental extraction)
If you already have 90% of JRVs processed, `generar_exclusiones.py` generates a file listing JRVs to skip. The browser script reads that file and only processes the missing ones.

---

## Phase 2: Google Drive

AWS S3 URLs **expire after 2 hours**. To have permanent access to the PDFs:

### Step 2.1: Upload PDFs
```bash
python subir_actas_drive_rapido.py
```
Downloads each PDF from S3 and uploads it to Google Drive organized by department:
```
My Drive/
  ├── ATLANTIDA/     → JRV_1001.pdf, JRV_1002.pdf ...
  ├── CORTES/        → JRV_5001.pdf ...
  └── ... (19 departments)
```

### Step 2.2: Add Drive URLs to JSON
```bash
python agregar_urls_drive_rapido.py
```
Adds a `url_drive` field to each JRV in the JSON:
```json
{
  "numero_jrv": 8042,
  "url_drive": "https://drive.google.com/file/d/1aBcD.../view?usp=sharing"
}
```

### Step 2.3: Make files public (CRITICAL for AI validation)
```bash
python compartir_drive_anonimo.py
```
Sets "anyone with the link can view" permissions so Gemini can download the PDFs.

---

## Phase 3: AI Validation

### Why validate?
The CNE digitizes votes manually. The validation compares that digitized data against the original scanned PDF ballot to detect discrepancies.

### How the AI reads a ballot

Ballots have a 3-column format for each value:
```
             BALLOTS | IN NUMBERS | IN LETTERS
Liberal:        45   |    4  5    | forty five
```

The AI prioritizes the **"IN LETTERS"** column because it is less ambiguous than handwritten digits (1 vs 7, 3 vs 5, etc.).

Correct reading example:
- "cero dos dos" = (0×100) + (2×10) + (2×1) = **22** (not 2)

### Validation fields added to the JSON

| Field | Description |
|-------|-------------|
| `pdf_votos_liberal` | Liberal votes read from the PDF |
| `pdf_votos_nacional` | Nacional votes read from the PDF |
| `pdf_votos_nulos` | Null votes read from the PDF |
| `pdf_gran_total` | Grand total read from the PDF |
| `InconsistenciaDatosDigitados` | 1 = digitized data ≠ PDF |
| `InconsistenciaGrandTotalPorVotantes` | 1 = vote sum ≠ total voters |
| `InconsistenciaPapeletas` | 1 = ballot count mismatch |
| `NumeroActaInconsistente` | 1 = QR code ≠ barcode |

### Validation options

| Script | Model | Cost (19k ballots) | Accuracy | Recommended |
|--------|-------|--------------------|----------|-------------|
| `validador_gemini_flash.py` | Gemini 2.0 Flash | $0-4 USD | ~92% | ✅ Budget-friendly |
| `validador_actas_dos_fases.py` | Sonnet 4 + Opus | ~$342 USD | ~99% | ✅ Maximum precision |

---

## Included JSON files

### `estructura_completa_cne_DEFINITIVOFEBRERO.json`
- **19,167 records** — complete structure of all JRVs in the country
- Includes all CNE extraction fields
- No Drive URLs (base structure)
- Date: February 2026

### `resultados_jrv_detallado_con_urls_TODOS_Union.json`
- **18,224 records** — union of all extractions with Google Drive URLs
- Includes `url_drive` field with permanent link to each ballot PDF
- Base file for AI validation

---

## Required setup

### Google Drive API
1. Create a project on [Google Cloud Console](https://console.cloud.google.com)
2. Enable **Google Drive API**
3. Create **OAuth 2.0** credentials (Desktop application)
4. Download as `credentials.json` in the project root

### Google AI (Gemini)
1. Get your API Key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Set it: `export GOOGLE_API_KEY='your-key'`

### Python dependencies
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests google-generativeai anthropic openpyxl
```

---

## Project stats

- **Country**: Honduras
- **Election**: Presidential 2025
- **Total JRVs**: ~19,000
- **Departments**: 19
- **Municipalities**: ~298
- **Parties captured**: DC, LIBRE, PINU, Liberal, Nacional + Nulls + Blanks
- **Development period**: December 2025 – February 2026
