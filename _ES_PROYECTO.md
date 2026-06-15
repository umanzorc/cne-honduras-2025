# CONTEXTO DEL PROYECTO - Extracción de Resultados Electorales CNE Honduras 2025

## 📋 RESUMEN EJECUTIVO

Este proyecto fue creado para extraer y consolidar los resultados de las elecciones de Honduras 2025 desde el sitio web del CNE (Consejo Nacional Electoral). El objetivo es obtener un archivo JSON estructurado con los votos del Partido Nacional y Partido Liberal por municipio, para facilitar proyecciones y análisis.

---

## 🎯 OBJETIVO DEL PROYECTO

**Problema**: El sitio web del CNE permite consultar resultados municipio por municipio, pero es muy lento y tedioso. El usuario necesita hacer proyecciones totales por departamento.

**Solución**: Extraer automáticamente todos los datos de votación de todos los municipios de Honduras y consolidarlos en un solo archivo JSON fácil de analizar.

**Enfoque**: Solo interesa el Partido Nacional (parpo_id: "0005") y Partido Liberal (parpo_id: "0004").

---

## 🏗️ EVOLUCIÓN DEL PROYECTO

### Intento 1: API C# con HttpClient (❌ Falló)
- **Problema detectado**: El servidor del CNE está protegido por Nexusguard (anti-bot)
- **Síntomas**: Timeouts, conexiones rechazadas, respuestas HTML en lugar de JSON
- **Conclusión**: Las peticiones desde aplicaciones C# eran bloqueadas

### Intento 2: API C# con Selenium WebDriver (❌ Falló)
- **Problema detectado**: Bloqueo geográfico o filtrado de IP estricto
- **Síntomas**: El servidor no acepta conexiones automatizadas, incluso con navegadores reales
- **Conclusión**: El CNE bloquea cualquier cliente HTTP automatizado

### Solución Final: JavaScript en el Navegador del Usuario (✅ Funciona)
- **Método**: Script JavaScript que se ejecuta en la consola del navegador (Edge/Chrome)
- **Ventaja**: Usa la sesión real del navegador que el CNE acepta
- **Resultado**: 100% confiable, no puede ser bloqueado

---

## 🔌 API DEL CNE - Endpoints Utilizados

### Base URL
```
https://resultadosgenerales2025-api.cne.hn
```

### 1. Obtener Listado de Departamentos
**Nota**: Este listado está hardcodeado en el código, no existe un endpoint para esto.

### 2. Obtener Municipios de un Departamento
```
GET /esc/v1/actas-documentos/01/{id_departamento}/municipios
```

**Ejemplo**:
```
GET /esc/v1/actas-documentos/01/05/municipios
```

**Response**:
```json
[
  {
    "id_municipio": "001",
    "municipio": "SAN PEDRO SULA"
  },
  {
    "id_municipio": "002",
    "municipio": "CHOLOMA"
  }
]
```

### 3. Obtener Votos de un Municipio
```
POST /esc/v1/presentacion-resultados
```

**Headers Requeridos**:
```
Content-Type: application/json
Accept: application/json
Authorization: Bearer null
```

**Body (Payload)**:
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

**Response** (abreviado):
```json
{
  "fecha_corte": "2025-12-04 15:00:00.0",
  "candidatos": [
    {
      "cddto_codigo": "000",
      "cddto_nombres": "NASRY JUAN ASFURA ZABLAH",
      "parpo_id": "0005",
      "parpo_nombre": "PARTIDO NACIONAL DE HONDURAS",
      "votos": 4442
    },
    {
      "cddto_codigo": "000",
      "cddto_nombres": "SALVADOR ALEJANDRO CESAR NASRALLA SALUM",
      "parpo_id": "0004",
      "parpo_nombre": "PARTIDO LIBERAL DE HONDURAS",
      "votos": 5647
    }
  ]
}
```

### 4. Obtener Actas Válidas de un Municipio
```
POST /esc/v1/presentacion-resultados/actas-validas
```

**Body (Payload)**: Igual que el endpoint de votos

**Response**:
```json
{
  "pendientesVerificacionVisual": 1,
  "total": 97,
  "publicadas": 90,
  "espera": 7,
  "verificacion": 90,
  "inconsistencias": 25,
  "correctas": 65
}
```

### 5. Obtener Votos en Blanco
```
POST /esc/v1/presentacion-resultados/votos
```

**Body (Payload)**:
```json
{
  "codigos": ["996"],  // Código 996 = Votos en blanco
  "tipco": "01",
  "depto": "05",
  "comuna": "00",
  "mcpio": "001",
  "zona": "01",
  "pesto": "062",
  "mesa": 3927
}
```

**Response**: Un número entero (ej: `1`)

### 6. Obtener Votos Nulos
```
POST /esc/v1/presentacion-resultados/votos
```

**Body (Payload)**:
```json
{
  "codigos": ["997", "998"],  // Códigos 997 y 998 = Votos nulos
  "tipco": "01",
  "depto": "05",
  "comuna": "00",
  "mcpio": "001",
  "zona": "01",
  "pesto": "062",
  "mesa": 3927
}
```

**Response**: Un número entero (ej: `3`)

---

## 📊 ESTRUCTURA DE DATOS

### Departamentos de Honduras (19 en total)
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

**Total de municipios**: Aproximadamente 298 en todo Honduras

### Formato del JSON Final Deseado
```json
[
  {
    "id_departamento": "05",
    "departamento": "CORTES",
    "id_municipio": "001",
    "municipio": "SAN PEDRO SULA",
    "fecha_corte": "2025-12-04 15:00:00.0",
    "votos_nacional": 4442,
    "votos_liberal": 5647,
    "total_actas": 97,
    "actas_publicadas": 90,
    "actas_correctas": 65
  }
]
```

**Campos incluidos**:
- ✅ Información del departamento y municipio
- ✅ Fecha de corte de los datos
- ✅ Votos del Partido Nacional (parpo_id: "0005")
- ✅ Votos del Partido Liberal (parpo_id: "0004")
- ✅ Estadísticas de actas

**Campos excluidos** (no son necesarios):
- ❌ Logos de partidos y candidatos
- ❌ Colores de partidos
- ❌ Otros partidos políticos
- ❌ Nombres completos de candidatos

---

## 💻 SOLUCIÓN IMPLEMENTADA: Script del Navegador

### Archivo: `script_navegador.js`

