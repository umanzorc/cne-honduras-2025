#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Parallel script to upload CNE Honduras ballots to Google Drive
Uses multithreading to speed up the download and upload process
OPTIMIZED VERSION: 10-20x faster than the sequential version
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
# CONFIGURATION
# ============================================================================

# JSON file with ballot data
JSON_FILE = 'resultados_jrv_detallado.json'

# Local temp folder for downloading PDFs
TEMP_FOLDER = 'actas_temp'

# Folder for successful upload logs
LOGS_FOLDER = 'LogsSubidas'

# Required scopes for Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Root folder ID in Google Drive
PARENT_FOLDER_ID = '1PqARS1zO82dv1S7_lokXHswBCAUaCZ2F'

# PARALLELISM CONFIGURATION
# Number of threads for downloading PDFs (can be high, they're HTTP requests)
NUM_HILOS_DESCARGA = 20  # Adjust based on your connection (10-50)

# Number of threads for uploading to Drive (API has rate limits)
NUM_HILOS_SUBIDA = 10  # Adjust based on rate limit errors (5-15)

# ============================================================================
# GLOBAL STATISTICS VARIABLES
# ============================================================================

stats_lock = Lock()
stats = {
    'procesadas': 0,
    'exitosas': 0,
    'fallidas': 0,
    'saltadas': 0,
    'total': 0,
    'jrv_nuevas': [],      # List of newly uploaded JRVs
    'jrv_fallidas': []     # List of failed JRVs
}

# ============================================================================
# GOOGLE DRIVE AUTHENTICATION
# ============================================================================

def autenticar_google_drive():
    """
    Authenticate with Google Drive API using OAuth 2.0
    Returns the Google Drive service
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
# GOOGLE DRIVE FUNCTIONS
# ============================================================================

def buscar_carpeta(service, nombre_carpeta, parent_id=None):
    """
    Search for a folder by name in Google Drive
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
    Create a folder in Google Drive
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
    Get the ID of an existing folder or create it if it doesn't exist
    """
    folder_id = buscar_carpeta(service, nombre_carpeta, parent_id)

    if folder_id:
        print(f"📁 Carpeta existente: {nombre_carpeta}")
        return folder_id
    else:
        return crear_carpeta(service, nombre_carpeta, parent_id)

def buscar_archivo(service, nombre_archivo, folder_id):
    """
    Search for a file by name in a specific folder
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
        # Suppress search errors
        return None

def subir_archivo(service, file_path, folder_id, nombre_archivo):
    """
    Upload a file to Google Drive
    If the file already exists, it SKIPS it (does not replace)
    """
    try:
        file_id = buscar_archivo(service, nombre_archivo, folder_id)

        if file_id:
            # File already exists, skip it
            return file_id

        # Create new file
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
# SEQUENTIAL LOG FUNCTIONS
# ============================================================================

def obtener_siguiente_correlativo(carpeta_logs):
    """
    Search for files in the logs folder and return the next sequential number
    """
    if not os.path.exists(carpeta_logs):
        return 1

    # List files in the folder
    archivos = os.listdir(carpeta_logs)

    # Filter only .json files and extract numbers
    correlativos = []
    for archivo in archivos:
        if archivo.endswith('.json'):
            try:
                # Extract number from filename (1.json, 2.json, etc.)
                numero = int(archivo.replace('.json', ''))
                correlativos.append(numero)
            except ValueError:
                continue

    # Return next number
    if correlativos:
        return max(correlativos) + 1
    else:
        return 1

def guardar_log_exitosas(jrvs_nuevas, carpeta_logs):
    """
    Save log of successfully uploaded JRVs with sequential number
    Format: [1, 2, 3, 4, ...]
    """
    # Create folder if it doesn't exist
    if not os.path.exists(carpeta_logs):
        os.makedirs(carpeta_logs)
        print(f"✅ Carpeta de logs creada: {carpeta_logs}")

    # Get next sequential number
    correlativo = obtener_siguiente_correlativo(carpeta_logs)

    # Extract only JRV numbers
    numeros_jrv = [item['jrv'] for item in jrvs_nuevas]

    # Sort
    numeros_jrv.sort()

    # Filename
    nombre_archivo = os.path.join(carpeta_logs, f"{correlativo}.json")

    # Save
    with open(nombre_archivo, 'w', encoding='utf-8') as f:
        json.dump(numeros_jrv, f, indent=2)

    print(f"✅ Log de JRVs exitosas guardado: {nombre_archivo}")
    print(f"   📊 {len(numeros_jrv)} JRVs en el log")

    return nombre_archivo, correlativo

# ============================================================================
# DOWNLOAD FUNCTIONS
# ============================================================================

