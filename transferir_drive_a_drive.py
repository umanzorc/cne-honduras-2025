#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para transferir actas de una cuenta de Google Drive a otra
Permite mover las 19k actas de tu cuenta personal a una cuenta anónima

IMPORTANTE: Este script requiere dos archivos de credenciales:
- credentials_original.json: Credenciales de tu cuenta personal (origen)
- credentials_anonima.json: Credenciales de la cuenta anónima (destino)
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

# Scopes necesarios
SCOPES = ['https://www.googleapis.com/auth/drive']

# IDs de carpetas padre (opcional)
PARENT_FOLDER_ID_DESTINO = None  # Cambiar si quieres subir a carpeta específica

def autenticar_drive(credentials_file, token_file):
    """
    Autentica con Google Drive usando OAuth 2.0

    Args:
        credentials_file: Archivo de credenciales (credentials.json)
        token_file: Archivo de token (se crea automáticamente)

    Returns:
        Servicio de Google Drive autenticado
    """
    creds = None

    # Verificar si ya existe token
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # Si no hay credenciales válidas, autenticar
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

        # Guardar credenciales para próxima ejecución
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)


def obtener_carpeta_por_nombre(service, nombre_carpeta, parent_id=None):
    """
    Busca una carpeta por nombre en Google Drive

    Args:
        service: Servicio de Google Drive
        nombre_carpeta: Nombre de la carpeta a buscar
        parent_id: ID de la carpeta padre (opcional)

    Returns:
        ID de la carpeta si existe, None si no existe
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
    Crea una carpeta en Google Drive

    Args:
        service: Servicio de Google Drive
        nombre_carpeta: Nombre de la carpeta
        parent_id: ID de la carpeta padre (opcional)

    Returns:
        ID de la carpeta creada
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
    Descarga un archivo desde Google Drive usando URL pública

    Args:
        url_drive: URL del archivo en Google Drive
        archivo_destino: Ruta donde guardar el archivo

    Returns:
        True si se descargó exitosamente, False si falló
    """
    try:
        # Extraer file_id de la URL
        # Formato: https://drive.google.com/file/d/FILE_ID/view?usp=...
        file_id = url_drive.split('/d/')[1].split('/')[0]

        # URL de descarga directa
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        # Descargar archivo
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
    Sube un archivo a Google Drive

    Args:
        service: Servicio de Google Drive
        archivo_local: Ruta del archivo local
        nombre_archivo: Nombre con el que se guardará en Drive
        folder_id: ID de la carpeta destino

    Returns:
        ID del archivo subido
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
    Hace un archivo público (cualquiera con el enlace puede ver)

    Args:
        service: Servicio de Google Drive
        file_id: ID del archivo

    Returns:
        URL pública del archivo
    """
    # Cambiar permisos a público
    service.permissions().create(
        fileId=file_id,
        body={
            'type': 'anyone',
            'role': 'reader'
        }
    ).execute()

    # Obtener URL
    file = service.files().get(
        fileId=file_id,
        fields='webViewLink'
    ).execute()

    # Cambiar formato de URL
    url = file.get('webViewLink')
    # De: https://drive.google.com/file/d/FILE_ID/view
    # A: https://drive.google.com/file/d/FILE_ID/view?usp=sharing
    if '?usp=' not in url:
        url = url.replace('/view', '/view?usp=sharing')
    else:
        url = url.replace('?usp=drivesdk', '?usp=sharing')

    return url


def transferir_actas(json_origen, json_destino, credentials_origen, credentials_destino):
    """
    Transfiere todas las actas de una cuenta de Drive a otra

    Args:
        json_origen: Archivo JSON con URLs de origen
        json_destino: Archivo JSON de salida con URLs actualizadas
        credentials_origen: credentials.json de cuenta origen
        credentials_destino: credentials.json de cuenta destino
    """

    print("=" * 80)
    print("TRANSFERENCIA DE ACTAS ENTRE CUENTAS DE GOOGLE DRIVE")
    print("=" * 80)

    # Autenticar ambas cuentas
    print("\n1. Autenticando cuenta ORIGEN...")
    service_origen = autenticar_drive(credentials_origen, "token_origen.json")
    print("   ✓ Autenticado en cuenta origen")

    print("\n2. Autenticando cuenta DESTINO (anónima)...")
    service_destino = autenticar_drive(credentials_destino, "token_destino.json")
    print("   ✓ Autenticado en cuenta destino")

    # Leer JSON
    print(f"\n3. Leyendo archivo JSON: {json_origen}")
    with open(json_origen, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    print(f"   Total de registros: {len(datos)}")

    # Contar actas con url_drive
    actas_con_url = [r for r in datos if r.get('url_drive')]
    print(f"   Actas con url_drive: {len(actas_con_url)}")

    # Crear carpetas por departamento
    print("\n4. Creando estructura de carpetas en cuenta destino...")
    carpetas_departamentos = {}
    departamentos_unicos = set(r['departamento'] for r in datos if r.get('url_drive'))

    for departamento in sorted(departamentos_unicos):
        # Verificar si ya existe la carpeta
        folder_id = obtener_carpeta_por_nombre(service_destino, departamento)

        if not folder_id:
            folder_id = crear_carpeta(service_destino, departamento, PARENT_FOLDER_ID_DESTINO)
            print(f"   ✓ Carpeta creada: {departamento}")
        else:
            print(f"   ✓ Carpeta existente: {departamento}")

        carpetas_departamentos[departamento] = folder_id

    # Transferir archivos
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
            # Descargar desde cuenta origen
            print(f"  → Descargando...")
            if descargar_archivo_desde_url_drive(url_original, archivo_temp):
                # Subir a cuenta destino
                print(f"  → Subiendo a cuenta destino...")
                folder_id = carpetas_departamentos[departamento]
                archivo_subido = subir_archivo_a_drive(
                    service_destino,
                    archivo_temp,
                    nombre_archivo,
                    folder_id
                )

                # Hacer público
                url_nueva = hacer_archivo_publico(service_destino, archivo_subido['id'])

                # Actualizar URL en el registro
                registro['url_drive'] = url_nueva

                # Borrar archivo temporal
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

        # Delay para evitar rate limiting
        time.sleep(0.5)

        # Mostrar progreso cada 100 archivos
        if i % 100 == 0:
            print("\n" + "=" * 80)
            print(f"PROGRESO: {i}/{total} ({i/total*100:.1f}%)")
            print(f"Exitosos: {exitosos} | Fallidos: {fallidos}")
            print("=" * 80)

    # Guardar JSON actualizado
    print(f"\n6. Guardando JSON actualizado: {json_destino}")
    with open(json_destino, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    # Guardar log de errores
    if errores:
        with open('errores_transferencia.json', 'w', encoding='utf-8') as f:
            json.dump(errores, f, ensure_ascii=False, indent=2)

    # Resumen final
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
    # CONFIGURACIÓN
    # ============================================

    # Archivos de entrada/salida
    json_origen = "resultados_validados_gemini.json"  # JSON con URLs originales
    json_destino = "resultados_validados_gemini_ANONIMO.json"  # JSON con URLs nuevas

    # Archivos de credenciales
    credentials_origen = "credentials_original.json"  # Tu cuenta personal
    credentials_destino = "credentials_anonima.json"  # Cuenta anónima nueva

    # ============================================

    # INSTRUCCIONES:
    # 1. Descargar credentials.json de tu cuenta PERSONAL y renombrarlo a credentials_original.json
    # 2. Crear cuenta Google ANÓNIMA (vía Tor, WiFi público)
    # 3. Descargar credentials.json de cuenta anónima y renombrarlo a credentials_anonima.json
    # 4. Ejecutar este script

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
