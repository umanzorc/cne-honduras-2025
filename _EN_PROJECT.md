# PROJECT CONTEXT — CNE Honduras 2025 Electoral Results Extraction

## Executive Summary

This project was created to extract and consolidate the results of the Honduras 2025 elections from the CNE (Consejo Nacional Electoral) website. The goal is to produce a structured JSON file with votes per party per municipality — and ultimately per JRV (voting booth) — to facilitate projections and independent analysis.

---

## Project Goal

**Problem**: The CNE website allows querying results municipality by municipality, but it is extremely slow and tedious. Manual collection of ~298 municipalities is impractical.

**Solution**: Automatically extract all voting data from every municipality (and every JRV) in Honduras and consolidate it into a single, easy-to-analyze JSON file.

**Primary parties of interest**: Partido Nacional (parpo_id: "0005") and Partido Liberal (parpo_id: "0004"), though the final scripts capture all 5 parties plus nulls and blanks.

---

## Project Evolution

### Attempt 1: C# API with HttpClient (❌ Failed)
- **Problem**: CNE server is protected by Nexusguard (anti-bot)
- **Symptoms**: Timeouts, refused connections, HTML responses instead of JSON
- **Conclusion**: Requests from C# applications were blocked

### Attempt 2: C# API with Selenium WebDriver (❌ Failed)
- **Problem**: Geographic blocking or strict IP filtering
- **Symptoms**: Server rejects automated connections even with real browsers
- **Conclusion**: CNE blocks any automated HTTP client

### Final Solution: JavaScript in the User's Browser (✅ Works)
- **Method**: JavaScript script executed in the browser console (Edge/Chrome)
- **Advantage**: Uses the real browser session that the CNE accepts
- **Result**: 100% reliable, cannot be blocked

---

## CNE API — Endpoints Used

**Base URL**: `https://resultadosgenerales2025-api.cne.hn`

### 1. Get Municipalities of a Department
```
GET /esc/v1/actas-documentos/01/{id_departamento}/municipios
```

**Example**: `GET /esc/v1/actas-documentos/01/05/municipios`

**Response**:
```json
[
  { "id_municipio": "001", "municipio": "SAN PEDRO SULA" },
  { "id_municipio": "002", "municipio": "CHOLOMA" }
]
```

### 2. Get Votes for a Municipality / JRV
```
POST /esc/v1/presentacion-resultados
```

**Required headers**:
```
Content-Type: application/json
Authorization: Bearer null
```

**Payload**:
```json
{
  "codigos": [],
  "tipco": "01",
  "depto": "05",
  "comuna": "00",
  "mcpio": "001",
  "zona": "",
  "pesto": "",
  "mesa": 0
}
```

**Response** (abbreviated):
```json
{
  "candidatos": [
    { "parpo_id": "0005", "parpo_nombre": "PARTIDO NACIONAL", "votos": 4442 },
    { "parpo_id": "0004", "parpo_nombre": "PARTIDO LIBERAL", "votos": 5647 }
  ]
}
```

### 3. Get Valid Ballots for a JRV
```
POST /esc/v1/presentacion-resultados/actas-validas
```
Same payload as above. Returns:
```json
{
  "total": 97,
  "publicadas": 90,
  "correctas": 65,
  "inconsistencias": 25
}
```

### 4. Get Null and Blank Votes (separate endpoint)
```
POST /esc/v1/presentacion-resultados/votos
```
- Blank votes: `"codigos": ["996"]` → returns an integer
- Null votes: `"codigos": ["997", "998"]` → returns an integer

**Important**: Nulls and blanks are NOT included in the `/presentacion-resultados` response. They require separate requests.

---

## Honduras Departments (19 total)