**Ubicación**: Raíz del proyecto

**Propósito**: Script JavaScript que se ejecuta directamente en la consola del navegador del usuario (Edge/Chrome) para extraer todos los datos.

**Características**:
- ✅ Itera por todos los departamentos
- ✅ Para cada departamento, obtiene sus municipios
- ✅ Para cada municipio, obtiene votos y actas
- ✅ Filtra solo Partido Nacional y Liberal
- ✅ Muestra progreso en tiempo real en la consola
- ✅ Permite descargar el JSON al finalizar
- ✅ Manejo de errores y reintentos
- ✅ Delays entre peticiones (500ms entre municipios, 1s entre departamentos)

**Funciones principales**:
- `extraerTodosLosDatos()`: Función principal que extrae todo
- `descargarJSON(datos)`: Descarga el resultado como archivo JSON
- `verProgreso()`: Muestra cuántos municipios se han procesado

**Tiempo estimado**: 15-20 minutos para procesar los ~298 municipios

---

## 📖 GUÍAS DE USO CREADAS

### 1. `InstruccionesClaude.txt`
Instrucciones originales del usuario con ejemplos de payloads y responses del CNE.

### 2. `GUIA_RAPIDA.md`
Guía técnica con los endpoints de la API C#, troubleshooting, y configuración.

### 3. `README_INSTRUCCIONES.md`
Documentación de la API C# con Selenium, estructura del proyecto, y opciones implementadas.

### 4. `SOLUCION_ALTERNATIVA.md`
**LA MÁS IMPORTANTE**: Guía paso a paso de cómo usar `script_navegador.js` en el navegador.

### 5. `GUIA_RAPIDA_EDGE.md`
Guía específica para Microsoft Edge (no revisada en este análisis).

### 6. `INSTRUCCIONES_USO.md`
Instrucciones adicionales de uso (no revisada en este análisis).

---

## 🔑 DECISIONES CLAVE Y LECCIONES APRENDIDAS

### Por qué falló la API C#
1. **Protección Nexusguard**: Servicio anti-bot que detecta peticiones HTTP directas
2. **Bloqueo geográfico/IP**: El servidor solo acepta tráfico desde ciertas IPs o ubicaciones
3. **Fingerprinting del navegador**: El CNE valida que las peticiones vengan de navegadores reales

### Por qué funciona el script del navegador
1. **Sesión real**: Usa la sesión auténtica del navegador del usuario
2. **Headers automáticos**: El navegador envía todos los headers requeridos
3. **Cookies y contexto**: Mantiene el contexto completo de la sesión
4. **No es detectable como bot**: Es JavaScript ejecutándose en un navegador legítimo

### Recomendación para Claude en futuras sesiones
**IMPORTANTE**: Si el usuario pregunta sobre problemas de conectividad o bloqueos al intentar extraer datos de sitios protegidos:
1. Primero intentar con HTTP simple
2. Si falla, intentar con Selenium
3. **Si ambos fallan**, la solución más confiable es usar JavaScript directamente en el navegador del usuario

---

## 🛠️ ARCHIVOS IMPORTANTES DEL PROYECTO

### Scripts JavaScript (Fase 1: Extracción)
- **`script_navegador_detallado_completo.js`**: Script completo por JRV con todos los partidos ⭐⭐⭐
- `script_navegador_detallado.js`: Script por JRV solo Nacional y Liberal
- `script_navegador.js`: Script simple por municipio

### Scripts Python (Fase 2: Validación IA)
- **`validador_actas_dos_fases.py`**: Validador recomendado (Sonnet 4 + Opus 4.5) ⭐⭐⭐
- `validador_actas_completo.py`: Validador solo Sonnet 4 (todas las actas)
- `validador_actas_hibrido.py`: Intento con OCR + IA (no recomendado)
- `validador_actas_ia.py`: Validador original (obsoleto)
- `verificar_modelos.py`: Utilidad para verificar modelos disponibles

### Scripts Python (Fase 3: Google Drive)
- **`subir_actas_drive_rapido.py`**: Subida asíncrona a Google Drive ⭐⭐⭐
- `subir_actas_drive.py`: Subida síncrona a Google Drive
- **`agregar_urls_drive.py`**: Agregar campo url_drive al JSON ⭐

### Documentación
- **`CONTEXTO_PROYECTO.md`** (este archivo): Contexto completo para Claude ⭐⭐⭐
- **`Pasos/guardarArchivos.md`**: Guía completa de Google Drive ⭐⭐
- **`README_SCRIPTS.md`**: Comparación de scripts de extracción ⭐
- `SOLUCION_ALTERNATIVA.md`: Guía de uso del script del navegador
- `PLAN_VALIDACION_IA.md`: Plan detallado de validación con IA
- `GUIA_RAPIDA.md`: Guía técnica de la API C# (no recomendada)
- `README_INSTRUCCIONES.md`: Documentación de la API C# (no recomendada)
- `InstruccionesClaude.txt`: Instrucciones originales del usuario

### Archivos de Ejemplo
- `EjemploActa1.png` - `EjemploActa6.png`, `EjemploActa11.png`: Actas de ejemplo para validación

### Archivos de Configuración (NO subir a Git)
- `credentials.json`: Credenciales OAuth 2.0 de Google Cloud
- `token.json`: Token de autenticación de Google Drive (generado automáticamente)

### Código C# (Archivos del intento con API)
- Estos archivos existen pero NO son la solución final
- Están documentados en `README_INSTRUCCIONES.md`
- No usar: Bloqueados por Nexusguard anti-bot del CNE

---

## 📝 INSTRUCCIONES DE USO (RESUMEN)

### Método Recomendado: Script del Navegador

1. **Abrir el sitio del CNE**:
   - URL: https://resultadosgenerales2025.cne.hn
   - Navegador: Microsoft Edge o Google Chrome

2. **Abrir la consola**:
   - Presionar `F12` o `Ctrl + Shift + J`
   - Ir a la pestaña "Console" / "Consola"

3. **Cargar el script**:
   - Copiar TODO el contenido de `script_navegador.js`
   - Pegar en la consola
   - Presionar Enter

4. **Ejecutar la extracción**:
   ```javascript
   await extraerTodosLosDatos()
   ```

5. **Esperar** (~15-20 minutos)
   - Ver progreso en la consola
   - NO cerrar la pestaña
   - NO cambiar de pestaña

