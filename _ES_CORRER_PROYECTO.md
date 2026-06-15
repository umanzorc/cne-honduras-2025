# Cómo Correr el Proyecto

## Requisitos previos

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests google-generativeai anthropic openpyxl
```

- `credentials.json` de Google Cloud Console (Drive API habilitada, OAuth 2.0)
- `GOOGLE_API_KEY` configurada (para validación con Gemini)

---

## FASE 1 — Extraer datos del CNE

1. Abrir https://resultadosgenerales2025.cne.hn en Chrome/Edge
2. Presionar `F12` → pestaña **Console**
3. Pegar todo el contenido de `script_navegador_detallado_completo.js`
4. Presionar Enter, luego ejecutar:

```javascript
await extraerTodosLosDatosDetallados()
```

5. Esperar (varias horas). Al terminar, descargar:

```javascript
descargarJSON(window.resultadosCNEDetallados)
```

**Resultado**: `resultados_jrv_detallado.json`

> Para probar primero con un municipio: `await extraerUnMunicipio("18", "003")`

---

## FASE 2 — Subir actas a Google Drive

```bash
# 1. Subir los PDFs (~1 hora para 20k actas)
python subir_actas_drive_rapido.py

# 2. Agregar URLs de Drive al JSON (~5-10 min)
python agregar_urls_drive_rapido.py

# 3. Hacer archivos públicos (NECESARIO para validación con IA)
python compartir_drive_anonimo.py
```

**Resultado**: `resultados_jrv_detallado_con_urls.json`

---

## FASE 3 — Validar actas con IA

```bash
# Opción A: Gemini Flash (económico, recomendado)
export GOOGLE_API_KEY='tu-key-aqui'
python validador_gemini_flash.py

# Opción B: Claude Sonnet + Opus (máxima precisión)
export ANTHROPIC_API_KEY='tu-key-aqui'
python validador_actas_dos_fases.py
```

**Resultado**: `resultados_validados_gemini.json`

---

## Extras

```bash
# Solo extraer JRVs faltantes (si hay una extracción previa parcial)
python generar_exclusiones.py
# Luego cargar jrvs_a_excluir.js en la consola antes de ejecutar el script

# Exportar a Excel
python json_to_excel_formateado.py

# Publicar de forma segura (transferir PDFs a cuenta anónima)
python transferir_drive_a_drive.py
```

---

## Archivos sensibles (NO subir a Git)

```
credentials.json
token.json
```