```json
[
  { "id_departamento": "01", "departamento": "ATLANTIDA" },
  { "id_departamento": "02", "departamento": "COLON" },
  { "id_departamento": "03", "departamento": "COMAYAGUA" },
  { "id_departamento": "04", "departamento": "COPAN" },
  { "id_departamento": "05", "departamento": "CORTES" },
  { "id_departamento": "06", "departamento": "CHOLUTECA" },
  { "id_departamento": "07", "departamento": "EL PARAISO" },
  { "id_departamento": "08", "departamento": "FRANCISCO MORAZAN" },
  { "id_departamento": "09", "departamento": "GRACIAS A DIOS" },
  { "id_departamento": "10", "departamento": "INTIBUCA" },
  { "id_departamento": "11", "departamento": "ISLAS DE LA BAHIA" },
  { "id_departamento": "12", "departamento": "LA PAZ" },
  { "id_departamento": "13", "departamento": "LEMPIRA" },
  { "id_departamento": "14", "departamento": "OCOTEPEQUE" },
  { "id_departamento": "15", "departamento": "OLANCHO" },
  { "id_departamento": "16", "departamento": "SANTA BARBARA" },
  { "id_departamento": "17", "departamento": "VALLE" },
  { "id_departamento": "18", "departamento": "YORO" },
  { "id_departamento": "20", "departamento": "VOTO EN EL EXTERIOR" }
]
```

**Total municipalities**: ~298 across Honduras  
**Total JRVs (voting booths)**: ~19,000

---

## Party IDs

| ID | Party |
|----|-------|
| `"0001"` | Partido Demócrata Cristiano de Honduras (DC) |
| `"0002"` | Partido Libertad y Refundación (LIBRE) |
| `"0003"` | Partido Innovación y Unidad Social Demócrata (PINU) |
| `"0004"` | Partido Liberal de Honduras |
| `"0005"` | Partido Nacional de Honduras |
| `"996"` | Blank votes |
| `"997"`, `"998"` | Null votes |

---

## Implemented Solution: Browser Script

### The Main Script: `script_navegador_detallado_completo.js`

**What it does**:
- Iterates through all departments → municipalities → zones → voting centers → JRVs
- For each JRV: fetches votes for all 5 parties, null votes, blank votes, and ballot status
- Makes null/blank vote requests in parallel using `Promise.all`
- Saves progress automatically every 10 municipalities to `window.resultadosCNEDetallados`
- Shows real-time progress in the console

**Available extraction scripts**:
| Script | Level | Parties | Time | Notes |
|--------|-------|---------|------|-------|
| `script_navegador.js` | Municipality | PN + PL only | 15-20 min | Quick overview |
| `script_navegador_detallado_completo.js` ⭐ | JRV | All 5 + nulls/blanks | Several hours | **Recommended** |
| `script_navegador_jrvs_faltantes.js` | Specific JRVs | All | Variable | For gap-filling |

**Usage**:
```javascript
// Extract everything
await extraerTodosLosDatosDetallados()

// Extract one department
await extraerUnDepartamento("18")

// Extract one municipality (for testing)
await extraerUnMunicipio("18", "003")  // El Negrito, Yoro

// Download result
descargarJSON(window.resultadosCNEDetallados)
```

**Important**: Keep the browser tab active (do NOT switch tabs or minimize while running).

---

## Phase 2: AI Validation

### Objective
Automatically verify that the votes digitized in the CNE system match the scanned PDF ballots, using AI vision to read and compare.

### How Ballots Are Structured

Each ballot has 3 columns per value:
1. **BALLOTS**: Number of physical ballots
2. **IN NUMBERS**: Votes written as digits
3. **IN LETTERS**: Votes written as words (zero, one, two, three, etc.)

**The "IN LETTERS" column is the most reliable** because:
- It is written manually as complete words
- Less prone to transcription errors
- Digits like 1 vs 7, 3 vs 5, 0 vs 6 are often ambiguous in handwriting

### Multi-column number reading (critical)
Ballots use a positional 3-column format:
```
         COL1 (hundreds) | COL2 (tens) | COL3 (units)
Liberal:      zero       |     four    |    five      = 45
```

The AI must read all three columns and sum them:
- "cero dos dos" = (0×100) + (2×10) + (2×1) = **22** (NOT 2!)
- "cero tres cero" = (0×100) + (3×10) + (0×1) = **30** (NOT 3!)

### Fields added by the AI validator