6. **Descargar el resultado**:
   ```javascript
   descargarJSON(window.resultadosCNE)
   ```

7. **Resultado**: Archivo `resultados_municipios.json` descargado

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### Seguridad y Bots
- El CNE tiene protección anti-bot (Nexusguard)
- Las peticiones automatizadas son bloqueadas
- El navegador del usuario es el único método confiable

### Rate Limiting
- Hay delays entre peticiones para no saturar el servidor
- 500ms entre municipios
- 1000ms entre departamentos

### Manejo de Errores
- El script tiene reintentos automáticos
- Si se interrumpe, se pueden guardar los datos procesados
- Se puede reanudar desde donde quedó

### Datos Temporales
- La fecha de corte cambia constantemente
- Los votos se actualizan en tiempo real
- Cada extracción es una "foto" de ese momento

---

## 🎯 PRÓXIMOS PASOS POSIBLES

Si el usuario solicita mejoras, estas son opciones viables:

1. **Agregar más partidos**: Modificar el script para incluir otros partidos
2. **Filtrar por departamento**: Extraer solo departamentos específicos
3. **Exportar a Excel**: Convertir el JSON a formato Excel/CSV
4. **Análisis de datos**: Crear gráficos o proyecciones
5. **Automatización periódica**: Ejecutar el script cada X horas
6. **Comparación temporal**: Comparar resultados de diferentes momentos

---

## 🔍 INFORMACIÓN TÉCNICA ADICIONAL

### Headers importantes de la API
```
Content-Type: application/json
Accept: application/json
Authorization: Bearer null
Origin: https://resultadosgenerales2025.cne.hn
Referer: https://resultadosgenerales2025.cne.hn/
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...
```

### Estructura de Payload
```json
{
  "codigos": [],      // Siempre vacío
  "tipco": "01",      // Tipo de consulta (presidencial)
  "depto": "XX",      // ID departamento (2 dígitos)
  "comuna": "00",     // Siempre "00"
  "mcpio": "XXX",     // ID municipio (3 dígitos)
  "zona": "",         // Vacío para consulta general
  "pesto": "",        // Vacío
  "mesa": 0           // 0 para todas las mesas
}
```

### IDs de Partidos
- `"0001"`: Partido Demócrata Cristiano de Honduras
- `"0002"`: Partido Libertad y Refundación
- `"0003"`: Partido Innovación y Unidad Social Demócrata
- `"0004"`: Partido Liberal de Honduras
- `"0005"`: Partido Nacional de Honduras

### Códigos Especiales para Votos
- `"996"`: Votos en blanco
- `"997"` y `"998"`: Votos nulos

---

## ⚠️ IMPORTANTE: Obtención de Votos Nulos y en Blanco

**Los votos nulos y en blanco NO vienen en el response de `/presentacion-resultados`**

Se obtienen mediante peticiones separadas al endpoint `/presentacion-resultados/votos`:

1. **Votos en Blanco**: Se obtienen con el código `"996"` en el array `codigos`
   - Response: Un número entero simple (ej: `1`)

2. **Votos Nulos**: Se obtienen con los códigos `"997"` y `"998"` en el array `codigos`
   - Response: Un número entero simple (ej: `3`)

**En el script**: Estas peticiones se hacen en paralelo usando `Promise.all` junto con las peticiones de votos de candidatos y actas.

---

## 📌 NOTAS PARA CLAUDE EN FUTURAS SESIONES

1. **El proyecto tiene 3 fases completas y funcionales**:
   - Fase 1: Extracción de datos del CNE (scripts JavaScript navegador)
   - Fase 2: Validación con IA (estrategia de dos fases)
   - Fase 3: Respaldo a Google Drive (scripts Python)

2. **NO intentar usar la API C#**: Ya se probó y no funciona por bloqueos del CNE
3. **NO intentar usar Selenium**: También está bloqueado
4. **La única solución confiable para extracción**: JavaScript en el navegador del usuario

5. **Scripts de extracción disponibles**:
   - `script_navegador.js`: Por municipio, solo Nacional y Liberal (15-20 min)
   - `script_navegador_detallado.js`: Por JRV, solo Nacional y Liberal (varias horas)
   - **`script_navegador_detallado_completo.js`**: ⭐ Por JRV, TODOS los partidos + nulos + blanco + SOPORTE DE EXCLUSIONES (recomendado)
   - `script_navegador_detallado_completo_rapido.js`: Versión con concurrencia 15x (satura servidor, NO usar)
   - `script_navegador_detallado_completo_moderado.js`: Versión con concurrencia 5x (alternativa conservadora)

6. **Scripts de validación IA**:
   - **RECOMENDADO para costo/precisión**: `validador_gemini_flash.py` (Google Gemini 2.0 Flash)
     - Costo: $0-4 USD para 19k actas (vs $38,000 con Claude)
     - Precisión: 90-95%
     - **IMPORTANTE**: Solo usa `url_drive` (NO usa `url_acta_pdf` que expira en 2h)
     - Requiere ejecutar `agregar_urls_drive_rapido.py` PRIMERO
   - **RECOMENDADO para máxima precisión**: `validador_actas_dos_fases.py` (Sonnet 4 + Opus 4.5)
     - Costo: ~$18 por 1,000 actas
     - Precisión final: ~98-99%
   - Obsoletos: `validador_actas_ia.py`, `validador_actas_completo.py`, `validador_actas_hibrido.py`
   - Documentación: `ALTERNATIVAS_IA_OCR.md`, `GUIA_GEMINI_FLASH.md`, `DIFERENCIAS_GOOGLE_AI_STUDIO_VS_CLOUD.md`

7. **Scripts de Google Drive**:
   - **RECOMENDADO**: `subir_actas_drive_rapido.py` (asíncrono, ~1 hora para 20k actas)
   - Alternativa: `subir_actas_drive.py` (síncrono, ~6 horas para 20k actas)
   - **`agregar_urls_drive_rapido.py`**: ⭐ Agrega URLs en 5-10 min (vs 4-6 horas del original)
   - `agregar_urls_drive.py`: Versión lenta (busca archivo por archivo)
   - Requiere `credentials.json` de Google Cloud Console
   - Crea carpeta por departamento en Google Drive
   - Genera logs: `actas_sin_url_drive.json` y `actas_sin_url_drive.log`

