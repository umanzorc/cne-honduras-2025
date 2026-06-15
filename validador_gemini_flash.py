#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#python validador_gemini_flash.py --depto 09
"""
Validador de Actas con Google Gemini 2.0 Flash
Alternativa económica a Claude para procesar 19,000 actas

COSTO: GRATIS (tier gratuito) o ~$4 (tier pagado)
TIEMPO: ~21 horas con tier gratuito (15 req/min)
PRECISIÓN ESTIMADA: 90-95%
"""

import json
import requests
import time
import tempfile
from pathlib import Path
from typing import Dict, List
import sys
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import argparse

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    import google.generativeai as genai
except ImportError:
    print("❌ Error: Necesitas instalar la librería de Google AI")
    print("💡 Ejecuta: pip install google-generativeai")
    sys.exit(1)

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# API Key de Google AI Studio (https://makersuite.google.com/app/apikey)
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')  # Configura: export GOOGLE_API_KEY='tu-key'

if not GOOGLE_API_KEY:
    print("❌ Error: No se encontró la API Key de Google")
    print("💡 Opciones:")
    print("   1. Configurar variable de entorno: export GOOGLE_API_KEY='tu-key'")
    print("   2. O editar línea 28 de este script directamente")
    print("\n📝 Obtén tu API Key aquí: https://makersuite.google.com/app/apikey")
    sys.exit(1)

# Archivos
JSON_INPUT = 'resultados_jrv_detallado_con_urls.json'
JSON_OUTPUT = 'resultados_validados_gemini.json'
JSON_PROCESADAS = 'jrvs_procesadas.json'  # Registro de JRVs ya procesadas

# Configuración de rate limiting
USAR_TIER_GRATUITO = False  # True = 15 req/min (gratis), False = sin límite (pagado)
REQUESTS_POR_MINUTO = 15 if USAR_TIER_GRATUITO else 500
DELAY_ENTRE_REQUESTS = 60 / REQUESTS_POR_MINUTO  # segundos

# Modelo
MODELO = "gemini-2.5-flash"  # Modelo básico disponible en tier gratuito

# Límite de actas a procesar (para pruebas)
LIMITE_ACTAS = 4000 # None = todas, o número específico (ej: 100 para pruebas)

# Configuración de concurrencia
# Gemini Flash soporta hasta 1000 req/min en tier pagado y 15 req/min en gratuito
# Para tier gratuito: max 3-5 concurrentes para no saturar
# Para tier pagado: 20-30 concurrentes es seguro
CONCURRENCIA_MAXIMA = 3 if USAR_TIER_GRATUITO else 20

# Carpeta de salida por departamento
OUTPUT_DIR = 'OutputDepartamentos'

# Mapeo de departamentos
DEPARTAMENTOS = {
    "01": "ATLANTIDA",
    "02": "COLON",
    "03": "COMAYAGUA",
    "04": "COPAN",
    "05": "CORTES",
    "06": "CHOLUTECA",
    "07": "EL PARAISO",
    "08": "FRANCISCO MORAZAN",
    "09": "GRACIAS A DIOS",
    "10": "INTIBUCA",
    "11": "ISLAS DE LA BAHIA",
    "12": "LA PAZ",
    "13": "LEMPIRA",
    "14": "OCOTEPEQUE",
    "15": "OLANCHO",
    "16": "SANTA BARBARA",
    "17": "VALLE",
    "18": "YORO",
    "20": "VOTO EN EL EXTERIOR"
}

# ============================================================================
# PROMPT DE EXTRACCIÓN
# ============================================================================

