#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script PARALELO para subir actas del CNE Honduras a Google Drive
Usa multithreading para acelerar el proceso de descarga y subida
VERSIÓN OPTIMIZADA: 10-20x más rápido que la versión secuencial
"""

import json
import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Archivo JSON con los datos de las actas
JSON_FILE = 'resultados_jrv_detallado.json'

# Carpeta local temporal para descargar PDFs
TEMP_FOLDER = 'actas_temp'

# Carpeta para logs de subidas exitosas
LOGS_FOLDER = 'LogsSubidas'

# Scopes necesarios para Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# ID de la carpeta raíz en Google Drive
PARENT_FOLDER_ID = '1PqARS1zO82dv1S7_lokXHswBCAUaCZ2F'

# CONFIGURACIÓN DE PARALELISMO
# Número de hilos para descargar PDFs (puede ser alto, son peticiones HTTP)
NUM_HILOS_DESCARGA = 20  # Ajusta según tu conexión (10-50)

# Número de hilos para subir a Drive (API tiene rate limits)
NUM_HILOS_SUBIDA = 10  # Ajusta según errores de rate limit (5-15)

# ============================================================================
# VARIABLES GLOBALES PARA ESTADÍSTICAS
# ============================================================================

stats_lock = Lock()
stats = {
    'procesadas': 0,
    'exitosas': 0,
    'fallidas': 0,
    'saltadas': 0,
    'total': 0,
    'jrv_nuevas': [],      # Lista de JRVs nuevas subidas
    'jrv_fallidas': []     # Lista de JRVs fallidas
}

# ============================================================================
# AUTENTICACIÓN CON GOOGLE DRIVE
# ============================================================================

def autenticar_google_drive():
    """
    Autentica con Google Drive API usando OAuth 2.0
    Retorna el servicio de Google Drive
    """
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

# ============================================================================
# FUNCIONES DE GOOGLE DRIVE
# ============================================================================

def buscar_carpeta(service, nombre_carpeta, parent_id=None):
    """
    Busca una carpeta por nombre en Google Drive
    """
    try:
        query = f"name='{nombre_carpeta}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        items = results.get('files', [])

        if items:
            return items[0]['id']

        return None

    except HttpError as error:
        print(f"Error buscando carpeta '{nombre_carpeta}': {error}")
        return None

def crear_carpeta(service, nombre_carpeta, parent_id=None):
    """
    Crea una carpeta en Google Drive
    """
    try:
        file_metadata = {
            'name': nombre_carpeta,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        if parent_id:
            file_metadata['parents'] = [parent_id]

        folder = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        print(f"✅ Carpeta creada: {nombre_carpeta}")
        return folder.get('id')

    except HttpError as error:
        print(f"Error creando carpeta '{nombre_carpeta}': {error}")
        return None

def obtener_o_crear_carpeta(service, nombre_carpeta, parent_id=None):
    """
    Obtiene el ID de una carpeta existente o la crea si no existe
    """
    folder_id = buscar_carpeta(service, nombre_carpeta, parent_id)

    if folder_id:
        print(f"📁 Carpeta existente: {nombre_carpeta}")
        return folder_id
    else:
        return crear_carpeta(service, nombre_carpeta, parent_id)

def buscar_archivo(service, nombre_archivo, folder_id):
    """
    Busca un archivo por nombre en una carpeta específica
    """
    try:
        query = f"name='{nombre_archivo}' and '{folder_id}' in parents and trashed=false"

        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        items = results.get('files', [])

        if items:
            return items[0]['id']

        return None

    except HttpError as error:
        # Silenciar errores de búsqueda
        return None

def subir_archivo(service, file_path, folder_id, nombre_archivo):
    """
    Sube un archivo a Google Drive
    Si el archivo ya existe, lo SALTA (no lo reemplaza)
    """
    try:
        file_id = buscar_archivo(service, nombre_archivo, folder_id)

        if file_id:
            # Archivo ya existe, saltarlo
            return file_id

        # Crear nuevo archivo
        file_metadata = {
            'name': nombre_archivo,
            'parents': [folder_id]
        }

        media = MediaFileUpload(file_path, mimetype='application/pdf')

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        return file.get('id')

    except HttpError as error:
        print(f"❌ Error subiendo '{nombre_archivo}': {error}")
        return None

# ============================================================================
# FUNCIONES DE LOGS CORRELATIVOS
# ============================================================================

def obtener_siguiente_correlativo(carpeta_logs):
    """
    Busca archivos en la carpeta de logs y retorna el siguiente número de correlativo
    """
    if not os.path.exists(carpeta_logs):
        return 1

    # Listar archivos en la carpeta
    archivos = os.listdir(carpeta_logs)

    # Filtrar solo archivos .json y extraer números
    correlativos = []
    for archivo in archivos:
        if archivo.endswith('.json'):
            try:
                # Extraer número del nombre (1.json, 2.json, etc.)
                numero = int(archivo.replace('.json', ''))
                correlativos.append(numero)
            except ValueError:
                continue

    # Retornar siguiente número
    if correlativos:
        return max(correlativos) + 1
    else:
        return 1

def guardar_log_exitosas(jrvs_nuevas, carpeta_logs):
    """
    Guarda log de JRVs subidas exitosamente con correlativo
    Formato: [1, 2, 3, 4, ...]
    """
    # Crear carpeta si no existe
    if not os.path.exists(carpeta_logs):
        os.makedirs(carpeta_logs)
        print(f"✅ Carpeta de logs creada: {carpeta_logs}")

    # Obtener siguiente correlativo
    correlativo = obtener_siguiente_correlativo(carpeta_logs)

    # Extraer solo los números de JRV
    numeros_jrv = [item['jrv'] for item in jrvs_nuevas]

    # Ordenar
    numeros_jrv.sort()

    # Nombre del archivo
    nombre_archivo = os.path.join(carpeta_logs, f"{correlativo}.json")

    # Guardar
    with open(nombre_archivo, 'w', encoding='utf-8') as f:
        json.dump(numeros_jrv, f, indent=2)

    print(f"✅ Log de JRVs exitosas guardado: {nombre_archivo}")
    print(f"   📊 {len(numeros_jrv)} JRVs en el log")

    return nombre_archivo, correlativo

# ============================================================================
# FUNCIONES DE DESCARGA
# ============================================================================

def descargar_pdf(url, file_path):
    """
    Descarga un PDF desde una URL
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with open(file_path, 'wb') as f:
            f.write(response.content)

        return True

    except Exception as e:
        return False