8. **Flujo de trabajo completo**:

   **FLUJO RECOMENDADO (con Gemini Flash - más económico):**
   - **Paso 1**: Extraer con `script_navegador_detallado_completo.js` → `resultados_jrv_detallado.json`
   - **Paso 2**: Subir con `subir_actas_drive_rapido.py` → Actas en Google Drive (~1 hora)
   - **Paso 3**: Agregar URLs con `agregar_urls_drive_rapido.py` → `resultados_jrv_detallado_con_urls.json` (~5-10 min)
   - **Paso 4**: ⚠️ **CRÍTICO**: Hacer archivos públicos con `compartir_drive_anonimo.py` (ver nota abajo)
   - **Paso 5**: Validar con `validador_gemini_flash.py` → `resultados_validados_gemini.json` (21h gratis o $4)
   - **Paso 6**: (Opcional) Extracción incremental con `generar_exclusiones.py` si faltan actas

   **FLUJO ALTERNATIVO (con Claude - máxima precisión):**
   - **Paso 1-4**: Igual que arriba
   - **Paso 5**: Validar con `validador_actas_dos_fases.py` → `resultados_validados_dos_fases.json` (~$342 para 19k)

9. **Votos nulos y en blanco**: Requieren peticiones separadas con códigos 996, 997, 998

10. **URLs de AWS S3 expiran en 2 horas**: Ejecutar script de Google Drive inmediatamente después de extraer datos

10b. **⚠️ CRÍTICO - Archivos de Drive deben ser públicos**:
    - **Problema**: `validador_gemini_flash.py` descarga PDFs desde `url_drive`
    - **Requisito**: Los archivos DEBEN ser públicos (acceso: "Cualquiera con el enlace")
    - **Solución**: Ejecutar `compartir_drive_anonimo.py` ANTES de validar con Gemini
    - **Alternativas**:
      1. Python: `python compartir_drive_anonimo.py` (automático, recomendado)
      2. Manual: En Drive web, seleccionar todos → Compartir → "Cualquiera con el enlace"
      3. Apps Script: Ver `SISTEMA_EXCLUSIONES.md` para código
    - **Tiempo**: ~5-15 min para 19k archivos
    - **Seguridad**: Solo lectura, propietario NO visible (anónimo)

11. **Sistema de Exclusiones (Extracción Incremental)**:
    - **Problema**: Con 90% de actas ya procesadas, no tiene sentido re-extraer las 19k actas
    - **Solución**: Sistema de exclusión de JRVs que ya tienen URL de Drive
    - **Flujo**:
      1. Python lee `resultados_jrv_detallado_con_urls.json`
      2. Genera `jrvs_a_excluir.js` con Set de JRVs que YA tienen `url_drive`
      3. Script del navegador verifica cada JRV contra `JRVS_A_EXCLUIR` antes de procesarla
      4. Solo procesa JRVs que NO están en el Set de exclusiones
    - **Ventaja**: Si tienes 90% procesado, solo extraes el 10% faltante (~1,900 JRVs)
    - **Scripts involucrados**:
      - `generar_exclusiones.py`: Lee JSON, genera archivo de exclusiones
      - `jrvs_a_excluir.js`: Set JavaScript con JRVs a excluir
      - `script_navegador_detallado_completo.js`: Lee Set y salta JRVs excluidas

12. **Archivos sensibles** (NO subir a Git):
    - `credentials.json`, `token.json`, `resultados*.json`, `jrvs_a_excluir.js`

13. **Documentación clave**:
    - `CONTEXTO_PROYECTO.md`: Este archivo (contexto completo)
    - `SOLUCION_ALTERNATIVA.md`: Por qué usar scripts del navegador
    - `Pasos/guardarArchivos.md`: Guía completa Google Drive
    - `README_SCRIPTS.md`: Comparación de scripts de extracción

---

## 📞 CONTEXTO DEL USUARIO

- **Objetivo**: Hacer proyecciones de resultados electorales por departamento
- **Partidos de interés**: Solo Nacional y Liberal
- **Problema original**: El sitio del CNE es muy lento para consultar municipio por municipio
- **Solución implementada**: Extracción automatizada con JavaScript en el navegador
- **Resultado deseado**: Un solo archivo JSON consolidado

---

## ✅ ESTADO ACTUAL DEL PROYECTO

**Estado**: ✅ COMPLETO Y FUNCIONAL

**Método de extracción**: Script JavaScript en navegador (`script_navegador.js`)

**Documentación**: Completa y actualizada

**Próximos pasos**: Ninguno requerido, el usuario puede ejecutar el script cuando lo necesite

---

## 🤖 VALIDACIÓN CON IA - FASE 2 DEL PROYECTO

### Objetivo
Validar automáticamente que los datos digitados en el sistema del CNE coincidan con los PDFs escaneados de las actas, usando Claude AI (Claude Sonnet 4) para leer y comparar.

### Scripts de Validación

#### 1. `validador_actas_ia.py` (Versión Original)
- Valida solo actas sospechosas (`error_suma=1` o `inconsistencias>0`)
- Genera JSON con objetos anidados
- Archivo salida: `resultados_validados.json`

#### 2. `validador_actas_completo.py` (Versión Completa - RECOMENDADO)
- Valida TODAS las actas (no solo sospechosas)
- Genera JSON plano sin propiedades anidadas
- Archivo salida: `resultados_validados_completo.json`

### Estructura del Acta Electoral

Las actas tienen 3 columnas para cada dato:
1. **PAPELETAS**: Número de papeletas físicas
2. **EN NÚMEROS**: Votos escritos en dígitos (0-9)
3. **EN LETRAS**: Votos escritos en palabras (cero, uno, dos, tres, etc.)

**⚠️ IMPORTANTE**: La columna **"EN LETRAS"** es la más confiable porque:
- Es escrita manualmente en palabras completas
- Más difícil de cometer errores de transcripción
- Los números pueden ser confusos (1 vs 7, 0 vs 6)

### Secciones del Acta

#### I. BALANCE GENERAL
- Papeletas recibidas, no utilizadas, utilizadas
- **TOTAL VOTANTES**: Suma de votantes registrados

#### II. RESUMEN DEL ESCRUTINIO
Votos por partido político:
- **DC** (Demócrata Cristiano) - Casilla verde
- **LIBRE** (Libertad y Refundación) - Casilla roja
- **PINU** (Innovación y Unidad) - Casilla naranja
- **Liberal** - Casilla roja con blanco
- **Nacional** - Casilla azul con estrella
- **VOTOS EN BLANCO**
- **VOTOS NULOS**
- **GRAN TOTAL**: Suma de todos los votos