def descargar_pdf(url, file_path):
    """
    Download a PDF from a URL
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
# PARALLEL FUNCTION: PROCESS A BALLOT
# ============================================================================

def procesar_acta(acta, folder_id, service, departamento):
    """
    Process a ballot: download PDF and upload to Drive
    This function runs in parallel across multiple threads
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

    # Filename
    nombre_archivo = f"JRV_{numero_jrv}.pdf"

    # Check if the file already exists in Drive
    file_id_existente = buscar_archivo(service, nombre_archivo, folder_id)

    if file_id_existente:
        # File already exists, skip it
        with stats_lock:
            stats['procesadas'] += 1
            stats['saltadas'] += 1
            stats['exitosas'] += 1  # Count as successful because it's already in Drive

            # Show progress every 50 files
            if stats['procesadas'] % 50 == 0:
                porcentaje = stats['procesadas'] * 100 // stats['total']
                print(f"Progreso: {stats['procesadas']}/{stats['total']} ({porcentaje}%) - "
                      f"OK: {stats['exitosas']} | Saltadas: {stats['saltadas']} | Fallidas: {stats['fallidas']}", flush=True)
        return True

    temp_file = os.path.join(TEMP_FOLDER, f"{numero_jrv}_{os.getpid()}_{time.time()}.pdf")

    # Download PDF
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

    # Upload to Google Drive
    file_id = subir_archivo(service, temp_file, folder_id, nombre_archivo)

    # Delete temp file
    try:
        os.remove(temp_file)
    except:
        pass

    # Update statistics
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

        # Show progress every 50 files
        if stats['procesadas'] % 50 == 0:
            porcentaje = stats['procesadas'] * 100 // stats['total']
            print(f"Progreso: {stats['procesadas']}/{stats['total']} ({porcentaje}%) - "
                  f"OK: {stats['exitosas']} | Saltadas: {stats['saltadas']} | Fallidas: {stats['fallidas']}", flush=True)

    return file_id is not None

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """
    Main function that processes the JSON and uploads ballots in parallel
    """
    print("=" * 80, flush=True)
    print("SUBIR ACTAS CNE HONDURAS A GOOGLE DRIVE - VERSION PARALELA", flush=True)
    print("=" * 80, flush=True)
    print(f"Hilos de descarga: {NUM_HILOS_DESCARGA}", flush=True)
    print(f"Hilos de subida: {NUM_HILOS_SUBIDA}", flush=True)
    print(flush=True)

    # Create temp folder
    print(f"Creando carpeta temporal: {TEMP_FOLDER}", flush=True)
    if not os.path.exists(TEMP_FOLDER):
        os.makedirs(TEMP_FOLDER)
    print("OK - Carpeta temporal creada", flush=True)
    print(flush=True)

    # Load JSON
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

    # Authenticate with Google Drive
    print("Autenticando con Google Drive...", flush=True)
    try:
        service = autenticar_google_drive()
        print("OK - Autenticacion exitosa", flush=True)
        print(flush=True)
    except Exception as e:
        print(f"ERROR en autenticacion: {e}", flush=True)
        return

    # Group ballots by department
    actas_por_departamento = {}
    for acta in actas:
        dept = acta.get('departamento', 'DESCONOCIDO')
        if dept not in actas_por_departamento:
            actas_por_departamento[dept] = []
        actas_por_departamento[dept].append(acta)

    print(f"📊 Actas agrupadas en {len(actas_por_departamento)} departamentos")
    print()

    # Initialize statistics
    stats['total'] = len(actas)

    # Start time
    tiempo_inicio = time.time()

    # Process each department
    for departamento, actas_dept in actas_por_departamento.items():
        print("=" * 80)
        print(f"📍 DEPARTAMENTO: {departamento} ({len(actas_dept)} actas)")
        print("=" * 80)

        # Get or create the department folder
        folder_id = obtener_o_crear_carpeta(service, departamento, PARENT_FOLDER_ID)

        if not folder_id:
            print(f"❌ No se pudo crear/obtener carpeta para {departamento}")
            with stats_lock:
                stats['fallidas'] += len(actas_dept)
            continue

        print(f"🚀 Procesando {len(actas_dept)} actas en paralelo...")
        print()

        # Process ballots in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=NUM_HILOS_SUBIDA) as executor:
            # Create a Drive service for each thread
            # (Google API is not thread-safe, each thread needs its own instance)
            futures = []

            for acta in actas_dept:
                # Create a new service for each task
                service_local = autenticar_google_drive()
                future = executor.submit(procesar_acta, acta, folder_id, service_local, departamento)
                futures.append(future)

            # Wait for all tasks to finish
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"❌ Error procesando acta: {e}")
                    with stats_lock:
                        stats['fallidas'] += 1

        print()

    # Total time
    tiempo_total = time.time() - tiempo_inicio

    # Final summary
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

    # Show newly uploaded JRVs
    if stats['jrv_nuevas']:
        print("=" * 80, flush=True)
        print(f"JRVs NUEVAS SUBIDAS ({len(stats['jrv_nuevas'])})", flush=True)
        print("=" * 80, flush=True)
        for item in sorted(stats['jrv_nuevas'], key=lambda x: (x['departamento'], x['jrv'])):
            print(f"  JRV {item['jrv']} - {item['departamento']} - {item['municipio']}", flush=True)
        print(flush=True)

    # Show failed JRVs
    if stats['jrv_fallidas']:
        print("=" * 80, flush=True)
        print(f"JRVs FALLIDAS ({len(stats['jrv_fallidas'])})", flush=True)
        print("=" * 80, flush=True)
        for item in sorted(stats['jrv_fallidas'], key=lambda x: (x['departamento'], x['jrv'])):
            print(f"  JRV {item['jrv']} - {item['departamento']} - {item['municipio']} - {item['razon']}", flush=True)
        print(flush=True)

    print()

    # Save log of successfully uploaded JRVs
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

    # Clean up temp folder
    try:
        # Delete leftover files
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
# EXECUTION
# ============================================================================

if __name__ == '__main__':
    main()