# ============================================================================
# FUNCIÓN PARALELA: PROCESAR UN ACTA
# ============================================================================

def procesar_acta(acta, folder_id, service, departamento):
    """
    Procesa una acta: descarga PDF y sube a Drive
    Esta función se ejecuta en paralelo en múltiples hilos
    """
    numero_jrv = acta.get('numero_jrv', 'DESCONOCIDO')
    municipio = acta.get('municipio', 'DESCONOCIDO')
    url_pdf = acta.get('url_acta_pdf', '')

    if not url_pdf:
        with stats_lock:
            stats['procesadas'] += 1
            stats['fallidas'] += 1
            stats['jrv_fallidas'].append({
                'jrv': numero_jrv,
                'departamento': departamento,
                'municipio': municipio,
                'razon': 'Sin URL de PDF'
            })
        return False

    # Nombre del archivo
    nombre_archivo = f"JRV_{numero_jrv}.pdf"

    # Verificar si el archivo ya existe en Drive
    file_id_existente = buscar_archivo(service, nombre_archivo, folder_id)

    if file_id_existente:
        # Archivo ya existe, saltarlo
        with stats_lock:
            stats['procesadas'] += 1
            stats['saltadas'] += 1
            stats['exitosas'] += 1  # Contar como exitosa porque ya está en Drive

            # Mostrar progreso cada 50 archivos
            if stats['procesadas'] % 50 == 0:
                porcentaje = stats['procesadas'] * 100 // stats['total']
                print(f"Progreso: {stats['procesadas']}/{stats['total']} ({porcentaje}%) - "
                      f"OK: {stats['exitosas']} | Saltadas: {stats['saltadas']} | Fallidas: {stats['fallidas']}", flush=True)
        return True

    temp_file = os.path.join(TEMP_FOLDER, f"{numero_jrv}_{os.getpid()}_{time.time()}.pdf")

    # Descargar PDF
    if not descargar_pdf(url_pdf, temp_file):
        with stats_lock:
            stats['procesadas'] += 1
            stats['fallidas'] += 1
            stats['jrv_fallidas'].append({
                'jrv': numero_jrv,
                'departamento': departamento,
                'municipio': municipio,
                'razon': 'Error descargando PDF'
            })
        return False

    # Subir a Google Drive
    file_id = subir_archivo(service, temp_file, folder_id, nombre_archivo)

    # Eliminar archivo temporal
    try:
        os.remove(temp_file)
    except:
        pass

    # Actualizar estadísticas
    with stats_lock:
        stats['procesadas'] += 1
        if file_id:
            stats['exitosas'] += 1
            stats['jrv_nuevas'].append({
                'jrv': numero_jrv,
                'departamento': departamento,
                'municipio': municipio
            })
        else:
            stats['fallidas'] += 1
            stats['jrv_fallidas'].append({
                'jrv': numero_jrv,
                'departamento': departamento,
                'municipio': municipio,
                'razon': 'Error subiendo a Drive'
            })

        # Mostrar progreso cada 50 archivos
        if stats['procesadas'] % 50 == 0:
            porcentaje = stats['procesadas'] * 100 // stats['total']
            print(f"Progreso: {stats['procesadas']}/{stats['total']} ({porcentaje}%) - "
                  f"OK: {stats['exitosas']} | Saltadas: {stats['saltadas']} | Fallidas: {stats['fallidas']}", flush=True)

    return file_id is not None

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """
    Función principal que procesa el JSON y sube las actas en paralelo
    """
    print("=" * 80, flush=True)
    print("SUBIR ACTAS CNE HONDURAS A GOOGLE DRIVE - VERSION PARALELA", flush=True)
    print("=" * 80, flush=True)
    print(f"Hilos de descarga: {NUM_HILOS_DESCARGA}", flush=True)
    print(f"Hilos de subida: {NUM_HILOS_SUBIDA}", flush=True)
    print(flush=True)

    # Crear carpeta temporal
    print(f"Creando carpeta temporal: {TEMP_FOLDER}", flush=True)
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    print("OK - Carpeta temporal creada", flush=True)
    print(flush=True)

    # Cargar JSON
    print(f"Cargando JSON: {JSON_FILE}", flush=True)
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            actas = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: No se encontro el archivo {JSON_FILE}", flush=True)
        return
    except json.JSONDecodeError:
        print(f"ERROR: El archivo {JSON_FILE} no es un JSON valido", flush=True)
        return

    print(f"OK - JSON cargado: {len(actas)} actas encontradas", flush=True)
    print(flush=True)

    # Autenticar con Google Drive
    print("Autenticando con Google Drive...", flush=True)
    try:
        service = autenticar_google_drive()
        print("OK - Autenticacion exitosa", flush=True)
        print(flush=True)
    except Exception as e:
        print(f"ERROR en autenticacion: {e}", flush=True)
        return

    # Agrupar actas por departamento
    actas_por_departamento = {}
    for acta in actas:
        dept = acta.get('departamento', 'DESCONOCIDO')
        if dept not in actas_por_departamento:
            actas_por_departamento[dept] = []
        actas_por_departamento[dept].append(acta)

    print(f"📊 Actas agrupadas en {len(actas_por_departamento)} departamentos")
    print()

    # Inicializar estadísticas
    stats['total'] = len(actas)

    # Tiempo de inicio
    tiempo_inicio = time.time()

    # Procesar cada departamento
    for departamento, actas_dept in actas_por_departamento.items():
        print("=" * 80)
        print(f"📍 DEPARTAMENTO: {departamento} ({len(actas_dept)} actas)")
        print("=" * 80)

        # Obtener o crear carpeta del departamento
        folder_id = obtener_o_crear_carpeta(service, departamento, PARENT_FOLDER_ID)

        if not folder_id:
            print(f"❌ No se pudo crear/obtener carpeta para {departamento}")
            with stats_lock:
                stats['fallidas'] += len(actas_dept)
            continue

        print(f"🚀 Procesando {len(actas_dept)} actas en paralelo...")
        print()

        # Procesar actas en paralelo usando ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=NUM_HILOS_SUBIDA) as executor:
            # Crear un servicio de Drive para cada hilo
            # (la API de Google no es thread-safe, cada hilo necesita su propia instancia)
            futures = []

            for acta in actas_dept:
                # Crear un nuevo servicio para cada tarea
                service_local = autenticar_google_drive()
                future = executor.submit(procesar_acta, acta, folder_id, service_local, departamento)
                futures.append(future)

            # Esperar a que todas las tareas terminen
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"❌ Error procesando acta: {e}")
                    with stats_lock:
                        stats['fallidas'] += 1

        print()

    # Tiempo total
    tiempo_total = time.time() - tiempo_inicio

    # Resumen final
    print()
    print("=" * 80, flush=True)
    print("RESUMEN FINAL", flush=True)
    print("=" * 80, flush=True)
    print(f"Actas procesadas exitosamente: {stats['exitosas']}", flush=True)
    print(f"Actas saltadas (ya existian): {stats['saltadas']}", flush=True)
    print(f"Actas nuevas subidas: {len(stats['jrv_nuevas'])}", flush=True)
    print(f"Actas fallidas: {stats['fallidas']}", flush=True)
    print(f"Total: {stats['total']}", flush=True)
    print(f"Tasa de exito: {stats['exitosas']*100//stats['total'] if stats['total'] > 0 else 0}%", flush=True)
    print(f"Tiempo total: {tiempo_total/60:.2f} minutos", flush=True)
    print(f"Velocidad: {stats['total']/tiempo_total*60:.1f} actas/minuto", flush=True)
    print(flush=True)

    # Mostrar JRVs nuevas subidas
    if stats['jrv_nuevas']:
        print("=" * 80, flush=True)
        print(f"JRVs NUEVAS SUBIDAS ({len(stats['jrv_nuevas'])})", flush=True)
        print("=" * 80, flush=True)
        for item in sorted(stats['jrv_nuevas'], key=lambda x: (x['departamento'], x['jrv'])):
            print(f"  JRV {item['jrv']} - {item['departamento']} - {item['municipio']}", flush=True)
        print(flush=True)

    # Mostrar JRVs fallidas
    if stats['jrv_fallidas']:
        print("=" * 80, flush=True)
        print(f"JRVs FALLIDAS ({len(stats['jrv_fallidas'])})", flush=True)
        print("=" * 80, flush=True)
        for item in sorted(stats['jrv_fallidas'], key=lambda x: (x['departamento'], x['jrv'])):
            print(f"  JRV {item['jrv']} - {item['departamento']} - {item['municipio']} - {item['razon']}", flush=True)
        print(flush=True)

    print()

    # Guardar log de JRVs subidas exitosamente
    if stats['jrv_nuevas']:
        print("=" * 80, flush=True)
        print("GUARDANDO LOG DE JRVs EXITOSAS", flush=True)
        print("=" * 80, flush=True)
        try:
            archivo_log, correlativo = guardar_log_exitosas(stats['jrv_nuevas'], LOGS_FOLDER)
            print(f"📁 Archivo: {archivo_log}")
            print(f"🔢 Correlativo: {correlativo}")
        except Exception as e:
            print(f"❌ Error guardando log: {e}")
        print()

    # Limpiar carpeta temporal
    try:
        # Eliminar archivos residuales
        for file in os.listdir(TEMP_FOLDER):
            try:
                os.remove(os.path.join(TEMP_FOLDER, file))
            except:
                pass
        os.rmdir(TEMP_FOLDER)
        print(f"🗑️  Carpeta temporal eliminada")
    except:
        print(f"⚠️  No se pudo eliminar carpeta temporal: {TEMP_FOLDER}")

# ============================================================================
# EJECUCIÓN
# ============================================================================

if __name__ == '__main__':
    main()