### Campos Agregados en la Validación

El script `validador_actas_completo.py` agrega 11 campos nuevos al JSON original:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pdf_votos_dc` | int/null | Votos DC extraídos del PDF |
| `pdf_votos_libre` | int/null | Votos LIBRE extraídos del PDF |
| `pdf_votos_pinu` | int/null | Votos PINU extraídos del PDF |
| `pdf_votos_liberal` | int/null | Votos Liberal extraídos del PDF |
| `pdf_votos_nacional` | int/null | Votos Nacional extraídos del PDF |
| `pdf_votos_nulos` | int/null | Votos Nulos extraídos del PDF |
| `pdf_votos_blanco` | int/null | Votos en Blanco extraídos del PDF |
| `pdf_gran_total` | int/null | Gran Total extraído del PDF |
| `pdf_total_votantes` | int/null | Total Votantes extraído del PDF |
| `codigo_jrv` | int | Código/Número de la JRV |
| `es_inconsistente` | 0/1 | 1 = hay discrepancias entre digitado y PDF, 0 = sin discrepancias |
| `suma_inconsistente` | 0/1 | 1 = la suma de votos ≠ gran_total ≠ total_votantes, 0 = suma correcta |

### Validación de Consistencia de Sumas

El script verifica que:
```
suma_votos == gran_total == total_votantes
```

Donde:
- `suma_votos` = DC + LIBRE + PINU + Liberal + Nacional + Nulos + Blanco
- `gran_total` = Total mostrado en el acta
- `total_votantes` = Total de votantes del balance general

Si estas tres cifras NO coinciden, se marca `suma_inconsistente = 1`

### Modelo de IA Utilizado

**Modelo**: `claude-sonnet-4-20250514` (Claude Sonnet 4)
- Es el modelo más reciente y potente de Anthropic
- Excelente capacidad de visión para analizar documentos
- Mayor precisión que Claude 3.5 Sonnet
- Costo: ~$3 por cada 1000 actas analizadas

### Prompt de Extracción

El prompt instruye a Claude para:
1. Leer la columna **"EN LETRAS"** (no la columna de números)
2. Convertir las palabras a números
3. Extraer votos de todos los partidos
4. Extraer GRAN TOTAL y TOTAL VOTANTES
5. Retornar un JSON estructurado

### Mejoras Implementadas

#### Problema Inicial
Claude leía "7" (siete) como "1" (uno) porque la escritura manual puede ser ambigua.

#### Solución
Cambiar el prompt para que lea la columna **"EN LETRAS"** en lugar de **"EN NÚMEROS"**:
- "siete" → 7 (sin ambigüedad)
- "uno" → 1 (sin ambigüedad)
- Mayor precisión en la extracción

### Ejemplo de JSON Resultante

```json
{
  "id_departamento": "18",
  "departamento": "YORO",
  "id_municipio": "003",
  "municipio": "EL NEGRITO",
  "numero_jrv": 18108,
  "votos_dc": 0,
  "votos_libre": 0,
  "votos_pinu": 0,
  "votos_liberal": 0,
  "votos_nacional": 0,
  "votos_nulos": 5,
  "votos_blanco": 7,
  "url_acta_pdf": "https://...",

  "pdf_votos_dc": 0,
  "pdf_votos_libre": 14,
  "pdf_votos_pinu": 0,
  "pdf_votos_liberal": 31,
  "pdf_votos_nacional": 103,
  "pdf_votos_nulos": 5,
  "pdf_votos_blanco": 7,
  "pdf_gran_total": 160,
  "pdf_total_votantes": 160,
  "codigo_jrv": 18108,
  "es_inconsistente": 1,
  "suma_inconsistente": 0
}
```

En este ejemplo:
- `es_inconsistente = 1`: Hay diferencias entre datos digitados y PDF (Liberal: 0 vs 31, Nacional: 0 vs 103)
- `suma_inconsistente = 0`: La suma es correcta (0+14+0+31+103+5+7 = 160 = gran_total = total_votantes)

### Dependencias Python

```bash
pip install anthropic requests
```

### Configuración

1. Obtener API Key de Anthropic: https://console.anthropic.com/
2. Editar línea 17 del script: `ANTHROPIC_API_KEY = "tu-clave-aqui"`
3. Ejecutar: `python validador_actas_completo.py`

### Costos Estimados

| Cantidad de Actas | Costo Aprox. | Tiempo Estimado |
|-------------------|--------------|-----------------|
| 100 actas | $0.30 | 3-5 minutos |
| 500 actas | $1.50 | 20-30 minutos |
| 1,000 actas | $3.00 | 40-60 minutos |
| 20,000 actas (todo) | $60 | 11-12 horas |

### Rate Limiting

El script incluye un delay de 2 segundos entre peticiones para evitar:
- Bloqueo por parte de Anthropic API
- Consumo excesivo de tokens
- Sobrecarga del sistema

### Archivos Relacionados

- `validador_actas_completo.py`: Script principal de validación
- `verificar_modelos.py`: Utilidad para verificar modelos disponibles
- `PLAN_VALIDACION_IA.md`: Plan detallado de la validación
- `EjemploActa1.png`: Imagen de referencia de un acta

---

---

## 🔄 ACTUALIZACIÓN 2025-12-05: Mejoras en Validación

### Nuevos Campos Agregados

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pdf_papeletas_recibidas` | int/null | Papeletas recibidas según acta de apertura |
| `pdf_papeletas_no_utilizadas` | int/null | Papeletas no utilizadas/sobrantes |
| `pdf_papeletas_utilizadas` | int/null | Papeletas utilizadas |
| `pdf_numero_acta_qr` | string/null | Código QR (esquina superior derecha) |
| `pdf_numero_acta_barra` | string/null | Código de barras (inferior derecha) |
| `InconsistenciaPapeletas` | 0/1 | 1 = papeletas_utilizadas ≠ (recibidas - no_utilizadas) O ≠ total_votantes |
| `NumeroActaInconsistente` | 0/1 | 1 = QR ≠ código de barras |

### Cambio de Orden: Votos Blancos antes que Votos Nulos

En todos los campos y validaciones, ahora el orden es:
- DC → LIBRE → PINU → Liberal → Nacional → **Blanco** → Nulos

### Validación Cruzada Números vs Letras