**Votes extracted from PDF**:
- `pdf_votos_dc`, `pdf_votos_libre`, `pdf_votos_pinu`
- `pdf_votos_liberal`, `pdf_votos_nacional`
- `pdf_votos_blanco`, `pdf_votos_nulos`
- `pdf_gran_total`, `pdf_total_votantes`

**Ballot counts**:
- `pdf_papeletas_recibidas`, `pdf_papeletas_no_utilizadas`, `pdf_papeletas_utilizadas`

**QR / barcode codes**:
- `pdf_numero_acta_qr`, `pdf_numero_acta_barra`

**Inconsistency flags**:
- `InconsistenciaDatosDigitados`: 1 = digitized votes ≠ PDF
- `InconsistenciaGrandTotalPorVotantes`: 1 = vote sum ≠ total voters
- `InconsistenciaPapeletas`: 1 = ballot count mismatch
- `NumeroActaInconsistente`: 1 = QR ≠ barcode

### Validation strategies

| Script | Model | Strategy | Cost (19k) | Precision | Status |
|--------|-------|----------|-----------|-----------|--------|
| `validador_gemini_flash.py` | Gemini 2.0 Flash | All ballots | $0-4 USD | ~92% | ✅ **Recommended** |
| `validador_actas_dos_fases.py` | Sonnet 4 + Opus | Two-phase | ~$342 USD | ~99% | ✅ Max precision |
| `validador_actas_completo.py` | Sonnet 4 | All ballots | ~$60 USD | ~85-90% | ⚠️ Testing only |
| `validador_actas_hibrido.py` | OCR + Sonnet 4 | Hybrid | — | Worse | ❌ Not recommended |

### Why Gemini Flash?
- **Cost**: Virtually free (rate-limited tier) or ~$4 for all 19k ballots
- **Precision**: 90-95%, sufficient for statistical analysis
- **Important**: Uses `url_drive` (permanent) — NOT `url_acta_pdf` (expires in 2h)
- Run `compartir_drive_anonimo.py` BEFORE validating (files must be public)

### Two-Phase Strategy (Claude)
- **Phase 1**: Claude Sonnet 4 on ALL ballots → fast + cheap
- **Phase 2**: Claude Opus on ONLY the inconsistencies from Phase 1 → maximum precision
- **Combined result**: ~99% accuracy at ~78% lower cost than Opus-only

---

## Phase 3: Google Drive

### Why Google Drive?
AWS S3 URLs in the extracted JSON expire after 2 hours. Google Drive provides permanent, shareable links.

### Workflow

```bash
# 1. Upload PDFs from S3 to Drive (~1 hour async)
python subir_actas_drive_rapido.py

# 2. Add Drive URLs to JSON (~5-10 min)
python agregar_urls_drive_rapido.py

# 3. Make files public (REQUIRED before AI validation)
python compartir_drive_anonimo.py
```

### Drive structure
```
My Drive/
  ├── ATLANTIDA/     JRV_1001.pdf, JRV_1002.pdf ...
  ├── CORTES/        JRV_5001.pdf ...
  └── ... (19 departments)
```

### Rate limits
- Google Drive API: 1,000 operations per 100 seconds
- Scripts include auto-delay to stay within limits

### Setup (first time only)
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project, enable **Google Drive API**
3. Create **OAuth 2.0** credentials (Desktop app)
4. Download as `credentials.json` in project root
5. Run any Drive script — browser will open for authorization
6. `token.json` is created automatically (do not delete)

---

## Incremental Extraction System

**Problem**: With 90% of JRVs already processed, re-extracting all 19k JRVs wastes time.

**Solution**:
1. `generar_exclusiones.py` reads the current JSON and generates a JavaScript file (`jrvs_a_excluir.js`) containing a Set of already-processed JRV codes.
2. Load that file in the browser console before running the extraction script.
3. The script checks each JRV against the exclusion Set and skips it if already done.

**Result**: Only the missing ~10% of JRVs are re-extracted.

---

## Secure Publishing