PROMPT_EXTRACCION = """Analiza esta acta electoral de Honduras y extrae EXACTAMENTE los votos de cada partido.

INSTRUCCIONES MUY IMPORTANTES:
- Esta es un acta de votación presidencial de Honduras
- El acta tiene 3 secciones de columnas: PAPELETAS, EN NÚMEROS, EN LETRAS

⚠️ FORMATO CRÍTICO DE LAS COLUMNAS "EN LETRAS":
- Cada fila tiene 3 SUB-COLUMNAS que forman un solo número:
  * Primera columna = CENTENAS (ej: "uno" = 100)
  * Segunda columna = DECENAS (ej: "cinco" = 50, "dos" = 20)
  * Tercera columna = UNIDADES (ej: "siete" = 7, "dos" = 2)
- DEBES SUMAR las 3 sub-columnas para obtener el número completo
- IMPORTANTE: "dos" en la columna de DECENAS = 20 (no 2)
- IMPORTANTE: "dos" en la columna de UNIDADES = 2 (no 20)

Ejemplos CRÍTICOS:
- "cero cinco siete" = (0×100) + (5×10) + (7×1) = 0 + 50 + 7 = 57
- "uno uno cero" = (1×100) + (1×10) + (0×1) = 100 + 10 + 0 = 110
- "dos cero seis" = (2×100) + (0×10) + (6×1) = 200 + 0 + 6 = 206
- "cero dos dos" = (0×100) + (2×10) + (2×1) = 0 + 20 + 2 = 22  ⚠️ NO es 2!
- "cero tres cero" = (0×100) + (3×10) + (0×1) = 0 + 30 + 0 = 30  ⚠️ NO es 3!
- "cero cuatro ocho" = (0×100) + (4×10) + (8×1) = 0 + 40 + 8 = 48  ⚠️ NO es 8!

PROCESO DE LECTURA:
1. Busca la sección "II. RESULTADOS DEL ESCRUTINIO"
2. Para cada partido, lee las 3 sub-columnas de "EN LETRAS"
3. Convierte cada palabra a su valor posicional:
   - 1ª columna: multiplica por 100
   - 2ª columna: multiplica por 10
   - 3ª columna: usa el valor directo
4. Suma los 3 valores

VALIDACIÓN CRUZADA:
- Compara "EN NÚMEROS" con "EN LETRAS"
- Si coinciden = alta confianza
- Si NO coinciden = prioriza "EN LETRAS" (es más confiable)

PARTIDOS A EXTRAER (en este orden):
- DC (Partido Demócrata Cristiano) - Casilla verde
- LIBRE (Libertad y Refundación) - Casilla roja
- PINU (Innovación y Unidad) - Casilla naranja
- Liberal - Casilla roja con blanco
- Nacional - Casilla azul con estrella
- VOTOS EN BLANCO
- VOTOS NULOS
- GRAN TOTAL (última fila de la sección II)

TAMBIÉN EXTRAE:
- TOTAL VOTANTES (de la sección I. BALANCE GENERAL, última fila)
- JRV (número en el encabezado "JRV N° XXXXX")
- Papeletas recibidas, no utilizadas, utilizadas
- Número de acta QR (esquina superior derecha)
- Número de acta código de barras (inferior derecha)

RETORNA UN JSON CON ESTA ESTRUCTURA EXACTA:
{
  "pdf_votos_dc": <número o null>,
  "pdf_votos_libre": <número o null>,
  "pdf_votos_pinu": <número o null>,
  "pdf_votos_liberal": <número o null>,
  "pdf_votos_nacional": <número o null>,
  "pdf_votos_blanco": <número o null>,
  "pdf_votos_nulos": <número o null>,
  "pdf_gran_total": <número o null>,
  "pdf_total_votantes": <número o null>,
  "pdf_jrv": <número o null>,
  "pdf_papeletas_recibidas": <número o null>,
  "pdf_papeletas_no_utilizadas": <número o null>,
  "pdf_papeletas_utilizadas": <número o null>,
  "pdf_numero_acta_qr": "<string o null>",
  "pdf_numero_acta_barra": "<string o null>"
}

IMPORTANTE:
- Si no puedes leer un valor claramente, usa null
- NO inventes valores
- Retorna SOLO el JSON, sin texto adicional
"""

# ============================================================================
# FUNCIONES
# ============================================================================

def configurar_gemini():
    """Configura la API de Google Gemini"""
    genai.configure(api_key=GOOGLE_API_KEY)

    # Configuración de seguridad (permisiva para documentos electorales)
    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE"
        }
    ]

    model = genai.GenerativeModel(
        model_name=MODELO,
        safety_settings=safety_settings
    )

    return model