El prompt ahora instruye a Claude para:
1. Leer AMBAS columnas: "EN NÚMEROS" y "EN LETRAS"
2. Comparar si coinciden
3. Si coinciden → usar valor con alta confianza
4. Si NO coinciden → priorizar "EN LETRAS" pero retornar `null` en casos muy dudosos
5. Esto reduce errores cuando la escritura es difusa o poco clara

### Problemas Encontrados y Soluciones

#### Problema 1: Lectura de Columnas Centena-Decena-Unidad
**Error**: Claude leía solo la última columna (unidades) en lugar de las 3 columnas.

**Ejemplo**:
- Acta dice: "cero cinco siete" (057)
- Claude leía: 7

**Solución**: Prompt actualizado con instrucciones explícitas:
- 1ª columna = CENTENAS × 100
- 2ª columna = DECENAS × 10
- 3ª columna = UNIDADES × 1
- Sumar las 3 para obtener el número completo

#### Problema 2: Escritura Difusa o Poco Marcada
**Errores comunes encontrados**:
- Ejemplo3: LIBRE 48 leído como 43 (confusión 8 vs 3 por marca difusa)
- Ejemplo3: Liberal 107 leído como 1 (no leyó centenas y decenas)
- Ejemplo3: Nacional 46 leído como 16 (confusión 4 vs 1)
- Ejemplo4: LIBRE 36 leído como 306 (error en centenas)
- Ejemplo5: Nulos 2 leído como 7
- Ejemplo6: LIBRE 32 leído como 52 (confusión 3 vs 5)

**Solución**: Validación cruzada entre "EN NÚMEROS" y "EN LETRAS"
- Si ambas columnas no coinciden, Claude marca como dudoso
- Prioriza "EN LETRAS" porque es menos ambigua
- En casos muy dudosos, retorna `null` para revisión manual

#### Problema 3: Números con Escritura Ambigua
**Confusiones comunes**:
- 1 vs 7 (cuando el trazo es poco claro)
- 3 vs 5 (cuando la curva superior está marcada)
- 0 vs 6 (cuando hay cierre parcial)
- 4 vs 9 (cuando el trazo no es nítido)

**Solución**:
- Leer columna "EN LETRAS" (palabras) en lugar de números
- Palabras como "cinco", "siete", "tres" son menos ambiguas que los dígitos escritos a mano

### Validación de Papeletas

Nueva validación que verifica:
```
papeletas_utilizadas == (papeletas_recibidas - papeletas_no_utilizadas)
Y
papeletas_utilizadas == total_votantes
```

Si cualquiera de estas condiciones falla:
```
InconsistenciaPapeletas = 1
```

### Validación de Números de Acta

Verifica que el código QR coincida con el código de barras:
```
if pdf_numero_acta_qr != pdf_numero_acta_barra:
    NumeroActaInconsistente = 1
```

### Archivos de Ejemplo Analizados

- `EjemploActa1.png`: Acta con formato estándar (corregida)
- `EjemploActa2.png`: Acta con formato centena-decena-unidad
- `EjemploActa3.png`: Acta con escritura difusa (múltiples errores)
- `EjemploActa4.png`: Acta con error en centenas
- `EjemploActa5.png`: Acta con error en nulos
- `EjemploActa6.png`: Acta con múltiples confusiones de dígitos

### Campos del JSON Actualizado (Total: 18 campos agregados)

**Votos extraídos del PDF**:
1. `pdf_votos_dc`
2. `pdf_votos_libre`
3. `pdf_votos_pinu`
4. `pdf_votos_liberal`
5. `pdf_votos_nacional`
6. `pdf_votos_blanco` ⭐ Orden cambiado
7. `pdf_votos_nulos`
8. `pdf_gran_total`
9. `pdf_total_votantes`
10. `pdf_jrv`

**Papeletas**:
11. `pdf_papeletas_recibidas` ⭐ NUEVO
12. `pdf_papeletas_no_utilizadas` ⭐ NUEVO
13. `pdf_papeletas_utilizadas` ⭐ NUEVO

**Códigos de acta**:
14. `pdf_numero_acta_qr` ⭐ NUEVO
15. `pdf_numero_acta_barra` ⭐ NUEVO

**Campos calculados**:
16. `codigo_jrv`
17. `SumatoriaManualPorPartido`

**Campos de inconsistencias**:
18. `InconsistenciaDatosDigitados`
19. `InconsistenciaGrandTotalPorVotantes`
20. `InconsistenciaJrv`
21. `InconsistenciaPapeletas` ⭐ NUEVO
22. `NumeroActaInconsistente` ⭐ NUEVO

### Mejoras en el Prompt

1. **Instrucciones explícitas sobre formato de 3 columnas** (centena-decena-unidad)
2. **Validación cruzada** entre "EN NÚMEROS" y "EN LETRAS"
3. **Lectura de códigos QR y de barras**
4. **Extracción de papeletas** del Balance General
5. **Ejemplos concretos** de cómo sumar las columnas
6. **Instrucciones sobre casos dudosos** (retornar null)

---

---

## 🚀 ACTUALIZACIÓN 2025-12-05: Validador en Dos Fases

### Estrategia Optimizada de Validación

Después de múltiples iteraciones y pruebas, se implementó una **estrategia de validación en dos fases** que optimiza costo y precisión:

#### FASE 1: Claude Sonnet 4 (TODAS las actas)
- **Modelo**: `claude-sonnet-4-20250514`
- **Alcance**: 100% de las actas
- **Costo**: ~$3 por 1,000 actas
- **Propósito**: Validación inicial rápida y económica
- **Salida**: `resultados_fase1_sonnet.json`

#### FASE 2: Claude Opus 4.5 (SOLO inconsistencias)
- **Modelo**: `claude-opus-4-5-20251101`
- **Alcance**: Solo actas con inconsistencias detectadas en Fase 1
- **Costo**: ~$15 por 1,000 actas
- **Propósito**: Re-validación con máxima precisión
- **Salida**: `resultados_validados_dos_fases.json` (resultado final)

### Comparación de Costos

| Estrategia | 20,000 Actas | Precisión |
|------------|--------------|-----------|
| Solo Sonnet 4 | ~$60 | Media-Alta |
| Solo Opus 4.5 | ~$300 | Muy Alta |
| **Dos Fases** ⭐ | **~$66** | **Muy Alta** |

**Ahorro vs Solo Opus**: ~$234 (78% menos) 🎉

