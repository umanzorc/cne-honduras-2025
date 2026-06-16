#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to transfer ballots from one Google Drive account to another
Allows moving the 19k ballots from your personal account to an anonymous account

IMPORTANT: This script requires two credential files:
- credentials_original.json: Credentials for your personal account (source)
- credentials_anonima.json: Credentials for the anonymous account (destination)
"""

import json
import os
import time
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

# Required scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

# Parent folder IDs (optional)
PARENT_FOLDER_ID_DESTINO = None  # Change if you want to upload to a specific folder

def autenticar_drive(credentials_file, token_file):
    """
    Authenticate with Google Drive using OAuth 2.0

    Args:
        credentials_file: Credentials file (credentials.json)
        token_file: Token file (created automatically)

    Returns:
        Authenticated Google Drive service
    """
    creds = None

    # Check if token already exists
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                raise FileNotFoundError(
                    f"No se encontró {credentials_file}. "
                    f"Descárgalo desde Google Cloud Console."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def obtener_carpeta_por_nombre(service, nombre_carpeta, parent_id=None):
    """
    Search for a folder by name in Google Drive

    Args:
        service: Google Drive service
        nombre_carpeta: Name of the folder to search for
        parent_id: Parent folder ID (optional)

    Returns:
        Folder ID if found, None if not found
    """
    query = f"name='{nombre_carpeta}' and mimeType='application/vnd.google-apps.folder' and trashed=false"

    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        pageSize=1
    ).execute()

    items = results.get('files', [])

    if items:
        return items[0]['id']
    return None


def crear_carpeta(service, nombre_carpeta, parent_id=None):
    """
    Create a folder in Google Drive

    Args:
        service: Google Drive service
        nombre_carpeta: Folder name
        parent_id: Parent folder ID (optional)

    Returns:
        ID of the created folder
    """
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

    return folder.get('id')


def descargar_archivo_desde_url_drive(url_drive, archivo_destino):
    """
    Download a file from Google Drive using a public URL

    Args:
        url_drive: File URL in Google Drive
        archivo_destino: Path where to save the file

    Returns:
        True if downloaded successfully, False if failed
    """
    try:
        # Extract file_id from the URL
        # Format: https://drive.google.com/file/d/FILE_ID/view?usp=...
        file_id = url_drive.split('/d/')[1].split('/')[0]

        # Direct download URL
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        # Download file
        response = requests.get(download_url, stream=True)

        if response.status_code == 200:
            with open(archivo_destino, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            print(f"  ⚠️ Error al descargar: HTTP {response.status_code}")
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def subir_archivo_a_drive(service, archivo_local, nombre_archivo, folder_id):
    """
    Upload a file to Google Drive

    Args:
        service: Google Drive service
        archivo_local: Local file path
        nombre_archivo: Name to save the file as in Drive
        folder_id: Destination folder ID

    Returns:
        ID of the uploaded file
    """
    file_metadata = {
        'name': nombre_archivo,
        'parents': [folder_id]
    }

    media = MediaFileUpload(
        archivo_local,
        mimetype='application/pdf',
        resumable=True
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    return file


def hacer_archivo_publico(service, file_id):
    """
    Make a file public (anyone with the link can view)

    Args:
        service: Google Drive service
        file_id: File ID

    Returns:
        Public URL of the file
    """
    # Change permissions to public
    service.permissions().create(
        fileId=file_id,
        body={
            'type': 'anyone',
            'role': 'reader'
        }
    ).execute()

    # Get URL
    file = service.files().get(
        fileId=file_id,
        fields='webViewLink'
    ).execute()

    # Change URL format
    url = file.get('webViewLink')
    # From: https://drive.google.com/file/d/FILE_ID/view
    # To:   https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    if '?usp=' not in url:
        url = url.replace('/view', '/view?usp=sharing')
    else:
        url = url.replace('?usp=drivesdk', '?usp=sharing')

    return url


def transferir_actas(json_origen, json_destino, credentials_origen, credentials_destino):
    """
    Transfer all ballots from one Drive account to another

    Args:
        json_origen: JSON file with source URLs
        json_destino: JSON output file with updated URLs
        credentials_origen: credentials.json for source account
        credentials_destino: credentials.json for destination account
    """

    print("=" * 80)
    print("TRANSFERENCIA DE ACTAS ENTRE CUENTAS DE GOOGLE DRIVE")
    print("=" * 80)

    # Authenticate both accounts
    print("\n1. Autenticando cuenta ORIGEN...")
    service_origen = autenticar_drive(credentials_origen, "token_origen.json")
    print("   ✓ Autenticado en cuenta origen")

    print("\n2. Autenticando cuenta DESTINO (anónima)...")
    service_destino = autenticar_drive(credentials_destino, "token_destino.json")
    print("   ✓ Autenticado en cuenta destino")

    # Read JSON
    print(f"\n3. Leyendo archivo JSON: {json_origen}")
    with open(json_origen, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    print(f"   Total de registros: {len(datos)}")

    # Count ballots with url_drive
    actas_con_url = [r for r in datos if r.get('url_drive')]
    print(f"   Actas con url_drive: {len(actas_con_url)}")

    # Create folders by department
    print("\n4. Creando estructura de carpetas en cuenta destino...")
    carpetas_departamentos = {}
    departamentos_unicos = set(r['departamento'] for r in datos if r.get('url_drive'))

    for departamento in sorted(departamentos_unicos):
        # Check if the folder already exists
        folder_id = obtener_carpeta_por_nombre(service_destino, departamento)

        if not folder_id:
            folder_id = crear_carpeta(service_destino, departamento, PARENT_FOLDER_ID_DESTINO)
            print(f"   ✓ Carpeta creada: {departamento}")
        else:
            print(f"   ✓ Carpeta existente: {departamento}")

        carpetas_departamentos[departamento] = folder_id

    # Transfer files
    print("\n5. Transfiriendo archivos...")
    print("   (Este proceso puede tardar varias horas para 19k actas)")
    print("-" * 80)

    archivos_temp = "actas_temp"
    os.makedirs(archivos_temp, exist_ok=True)

    total = len(actas_con_url)
    exitosos = 0
    fallidos = 0
    errores = []

    for i, registro in enumerate(actas_con_url, 1):
        url_original = registro['url_drive']
        numero_jrv = registro['numero_jrv']
        departamento = registro['departamento']
        nombre_archivo = f"JRV_{numero_jrv}.pdf"
        archivo_temp = os.path.join(archivos_temp, nombre_archivo)

        print(f"\n[{i}/{total}] JRV {numero_jrv} - {departamento}")

        try:
            # Download from source account
            print(f"  → Descargando...")
            if descargar_archivo_desde_url_drive(url_original, archivo_temp):
                # Upload to destination account
                print(f"  → Subiendo a cuenta destino...")
                folder_id = carpetas_departamentos[departamento]
                archivo_subido = subir_archivo_a_drive(
                    service_destino,
                    archivo_temp,
                    nombre_archivo,
                    folder_id
                )

                # Make public
                url_nueva = hacer_archivo_publico(service_destino, archivo_subido['id'])

                # Update URL in the record
                registro['url_drive'] = url_nueva

                # Delete temp file
                os.remove(archivo_temp)

                exitosos += 1
                print(f"  ✓ Transferido exitosamente")
                print(f"  Nueva URL: {url_nueva}")

            else:
                fallidos += 1
                errores.append({
                    'jrv': numero_jrv,
                    'departamento': departamento,
                    'error': 'Error al descargar'
                })

        except Exception as e:
            fallidos += 1
            errores.append({
                'jrv': numero_jrv,
                'departamento': departamento,
                'error': str(e)
            })
            print(f"  ❌ Error: {e}")

        # Delay to avoid rate limiting
        time.sleep(0.5)

        # Show progress every 100 files
        if i % 100 == 0:
            print("\n" + "=" * 80)
            print(f"PROGRESO: {i}/{total} ({i/total*100:.1f}%)")
            print(f"Exitosos: {exitosos} | Fallidos: {fallidos}")
            print("=" * 80)

    # Save updated JSON
    print(f"\n6. Guardando JSON actualizado: {json_destino}")
    with open(json_destino, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    # Save error log
    if errores:
        with open('errores_transferencia.json', 'w', encoding='utf-8') as f:
            json.dump(errores, f, ensure_ascii=False, indent=2)

    # Final summary
    print("\n" + "=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80)
    print(f"Total de actas procesadas: {total}")
    print(f"Transferencias exitosas: {exitosos} ({exitosos/total*100:.1f}%)")
    print(f"Transferencias fallidas: {fallidos} ({fallidos/total*100:.1f}%)")
    print(f"\nArchivo JSON actualizado: {json_destino}")

    if errores:
        print(f"Log de errores: errores_transferencia.json")

    print("\n✓ Proceso completado!")


if __name__ == "__main__":
    # CONFIGURATION
    # ============================================

    # Input/output files
    json_origen = "resultados_validados_gemini.json"   # JSON with original URLs
    json_destino = "resultados_validados_gemini_ANONIMO.json"  # JSON with new URLs

    # Credential files
    credentials_origen = "credentials_original.json"  # Your personal account
    credentials_destino = "credentials_anonima.json"  # New anonymous account

    # ============================================

    # INSTRUCTIONS:
    # 1. Download credentials.json from your PERSONAL account and rename it to credentials_original.json
    # 2. Create an ANONYMOUS Google account (via Tor, public WiFi)
    # 3. Download credentials.json from the anonymous account and rename it to credentials_anonima.json
    # 4. Run this script

    print("""
    ⚠️ IMPORTANTE: Antes de ejecutar, asegúrate de tener:

    1. credentials_original.json (de tu cuenta personal)
    2. credentials_anonima.json (de la cuenta anónima)
    3. resultados_validados_gemini.json (con las URLs originales)

    ¿Deseas continuar? (s/n): """, end='')

    respuesta = input().strip().lower()

    if respuesta == 's':
        try:
            transferir_actas(
                json_origen,
                json_destino,
                credentials_origen,
                credentials_destino
            )
        except Exception as e:
            print(f"\n❌ Error crítico: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\nOperación cancelada.")