See `PLAN_PUBLICACION_SEGURA.md` for detailed instructions on publishing the data anonymously. Key recommendations:
- Use Tor Browser + public WiFi for sensitive actions
- Create a dedicated anonymous Google account for Drive
- Use `transferir_drive_a_drive.py` to copy files from personal to anonymous account
- Use `limpiar_urls_drive.py` to remove identifying parameters from URLs (`ouid=...`)

---

## Key Files

### JavaScript — Phase 1 (Extraction)
| File | Description |
|------|-------------|
| `script_navegador_detallado_completo.js` ⭐ | Full extraction: all parties, all JRVs, exclusion support |
| `script_navegador.js` | Simple extraction: municipality level, Nacional + Liberal only |
| `script_navegador_jrvs_faltantes.js` | Targeted extraction for specific missing JRVs |

### Python — Phase 2 (AI Validation)
| File | Description |
|------|-------------|
| `validador_gemini_flash.py` ⭐ | Google Gemini 2.0 Flash validator (recommended) |
| `validador_actas_dos_fases.py` ⭐ | Two-phase Claude validator (max precision) |

### Python — Phase 3 (Google Drive)
| File | Description |
|------|-------------|
| `subir_actas_drive_rapido.py` ⭐ | Async PDF uploader (~1h for 20k) |
| `agregar_urls_drive_rapido.py` ⭐ | Adds Drive URLs to JSON (~5-10 min) |
| `compartir_drive_anonimo.py` | Makes Drive files publicly accessible |
| `limpiar_urls_drive.py` | Removes identifying parameters from URLs |
| `transferir_drive_a_drive.py` | Transfers files between Drive accounts |

### Python — Utilities
| File | Description |
|------|-------------|
| `generar_exclusiones.py` | Generates JRV exclusion list for incremental extraction |
| `json_to_excel_formateado.py` | Exports JSON results to formatted Excel |
| `convertir_excel_a_json.py` | Converts Excel results back to JSON |

### JSON Data Files
| File | Records | Description |
|------|---------|-------------|
| `estructura_completa_cne_DEFINITIVOFEBRERO.json` | 19,167 | Complete CNE structure — Feb 2026 (most complete) |
| `resultados_jrv_detallado_con_urls_TODOS_Union.json` | 18,224 | All results with permanent Google Drive URLs |

### Sensitive files (do NOT commit to Git)
- `credentials.json` — Google Cloud OAuth credentials
- `token.json` — Saved authentication token

---

## Complete Recommended Workflow

```
Step 1  → script_navegador_detallado_completo.js (browser)
             ↓ resultados_jrv_detallado.json

Step 2  → subir_actas_drive_rapido.py
             ↓ PDFs in Google Drive

Step 3  → agregar_urls_drive_rapido.py
             ↓ resultados_jrv_detallado_con_urls.json

Step 4  → compartir_drive_anonimo.py  ← CRITICAL before Step 5
             ↓ Files publicly accessible

Step 5  → validador_gemini_flash.py
             ↓ resultados_validados_gemini.json

Step 6  → (optional) generar_exclusiones.py + re-run browser script
             for any JRVs missed in Step 1
```

---

## Key Lessons Learned

1. **Direct AI beats hybrid OCR**: Claude reading PDFs directly outperforms Tesseract OCR → text → AI
2. **Explicit examples are critical**: Edge cases like "cero dos dos" = 22 must be demonstrated in the prompt
3. **Two-phase strategy is optimal**: Use cheap model first, premium only for flagged cases
4. **Cross-validation helps**: Comparing "IN NUMBERS" vs "IN LETTERS" columns reduces errors
5. **Handwriting variability is the main challenge**: Ambiguous digits (1/7, 3/5, 0/6) cause most errors
6. **AWS S3 URLs expire in 2 hours**: Run Drive upload scripts immediately after extraction

---

## Project Stats

- **Country**: Honduras
- **Election**: Presidential 2025
- **Total JRVs**: ~19,000
- **Departments**: 19
- **Municipalities**: ~298
- **Development period**: December 2025 – February 2026
- **Final dataset**: 19,167 JRVs (Feb 2026)

---

*Document created: 2025-12-04*
*Last updated: 2026-02-01*
*Version: 5.0 — English translation added*