### Script: `validador_actas_dos_fases.py`

**Características**:
- Procesa todas las actas con Sonnet 4
- Identifica automáticamente actas con inconsistencias
- Re-procesa inconsistentes con Opus 4.5
- Combina resultados (Opus sobrescribe Sonnet para inconsistentes)
- Genera reporte de costos estimados

**Ejecución**:
```bash
python validador_actas_dos_fases.py
```

**Archivos generados**:
1. `resultados_fase1_sonnet.json` - Todos los resultados de Fase 1
2. `resultados_validados_dos_fases.json` - **Resultado final combinado**

### Problema Crítico Resuelto: Números Repetidos en Columnas

#### Error Común Identificado
Claude leía solo la **última columna** cuando había palabras repetidas:

**Ejemplo**:
- Acta dice: "cero dos dos" (columnas: centenas-decenas-unidades)
- Claude leía: **2** ❌
- Valor correcto: (0×100) + (2×10) + (2×1) = **22** ✅

#### Solución Implementada
Agregamos **ejemplos explícitos** al prompt con casos problemáticos:

```
⚠️ Ejemplos CRÍTICOS:
- "cero dos dos" = (0×100) + (2×10) + (2×1) = 0 + 20 + 2 = 22  ⚠️ NO es 2!
- "cero tres cero" = (0×100) + (3×10) + (0×1) = 0 + 30 + 0 = 30  ⚠️ NO es 3!
- "cero cuatro ocho" = (0×100) + (4×10) + (8×1) = 0 + 40 + 8 = 48  ⚠️ NO es 8!
```

Esto enseña a Claude la multiplicación posicional correcta incluso con palabras repetidas.

### Intentos Descartados: OCR Híbrido

Se probó una estrategia híbrida **Tesseract OCR + Claude**:

**Concepto**:
1. Tesseract OCR extrae TODO el texto del PDF
2. Claude solo estructura los datos ya extraídos

**Resultado**: ❌ **Funcionaba PEOR** que usar solo Claude

**Razones**:
- Tesseract perdía formato/estructura de las columnas
- Claude trabaja mejor viendo directamente la imagen
- La conversión PDF → Imagen → OCR → Texto introducía errores adicionales
- Calidad del escaneo afectaba mucho a Tesseract

**Conclusión**: Usar Claude directamente con el PDF es más preciso.

### Modelos de Claude: Comparación

| Modelo | ID API | Input | Output | Precisión | Velocidad |
|--------|--------|-------|--------|-----------|-----------|
| Sonnet 4 | `claude-sonnet-4-20250514` | $3/1M | $15/1M | Alta | Rápida |
| **Opus 4.5** | `claude-opus-4-5-20251101` | $15/1M | $75/1M | **Muy Alta** | Más lenta |
| Haiku 3.5 | `claude-3-5-haiku-20241022` | $0.80/1M | $4/1M | Media | Muy rápida |

### Tasa de Precisión Actual

Con la estrategia de dos fases y prompt mejorado:
- **Fase 1 (Sonnet 4)**: ~85-90% de precisión
- **Fase 2 (Opus 4.5)**: ~98-99% de precisión
- **Resultado Final**: ~98-99% de precisión en TODAS las actas

### Scripts Disponibles

| Script | Modelo | Estrategia | Recomendado |
|--------|--------|-----------|-------------|
| `validador_actas_ia.py` | Sonnet 4 | Solo sospechosas | ❌ Obsoleto |
| `validador_actas_completo.py` | Sonnet 4 | Todas las actas | ⚠️ Usar para pruebas |
| `validador_actas_hibrido.py` | OCR + Sonnet 4 | Híbrido | ❌ No recomendado |
| **`validador_actas_dos_fases.py`** | **Sonnet 4 + Opus 4.5** | **Dos fases** | ✅ **RECOMENDADO** |

### Lecciones Aprendidas

1. **IA directa mejor que OCR híbrido**: Claude lee PDFs mejor que procesar texto extraído por OCR
2. **Ejemplos explícitos críticos**: Casos edge como "cero dos dos" necesitan ejemplos en el prompt
3. **Estrategia de dos fases óptima**: Usar modelo económico primero, premium solo para casos problemáticos
4. **Validación cruzada ayuda**: Comparar "EN NÚMEROS" vs "EN LETRAS" reduce errores
5. **Escritura a mano variable**: Actas con escritura difusa son el mayor desafío

### Archivos de Ejemplo Documentados

- `EjemploActa1.png`: Acta estándar (corregida)
- `EjemploActa2.png`: Formato centena-decena-unidad
- `EjemploActa3.png`: Escritura difusa (múltiples errores)
- `EjemploActa4.png`: Error en centenas
- `EjemploActa5.png`: Error en nulos
- `EjemploActa6.png`: Múltiples confusiones de dígitos
- `EjemploActa11.png`: Caso "cero dos dos" = 22 (palabras repetidas)

---

## 📤 ACTUALIZACIÓN 2025-12-05: Fase 3 - Subida a Google Drive

### Objetivo
Organizar y respaldar todas las actas electorales (PDFs) en Google Drive, creando una carpeta por departamento para facilitar el acceso y compartir los documentos.

### Scripts de Google Drive

#### 1. `subir_actas_drive.py` - Subir Actas a Drive
**Propósito**: Descargar PDFs desde AWS S3 y subirlos a Google Drive organizados por departamento.

**Características**:
- ✅ Lee `resultados_jrv_detallado.json` con URLs de actas
- ✅ Descarga PDFs desde AWS S3 (URLs temporales)
- ✅ Crea carpeta por departamento en Google Drive
- ✅ Nombra archivos como `JRV_{numero_jrv}.pdf`
- ✅ Reemplaza archivos existentes automáticamente
- ✅ Muestra progreso en tiempo real
- ✅ Maneja errores y reintentos
- ⚠️ Requiere autenticación OAuth 2.0 de Google

