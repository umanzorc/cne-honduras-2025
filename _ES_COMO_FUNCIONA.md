# Cómo Funciona: Extracción y Validación de Actas CNE Honduras 2025

## ¿Qué hace este proyecto?

Extrae, valida y respalda los resultados electorales del sitio oficial del CNE (Consejo Nacional Electoral) de Honduras 2025. El resultado final es un JSON con **~19,000 JRVs** (Juntas Receptoras de Votos) que incluye:

- Votos por partido en cada mesa de votación
- Estado de las actas (correcta, inconsistente, en espera)
- URL del PDF del acta escaneada en Google Drive
- Validación cruzada con IA (leyendo el PDF real vs los datos digitados en el sistema)

---

## Arquitectura: 3 Fases

```
CNE Website
    │
    ▼
[FASE 1] Script JS en Navegador
    │  script_navegador_detallado_completo.js
    │  → resultados_jrv_detallado.json
    │
    ▼
[FASE 2] Subida a Google Drive (Python)
    │  subir_actas_drive_rapido.py         → PDFs organizados en Drive
    │  agregar_urls_drive_rapido.py        → URLs permanentes en el JSON
    │  compartir_drive_anonimo.py          → Archivos públicos
    │  → resultados_jrv_detallado_con_urls.json
    │
    ▼
[FASE 3] Validación con IA (Python)
    │  validador_gemini_flash.py           → Lee cada PDF con Gemini
    │  → resultados_validados_gemini.json
    │
    ▼
JSON Final: datos + validación + URLs Drive
```

---

## Fase 1: Extracción del CNE

### Por qué JavaScript en el navegador
El sitio del CNE está protegido por **Nexusguard** (anti-bot). Las peticiones desde Python, C# o Selenium son bloqueadas. El único método que funciona es ejecutar JavaScript directamente en la consola del navegador, usando la sesión auténtica del usuario.

### Endpoints del CNE utilizados

**Base URL**: `https://resultadosgenerales2025-api.cne.hn`

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/esc/v1/actas-documentos/01/{depto}/municipios` | GET | Municipios de un departamento |
| `/esc/v1/presentacion-resultados` | POST | Votos por candidato en una JRV |
| `/esc/v1/presentacion-resultados/actas-validas` | POST | Estado del acta (correcta/inconsistente) |
| `/esc/v1/presentacion-resultados/votos` | POST | Votos nulos (997,998) y en blanco (996) |

### Estructura de datos extraídos

Cada registro tiene la jerarquía completa:
```
Departamento → Municipio → Zona → Centro de Votación → JRV
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

### Scripts de extracción disponibles

| Script | Nivel | Partidos | Tiempo |
|--------|-------|----------|--------|
| `script_navegador.js` | Municipio | Nacional + Liberal | 15-20 min |
| `script_navegador_detallado_completo.js` ⭐ | JRV | Todos (5) + Nulos + Blanco | Varias horas |
| `script_navegador_jrvs_faltantes.js` | JRV específicas | Todos | Variable |

### Sistema de exclusiones (extracción incremental)
Si ya tienes el 90% de JRVs procesadas, `generar_exclusiones.py` genera un archivo con las JRVs a saltar. El script del navegador lee ese archivo y solo procesa las que faltan.

---

## Fase 2: Google Drive

Las URLs de AWS S3 **expiran en 2 horas**. Para tener acceso permanente a los PDFs:

### Paso 2.1: Subir los PDFs
```bash
python subir_actas_drive_rapido.py
```
Descarga cada PDF desde S3 y lo sube a Google Drive organizado por departamento:
```
Mi Unidad/
  ├── ATLANTIDA/     → JRV_1001.pdf, JRV_1002.pdf ...
  ├── CORTES/        → JRV_5001.pdf ...
  └── ... (19 departamentos)
```

### Paso 2.2: Agregar URLs al JSON
```bash
python agregar_urls_drive_rapido.py
```
Agrega el campo `url_drive` a cada JRV en el JSON:
```json
{
  "numero_jrv": 8042,
  "url_drive": "https://drive.google.com/file/d/1aBcD.../view?usp=sharing"
}
```

### Paso 2.3: Hacer archivos públicos (CRÍTICO para validación)
```bash
python compartir_drive_anonimo.py
```
Establece permisos de "cualquiera con el enlace puede ver" para que Gemini pueda descargar los PDFs.

---

## Fase 3: Validación con IA

### Por qué validar
El CNE digitaliza los votos manualmente. La validación compara esos datos digitados contra el PDF escaneado del acta original para detectar discrepancias.

### Cómo lee el acta la IA

Las actas tienen un formato de 3 columnas por cada dato:
```
             PAPELETAS  | EN NÚMEROS | EN LETRAS
Liberal:         45     |     4  5   |  cuarenta cinco
```

La IA prioriza la columna **"EN LETRAS"** porque es menos ambigua que los dígitos escritos a mano (1 vs 7, 3 vs 5, etc.).

Ejemplo de lectura correcta:
- "cero dos dos" = (0×100) + (2×10) + (2×1) = **22** (no 2)

### Campos de validación agregados al JSON

| Campo | Descripción |
|-------|-------------|
| `pdf_votos_liberal` | Votos Liberal leídos del PDF |
| `pdf_votos_nacional` | Votos Nacional leídos del PDF |
| `pdf_votos_nulos` | Votos nulos leídos del PDF |
| `pdf_gran_total` | Gran total leído del PDF |
| `InconsistenciaDatosDigitados` | 1 = datos digitados ≠ PDF |
| `InconsistenciaGrandTotalPorVotantes` | 1 = suma de votos ≠ total votantes |
| `InconsistenciaPapeletas` | 1 = papeletas no cuadran |
| `NumeroActaInconsistente` | 1 = QR ≠ código de barras |

### Opciones de validación

| Script | Modelo | Costo (19k actas) | Precisión | Recomendado |
|--------|--------|-------------------|-----------|-------------|
| `validador_gemini_flash.py` | Gemini 2.0 Flash | $0-4 USD | ~92% | ✅ Económico |
| `validador_actas_dos_fases.py` | Sonnet 4 + Opus | ~$342 USD | ~99% | ✅ Máxima precisión |

---

## Archivos JSON incluidos

### `estructura_completa_cne_DEFINITIVOFEBRERO.json`
- **19,167 registros** — estructura completa de todas las JRVs del país
- Incluye todos los campos de extracción del CNE
- Sin URLs de Drive (estructura base)
- Fecha: Febrero 2026

### `resultados_jrv_detallado_con_urls_TODOS_Union.json`
- **18,224 registros** — unión de todas las extracciones con URLs de Google Drive
- Incluye campo `url_drive` con enlace permanente al PDF del acta
- Base para validación con IA

---

## Configuración necesaria

### Google Drive API
1. Crear proyecto en [Google Cloud Console](https://console.cloud.google.com)
2. Habilitar **Google Drive API**
3. Crear credenciales **OAuth 2.0** (Aplicación de escritorio)
4. Descargar como `credentials.json` en la raíz del proyecto

### Google AI (Gemini)
1. Obtener API Key en [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Configurar: `export GOOGLE_API_KEY='tu-key'`

### Dependencias Python
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests google-generativeai anthropic openpyxl
```

---

## Datos del proyecto

- **País**: Honduras
- **Elección**: Presidencial 2025
- **Total JRVs**: ~19,000
- **Departamentos**: 19
- **Municipios**: ~298
- **Partidos capturados**: DC, LIBRE, PINU, Liberal, Nacional + Nulos + Blancos
- **Período de trabajo**: Diciembre 2025 – Febrero 2026