def cargar_jrvs_procesadas() -> set:
    """Carga el conjunto de JRVs que ya fueron procesadas exitosamente"""
    if not os.path.exists(JSON_PROCESADAS):
        return set()

    try:
        with open(JSON_PROCESADAS, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data.get('jrvs_procesadas', []))
    except Exception as e:
        print(f"⚠️  Error cargando JRVs procesadas: {e}")
        return set()

def guardar_jrv_procesada(numero_jrv: int, jrvs_procesadas: set, lock: Lock):
    """Agrega una JRV al conjunto de procesadas y guarda el archivo"""
    with lock:
        jrvs_procesadas.add(numero_jrv)
        try:
            with open(JSON_PROCESADAS, 'w', encoding='utf-8') as f:
                json.dump({
                    'jrvs_procesadas': sorted(list(jrvs_procesadas)),
                    'total': len(jrvs_procesadas),
                    'ultima_actualizacion': time.strftime('%Y-%m-%d %H:%M:%S')
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  Error guardando JRV procesada: {e}")

def cargar_json(ruta_json: str) -> List[Dict]:
    """Carga el JSON con los datos del CNE"""
    print(f"📂 Cargando datos desde: {ruta_json}")

    if not os.path.exists(ruta_json):
        print(f"❌ Error: Archivo no encontrado: {ruta_json}")
        sys.exit(1)

    with open(ruta_json, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    if isinstance(datos, dict):
        print("ℹ️  Detectado un solo registro, convirtiéndolo a lista")
        datos = [datos]

    print(f"✅ Cargados {len(datos)} registros\n")
    return datos

def convertir_url_drive_descarga(url: str) -> str:
    """
    Convierte URL de Drive de visualización a descarga directa
    Input:  https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    Output: https://drive.google.com/uc?export=download&id=FILE_ID
    """
    if 'drive.google.com' in url:
        # Extraer el FILE_ID
        if '/file/d/' in url:
            file_id = url.split('/file/d/')[1].split('/')[0]
            return f'https://drive.google.com/uc?export=download&id={file_id}'
    return url

def descargar_pdf(url: str) -> bytes:
    """Descarga el PDF desde la URL (AWS S3 o Google Drive)"""
    try:
        # Convertir URL de Drive si es necesario
        url_descarga = convertir_url_drive_descarga(url)

        response = requests.get(url_descarga, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"      ❌ Error descargando PDF: {e}")
        return None

def extraer_votos_con_gemini(pdf_url: str, model, max_reintentos: int = 3) -> Dict:
    """
    Envía el PDF a Gemini y extrae los votos con reintentos automáticos
    """
    for intento in range(max_reintentos):
        # Descargar PDF
        pdf_content = descargar_pdf(pdf_url)
        if not pdf_content:
            if intento < max_reintentos - 1:
                print(f"      ⚠️  Reintento {intento + 1}/{max_reintentos}...")
                time.sleep(2)
                continue
            return None

        # Crear archivo temporal
        temp_file = None

        try:
            # Guardar PDF en archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(pdf_content)
                temp_file = tmp.name

            # Subir archivo a Gemini
            file = genai.upload_file(path=temp_file, mime_type='application/pdf')

            # Esperar a que el archivo se procese
            while file.state.name == "PROCESSING":
                time.sleep(1)
                file = genai.get_file(file.name)

            if file.state.name == "FAILED":
                print(f"      ❌ Error: Gemini falló al procesar el PDF")
                if intento < max_reintentos - 1:
                    print(f"      ⚠️  Reintento {intento + 1}/{max_reintentos}...")
                    genai.delete_file(file.name)
                    time.sleep(2)
                    continue
                return None

            # Generar contenido
            response = model.generate_content([file, PROMPT_EXTRACCION])

            # Eliminar archivo de Gemini
            genai.delete_file(file.name)

            # Parsear respuesta
            texto_respuesta = response.text.strip()

            # Limpiar respuesta (a veces Gemini agrega markdown)
            if texto_respuesta.startswith('```json'):
                texto_respuesta = texto_respuesta.replace('```json', '').replace('```', '').strip()
            elif texto_respuesta.startswith('```'):
                texto_respuesta = texto_respuesta.replace('```', '').strip()

            # Parsear JSON
            resultado = json.loads(texto_respuesta)

            return resultado

        except json.JSONDecodeError as e:
            print(f"      ❌ Error parseando JSON: {e}")
            if intento < max_reintentos - 1:
                print(f"      ⚠️  Reintento {intento + 1}/{max_reintentos}...")
                time.sleep(2)
                continue
            print(f"      Respuesta: {response.text[:200]}...")
            return None
        except Exception as e:
            print(f"      ❌ Error en Gemini: {e}")
            if intento < max_reintentos - 1:
                print(f"      ⚠️  Reintento {intento + 1}/{max_reintentos}...")
                time.sleep(2)
                continue
            return None
        finally:
            # Limpiar archivo temporal
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    return None

def calcular_campos_validacion(acta_original: Dict, datos_pdf: Dict) -> Dict:
    """
    Calcula campos de validación comparando datos digitados vs PDF
    """
    if not datos_pdf:
        return acta_original

    # Agregar datos del PDF al acta
    acta_completa = {**acta_original, **datos_pdf}

    # Calcular sumatoria manual
    suma_manual = sum(filter(None, [
        datos_pdf.get('pdf_votos_dc', 0),
        datos_pdf.get('pdf_votos_libre', 0),
        datos_pdf.get('pdf_votos_pinu', 0),
        datos_pdf.get('pdf_votos_liberal', 0),
        datos_pdf.get('pdf_votos_nacional', 0),
        datos_pdf.get('pdf_votos_blanco', 0),
        datos_pdf.get('pdf_votos_nulos', 0)
    ]))

    acta_completa['SumatoriaManualPorPartido'] = suma_manual

    # Código JRV
    acta_completa['codigo_jrv'] = acta_original.get('numero_jrv')

    # Validar inconsistencias
    # 1. Comparar datos digitados con PDF
    inconsistencia_datos = 0
    if (acta_original.get('votos_dc') != datos_pdf.get('pdf_votos_dc') or
        acta_original.get('votos_libre') != datos_pdf.get('pdf_votos_libre') or
        acta_original.get('votos_pinu') != datos_pdf.get('pdf_votos_pinu') or
        acta_original.get('votos_liberal') != datos_pdf.get('pdf_votos_liberal') or
        acta_original.get('votos_nacional') != datos_pdf.get('pdf_votos_nacional') or
        acta_original.get('votos_blanco') != datos_pdf.get('pdf_votos_blanco') or
        acta_original.get('votos_nulos') != datos_pdf.get('pdf_votos_nulos')):
        inconsistencia_datos = 1

    acta_completa['InconsistenciaDatosDigitados'] = inconsistencia_datos

    # 2. Validar gran total vs total votantes
    gran_total = datos_pdf.get('pdf_gran_total')
    total_votantes = datos_pdf.get('pdf_total_votantes')

    inconsistencia_totales = 0
    if gran_total and total_votantes and suma_manual:
        if not (gran_total == total_votantes == suma_manual):
            inconsistencia_totales = 1

    acta_completa['InconsistenciaGrandTotalPorVotantes'] = inconsistencia_totales

    # 3. Validar JRV
    jrv_digitado = acta_original.get('numero_jrv')
    jrv_pdf = datos_pdf.get('pdf_jrv')

    inconsistencia_jrv = 0
    if jrv_digitado and jrv_pdf and jrv_digitado != jrv_pdf:
        inconsistencia_jrv = 1

    acta_completa['InconsistenciaJrv'] = inconsistencia_jrv

    # 4. Validar papeletas
    papeletas_recibidas = datos_pdf.get('pdf_papeletas_recibidas')
    papeletas_no_utilizadas = datos_pdf.get('pdf_papeletas_no_utilizadas')
    papeletas_utilizadas = datos_pdf.get('pdf_papeletas_utilizadas')

    inconsistencia_papeletas = 0
    if papeletas_recibidas and papeletas_no_utilizadas and papeletas_utilizadas:
        if papeletas_utilizadas != (papeletas_recibidas - papeletas_no_utilizadas):
            inconsistencia_papeletas = 1
        if total_votantes and papeletas_utilizadas != total_votantes:
            inconsistencia_papeletas = 1

    acta_completa['InconsistenciaPapeletas'] = inconsistencia_papeletas

    # 5. Validar números de acta
    numero_acta_inconsistente = 0
    qr = datos_pdf.get('pdf_numero_acta_qr')
    barra = datos_pdf.get('pdf_numero_acta_barra')

    if qr and barra and qr != barra:
        numero_acta_inconsistente = 1

    acta_completa['NumeroActaInconsistente'] = numero_acta_inconsistente

    return acta_completa

def guardar_progreso(resultados: List[Dict], archivo_salida: str, lock: Lock):
    """
    Guarda el progreso actual de forma thread-safe
    Si el archivo existe, carga los datos existentes y actualiza/agrega los nuevos
    """
    with lock:
        datos_existentes = []

        # Cargar datos existentes si el archivo existe
        if os.path.exists(archivo_salida):
            try:
                with open(archivo_salida, 'r', encoding='utf-8') as f:
                    datos_existentes = json.load(f)
                    if not isinstance(datos_existentes, list):
                        datos_existentes = []
            except Exception as e:
                print(f"⚠️  Error cargando datos existentes: {e}")
                datos_existentes = []

        # Crear un diccionario de datos existentes indexado por numero_jrv
        dict_existentes = {acta.get('numero_jrv'): acta for acta in datos_existentes}

        # Actualizar/agregar nuevos resultados
        for acta in resultados:
            numero_jrv = acta.get('numero_jrv')
            if numero_jrv:
                dict_existentes[numero_jrv] = acta

        # Convertir de vuelta a lista ordenada por numero_jrv
        datos_finales = sorted(dict_existentes.values(), key=lambda x: x.get('numero_jrv', 0))

        # Guardar
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(datos_finales, f, ensure_ascii=False, indent=2)

def procesar_acta_worker(acta: Dict, model, jrvs_procesadas: set, resultados: List[Dict],
                          lock: Lock, stats: Dict, jrvs_fallidas: List[int]) -> bool:
    """
    Procesa una sola acta en un worker thread
    Retorna True si fue exitosa, False si hubo error
    """
    numero_jrv = acta.get('numero_jrv', 'Desconocido')
    municipio = acta.get('municipio', 'Desconocido')

    # Verificar si ya fue procesada
    if numero_jrv in jrvs_procesadas:
        with lock:
            print(f"⏭️  JRV {numero_jrv} - {municipio} (ya procesada, omitiendo)")
        return True

    # SOLO usar URL de Drive (permanente)
    url_pdf = acta.get('url_drive')

    with lock:
        print(f"🤖 JRV {numero_jrv} - {municipio}")

    if not url_pdf:
        with lock:
            print(f"   ⚠️  Sin URL de Drive, omitiendo...")
        return True

    # Extraer datos con Gemini (con 3 reintentos automáticos)
    datos_pdf = extraer_votos_con_gemini(url_pdf, model, max_reintentos=3)

    if datos_pdf:
        # Calcular campos de validación
        acta_completa = calcular_campos_validacion(acta, datos_pdf)

        # Eliminar URL del CNE (expira en 2h)
        if 'url_acta_pdf' in acta_completa:
            del acta_completa['url_acta_pdf']

        resultados.append(acta_completa)

        # Guardar en registro de procesadas
        guardar_jrv_procesada(numero_jrv, jrvs_procesadas, lock)

        # Mostrar resumen
        inconsistencias = sum([
            acta_completa.get('InconsistenciaDatosDigitados', 0),
            acta_completa.get('InconsistenciaGrandTotalPorVotantes', 0),
            acta_completa.get('InconsistenciaJrv', 0),
            acta_completa.get('InconsistenciaPapeletas', 0),
            acta_completa.get('NumeroActaInconsistente', 0)
        ])

        estado = "✅ OK" if inconsistencias == 0 else f"⚠️  {inconsistencias} incons."
        with lock:
            print(f"   {estado}")
            stats['exitosas'] += 1
            stats['fallos_consecutivos'] = 0  # Resetear contador
        return True
    else:
        with lock:
            print(f"   ❌ Error procesando (falló después de 3 reintentos)")
            stats['errores'] += 1
            stats['fallos_consecutivos'] += 1
            jrvs_fallidas.append(numero_jrv)

        return False

def main():
    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser(
        description='Validador de Actas con Google Gemini 2.0 Flash',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Ejemplos de uso:
  python validador_gemini_flash.py --depto 05           # Procesar solo CORTES
  python validador_gemini_flash.py --depto 08           # Procesar solo FRANCISCO MORAZAN
  python validador_gemini_flash.py --jrv 5001           # Procesar/reprocesar solo JRV 5001
  python validador_gemini_flash.py                       # Procesar todos los departamentos (usar con precaución)

Códigos de departamentos:
  01 = ATLANTIDA          08 = FRANCISCO MORAZAN    15 = OLANCHO
  02 = COLON              09 = GRACIAS A DIOS       16 = SANTA BARBARA
  03 = COMAYAGUA          10 = INTIBUCA             17 = VALLE
  04 = COPAN              11 = ISLAS DE LA BAHIA    18 = YORO
  05 = CORTES             12 = LA PAZ               20 = VOTO EN EL EXTERIOR
  06 = CHOLUTECA          13 = LEMPIRA
  07 = EL PARAISO         14 = OCOTEPEQUE
        '''
    )
    parser.add_argument('--depto', type=str, help='Código del departamento (ej: 05 para CORTES)')
    parser.add_argument('--jrv', type=int, help='Número de JRV específica a procesar (ej: 5001)')
    args = parser.parse_args()

    print("=" * 80)
    print("VALIDADOR DE ACTAS CON GOOGLE GEMINI 2.0 FLASH (OPTIMIZADO)")
    print("=" * 80)
    print()

    # Validar parámetros
    id_departamento = None
    nombre_departamento = None
    archivo_salida = JSON_OUTPUT
    numero_jrv_especifica = args.jrv

    # Modo JRV específica
    if numero_jrv_especifica:
        print(f"🎯 Modo JRV específica: {numero_jrv_especifica}")
        print(f"   Se procesará solo esta JRV y se sobrescribirá en su archivo de departamento\n")

    # Validar departamento
    if args.depto:
        id_departamento = args.depto.zfill(2)  # Asegurar 2 dígitos (5 -> 05)

        if id_departamento not in DEPARTAMENTOS:
            print(f"❌ Error: Departamento '{id_departamento}' no válido")
            print("\n📋 Departamentos disponibles:")
            for id_dep, nombre in sorted(DEPARTAMENTOS.items()):
                print(f"   {id_dep} = {nombre}")
            sys.exit(1)

        nombre_departamento = DEPARTAMENTOS[id_departamento]
        archivo_salida = os.path.join(OUTPUT_DIR, f"{id_departamento}_{nombre_departamento.replace(' ', '_')}.json")

        print(f"🎯 Departamento seleccionado: {id_departamento} - {nombre_departamento}")
        print(f"📁 Archivo de salida: {archivo_salida}\n")
    elif not numero_jrv_especifica:
        print(f"⚠️  ADVERTENCIA: No se especificó departamento ni JRV")
        print(f"   Se procesarán TODOS los departamentos y se guardarán en: {archivo_salida}")
        print(f"   Usa --depto XX para procesar un departamento específico")
        print(f"   Usa --jrv XXXX para procesar una JRV específica\n")

    # Mostrar configuración
    tier = "GRATUITO (15 req/min)" if USAR_TIER_GRATUITO else "PAGADO (sin límite)"
    print(f"⚙️  Configuración:")
    print(f"   Modelo: {MODELO}")
    print(f"   Tier: {tier}")
    print(f"   Rate limit: {REQUESTS_POR_MINUTO} requests/minuto")
    print(f"   Delay entre requests: {DELAY_ENTRE_REQUESTS:.2f} segundos")
    print(f"   Concurrencia máxima: {CONCURRENCIA_MAXIMA} hilos")
    if LIMITE_ACTAS:
        print(f"   Límite de actas: {LIMITE_ACTAS} (modo prueba)")
    print()

    # Configurar Gemini
    print("🔧 Configurando Google Gemini...")
    try:
        model = configurar_gemini()
        print("✅ Gemini configurado correctamente\n")
    except Exception as e:
        print(f"❌ Error configurando Gemini: {e}")
        print("💡 Verifica que tu API Key sea válida")
        sys.exit(1)

    # Cargar JRVs ya procesadas
    print("📋 Cargando registro de JRVs procesadas...")
    jrvs_procesadas = cargar_jrvs_procesadas()
    print(f"✅ {len(jrvs_procesadas)} JRVs ya procesadas anteriormente\n")

    # Cargar datos
    datos = cargar_json(JSON_INPUT)

    # Filtrar por JRV específica
    if numero_jrv_especifica:
        datos = [acta for acta in datos if acta.get('numero_jrv') == numero_jrv_especifica]

        if len(datos) == 0:
            print(f"❌ Error: No se encontró la JRV {numero_jrv_especifica}")
            sys.exit(1)

        # Determinar archivo de salida basado en el departamento de la JRV
        acta_encontrada = datos[0]
        id_departamento = acta_encontrada.get('id_departamento')
        if id_departamento and id_departamento in DEPARTAMENTOS:
            nombre_departamento = DEPARTAMENTOS[id_departamento]
            archivo_salida = os.path.join(OUTPUT_DIR, f"{id_departamento}_{nombre_departamento.replace(' ', '_')}.json")
            print(f"🔍 JRV encontrada: {numero_jrv_especifica}")
            print(f"📂 Departamento: {id_departamento} - {nombre_departamento}")
            print(f"📁 Se guardará en: {archivo_salida}\n")
        else:
            print(f"⚠️  No se pudo determinar departamento, usando archivo por defecto\n")

        # Forzar procesamiento aunque ya esté en jrvs_procesadas (modo sobreescribir)
        actas_pendientes = datos
    else:
        # Filtrar por departamento si se especificó
        if id_departamento:
            datos = [acta for acta in datos if acta.get('id_departamento') == id_departamento]
            print(f"🔍 Filtrado por departamento {id_departamento}: {len(datos)} actas encontradas\n")

        # Filtrar actas que NO han sido procesadas
        actas_pendientes = [acta for acta in datos
                            if acta.get('numero_jrv') not in jrvs_procesadas]

        print(f"📊 Total actas en archivo: {len(datos)}")
        print(f"✅ Ya procesadas: {len(datos) - len(actas_pendientes)}")
        print(f"⏳ Pendientes: {len(actas_pendientes)}\n")

    # Aplicar límite si está configurado (solo a las pendientes)
    if LIMITE_ACTAS:
        actas_pendientes = actas_pendientes[:LIMITE_ACTAS]
        print(f"⚠️  Modo prueba: procesando solo {len(actas_pendientes)} actas pendientes\n")

    if len(actas_pendientes) == 0:
        print("✅ No hay actas pendientes por procesar!")
        return

    # Procesar actas con concurrencia
    print("=" * 80)
    print(f"🚀 INICIANDO PROCESAMIENTO DE {len(actas_pendientes)} ACTAS")
    print("=" * 80)
    print()

    resultados = []
    lock = Lock()
    stats = {'exitosas': 0, 'errores': 0, 'fallos_consecutivos': 0}
    jrvs_fallidas = []
    tiempo_inicio = time.time()
    proceso_detenido = False

    # Usar ThreadPoolExecutor para procesamiento concurrente
    with ThreadPoolExecutor(max_workers=CONCURRENCIA_MAXIMA) as executor:
        futures = []

        for acta in actas_pendientes:
            # Enviar tarea al pool
            future = executor.submit(
                procesar_acta_worker,
                acta, model, jrvs_procesadas, resultados, lock, stats, jrvs_fallidas
            )
            futures.append(future)

            # Rate limiting: esperar entre envíos
            time.sleep(DELAY_ENTRE_REQUESTS)

        # Esperar a que terminen todas las tareas
        contador = 0
        for future in futures:
            future.result()  # Esperar a que complete
            contador += 1

            # Verificar si hay 3 fallos consecutivos
            with lock:
                if stats['fallos_consecutivos'] >= 3:
                    print()
                    print("=" * 80)
                    print("⛔ PROCESO DETENIDO: 3 fallos consecutivos detectados")
                    print("=" * 80)
                    print("Es posible que haya un problema con la API o la conexión.")
                    print("Revisa los errores anteriores y vuelve a intentar más tarde.")
                    print()
                    proceso_detenido = True
                    break

            # Guardar progreso cada 10 actas
            if contador % 10 == 0:
                guardar_progreso(resultados, archivo_salida, lock)
                with lock:
                    print(f"💾 Progreso guardado ({contador}/{len(actas_pendientes)})")

            # Estadísticas cada 25 actas
            if contador % 25 == 0:
                tiempo_transcurrido = time.time() - tiempo_inicio
                velocidad = contador / tiempo_transcurrido if tiempo_transcurrido > 0 else 0
                tiempo_restante = (len(actas_pendientes) - contador) / velocidad / 60 if velocidad > 0 else 0

                with lock:
                    print()
                    print(f"📊 PROGRESO: {contador}/{len(actas_pendientes)} ({(contador/len(actas_pendientes)*100):.1f}%)")
                    print(f"⚡ Velocidad: {velocidad:.2f} actas/seg")
                    print(f"⏱️  Tiempo restante: ~{tiempo_restante:.1f} minutos")
                    print(f"✅ Exitosas: {stats['exitosas']} | ❌ Errores: {stats['errores']}")
                    print()

    # Guardar resultado final
    print()
    print("=" * 80)
    print("💾 Guardando resultado final...")
    guardar_progreso(resultados, archivo_salida, lock)

    # Estadísticas finales
    tiempo_total = time.time() - tiempo_inicio

    print()
    print("=" * 80)
    print("✅ PROCESAMIENTO COMPLETADO")
    print("=" * 80)
    print(f"📊 Total actas procesadas: {len(actas_pendientes)}")
    print(f"✅ Exitosas: {stats['exitosas']}")
    print(f"❌ Errores: {stats['errores']}")
    print(f"⏱️  Tiempo total: {tiempo_total/60:.1f} minutos")
    if tiempo_total > 0:
        print(f"⚡ Velocidad promedio: {len(actas_pendientes)/tiempo_total:.2f} actas/seg")
    print()
    print(f"📁 Archivo generado: {archivo_salida}")
    print(f"📁 Registro JRVs: {JSON_PROCESADAS}")
    print("=" * 80)
    print()

    # Calcular inconsistencias
    total_inconsistencias = sum(1 for r in resultados
                                if r.get('InconsistenciaDatosDigitados', 0) == 1)

    print(f"📋 Resumen de validación:")
    print(f"   Actas con inconsistencias: {total_inconsistencias}")
    print(f"   Actas correctas: {len(resultados) - total_inconsistencias}")
    if len(resultados) > 0:
        print(f"   Porcentaje de precisión: {((len(resultados) - total_inconsistencias) / len(resultados) * 100):.1f}%")
    print()

    # Mostrar JRVs que fallaron completamente
    if len(jrvs_fallidas) > 0:
        print("=" * 80)
        print(f"⚠️  JRVs QUE FALLARON COMPLETAMENTE ({len(jrvs_fallidas)} actas)")
        print("=" * 80)
        print()
        print("Las siguientes JRVs fallaron después de 3 reintentos:")
        print()

        # Guardar en archivo para fácil reprocesamiento
        archivo_fallidas = 'jrvs_fallidas.json'
        with open(archivo_fallidas, 'w', encoding='utf-8') as f:
            json.dump({
                'jrvs_fallidas': sorted(jrvs_fallidas),
                'total': len(jrvs_fallidas),
                'fecha': time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)

        # Mostrar en grupos de 10 por línea
        for i in range(0, len(jrvs_fallidas), 10):
            grupo = jrvs_fallidas[i:i+10]
            print(f"   {', '.join(map(str, grupo))}")

        print()
        print(f"📁 Lista guardada en: {archivo_fallidas}")
        print()
        print("💡 Para reprocesar una JRV fallida:")
        print(f"   python validador_gemini_flash.py --jrv XXXX")
        print()
        print("=" * 80)
        print()

    if proceso_detenido:
        print("⚠️  ADVERTENCIA: El proceso se detuvo por fallos consecutivos.")
        print("   Algunas actas no fueron procesadas.")
        print("   Vuelve a ejecutar el mismo comando para continuar desde donde quedó.")
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
        print("💾 El progreso se ha guardado hasta donde se procesó")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