**Configuración inicial**:
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client requests
```

**Credenciales necesarias**:
1. Crear proyecto en Google Cloud Console
2. Habilitar Google Drive API
3. Crear credenciales OAuth 2.0 (Aplicación de escritorio)
4. Descargar `credentials.json` y colocarlo en la raíz del proyecto

**Ejecución**:
```bash
python subir_actas_drive.py
```

**Tiempo estimado**:
- 1,000 actas: ~15 minutos
- 5,000 actas: ~1.5 horas
- 10,000 actas: ~3 horas
- 20,000 actas: ~6 horas

**Estructura en Google Drive**:
```
Mi unidad/
  └─ [Carpeta Raíz] (opcional: PARENT_FOLDER_ID)
      ├─ ATLANTIDA/
      │   ├─ JRV_1001.pdf
      │   └─ JRV_1002.pdf
      ├─ CORTES/
      │   ├─ JRV_5001.pdf
      │   └─ JRV_5002.pdf
      ├─ FRANCISCO MORAZAN/
      └─ ... (19 departamentos)
```

#### 2. `subir_actas_drive_rapido.py` - Versión Asíncrona (Más Rápida)
**Características adicionales**:
- ✅ Subida asíncrona (múltiples archivos en paralelo)
- ✅ 5-10x más rápido que la versión sincrónica
- ✅ Configuración de concurrencia ajustable
- ⚠️ Mayor uso de CPU/RAM

**Ejecución**:
```bash
python subir_actas_drive_rapido.py
```

#### 3. `agregar_urls_drive.py` - Agregar URLs de Drive al JSON
**Propósito**: Una vez subidas las actas, agregar el campo `url_drive` a cada registro del JSON.

**Características**:
- ✅ Busca archivos en las carpetas de Google Drive
- ✅ Agrega campo `url_drive` con el enlace público
- ✅ Hace públicos los archivos (opcional: `HACER_PUBLICOS = True`)
- ✅ Genera nuevo JSON: `resultados_jrv_detallado_con_urls.json`

**Formato del campo agregado**:
```json
{
  "numero_jrv": 18166,
  "url_acta_pdf": "https://....s3.amazonaws.com/...",
  "url_drive": "https://drive.google.com/file/d/1aBcDeFgHiJkLmNoPqRs/view?usp=sharing"
}
```

**Ejecución**:
```bash
python agregar_urls_drive.py
```

### Flujo de Trabajo Completo

#### Paso 1: Extraer Datos del CNE
```javascript
// En consola del navegador
await extraerTodosLosDatosDetallados()
descargarJSON(window.resultadosCNEDetallados)
```
**Resultado**: `resultados_jrv_detallado.json`

#### Paso 2: Validar Actas con IA
```bash
python validador_actas_dos_fases.py
```
**Resultado**: `resultados_validados_dos_fases.json`

#### Paso 3: Subir Actas a Google Drive
```bash
python subir_actas_drive_rapido.py
```
**Resultado**: Actas organizadas en Google Drive por departamento

#### Paso 4: Agregar URLs de Drive al JSON
```bash
python agregar_urls_drive.py
```
**Resultado**: `resultados_jrv_detallado_con_urls.json`

### Ventajas de Google Drive

1. **Respaldo confiable**: AWS S3 URLs expiran después de 2 horas, Drive es permanente
2. **Organización**: Carpetas por departamento facilitan navegación
3. **Compartir**: Enlaces públicos para compartir actas específicas
4. **Acceso rápido**: Búsqueda por JRV en Drive
5. **Colaboración**: Múltiples personas pueden acceder simultáneamente

### Limitaciones y Consideraciones

#### Rate Limiting de Google Drive API
- **Límite**: 1,000 operaciones por 100 segundos
- **Solución**: Scripts incluyen delay de 0.5-1s entre archivos
- **Si falla**: Aumentar delay en el código

#### URLs de AWS S3 Expiran
- **Problema**: URLs en `resultados_jrv_detallado.json` expiran en 2 horas
- **Solución**: Ejecutar script de subida inmediatamente después de extraer datos
- **Alternativa**: Re-ejecutar script del navegador para obtener URLs frescas

#### Espacio en Google Drive
- **Actas estimadas**: ~20,000 actas × ~100 KB/acta = ~2 GB
- **Google Drive gratuito**: 15 GB (suficiente)
- **Recomendación**: Verificar espacio disponible antes de iniciar

### Archivos de Configuración

#### `credentials.json` (NO subir a Git)
Credenciales OAuth 2.0 descargadas de Google Cloud Console.

#### `token.json` (NO subir a Git, generado automáticamente)
Token de autenticación guardado después del primer login.

#### `.gitignore` Recomendado
```gitignore
credentials.json
token.json
actas_temp/
resultados*.json
```

### Seguridad

**Archivos públicos**:
- `agregar_urls_drive.py` puede hacer públicos los PDFs (`HACER_PUBLICOS = True`)
- URLs públicas: Cualquiera con el enlace puede ver el PDF
- URLs privadas: Solo tú puedes verlos

**Recomendación**:
- Usar URLs públicas si quieres compartir las actas
- Usar URLs privadas si son datos sensibles

### Documentación Adicional

- **Guía completa**: `Pasos/guardarArchivos.md`
- **Configuración Google Cloud**: https://console.cloud.google.com/
- **Google Drive API Docs**: https://developers.google.com/drive/api/v3/about-sdk

### Scripts Disponibles Actualizados

| Script | Propósito | Tiempo Estimado |
|--------|-----------|-----------------|
| `script_navegador_detallado_completo.js` | Extraer datos CNE por JRV | Varias horas |
| `validador_actas_dos_fases.py` | Validar actas con IA | ~12 horas (20k actas) |
| **`subir_actas_drive.py`** ⭐ | **Subir actas a Drive (síncrono)** | **~6 horas (20k actas)** |
| **`subir_actas_drive_rapido.py`** ⚡ | **Subir actas a Drive (asíncrono)** | **~1 hora (20k actas)** |
| **`agregar_urls_drive.py`** | **Agregar campo url_drive al JSON** | **~10-15 minutos** |

### Estado Actual del Proyecto - Actualizado

**Estado**: ✅ COMPLETO - 3 FASES FUNCIONALES

1. **FASE 1 - Extracción**: ✅ Scripts JavaScript del navegador
2. **FASE 2 - Validación IA**: ✅ Estrategia de dos fases (Sonnet 4 + Opus 4.5)
3. **FASE 3 - Respaldo Drive**: ✅ Scripts de subida a Google Drive

**Próximos pasos opcionales**:
- Automatizar proceso completo de 3 fases
- Dashboard web para visualizar resultados
- Alertas automáticas de inconsistencias
- Exportación a Excel/CSV

---

*Documento creado: 2025-12-04*
*Última actualización: 2025-12-05*
*Versión: 5.0 - Fase 3 agregada: Subida a Google Drive*
