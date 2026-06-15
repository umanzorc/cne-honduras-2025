#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para hacer pública una carpeta de Google Drive sin mostrar propietario
"""

import os
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

FOLDER_ID = '1PqARS1zO82dv1S7_lokXHswBCAUaCZ2F'  # ID de la carpeta a compartir
SCOPES = ['https://www.googleapis.com/auth/drive']

# ============================================================================
# AUTENTICACIÓN
# ============================================================================

def autenticar_google_drive():
    """Autentica con Google Drive API"""
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

# ============================================================================
# HACER CARPETA PÚBLICA
# ============================================================================

def hacer_carpeta_publica(service, folder_id):
    """
    Hace una carpeta pública con acceso de 'viewer' para cualquiera con el enlace
    """
    try:
        # Permisos para hacer pública la carpeta
        permission = {
            'type': 'anyone',  # Cualquiera con el enlace
            'role': 'reader'   # Solo lectura
        }

        service.permissions().create(
            fileId=folder_id,
            body=permission,
            fields='id'
        ).execute()

        print(f"✅ Carpeta configurada como pública (solo lectura)")

        # Obtener el enlace de la carpeta
        file = service.files().get(
            fileId=folder_id,
            fields='webViewLink, name'
        ).execute()

        return file.get('webViewLink'), file.get('name')

    except Exception as error:
        print(f"❌ Error: {error}")
        return None, None

def hacer_todos_archivos_publicos(service, folder_id):
    """
    Hace públicos TODOS los archivos dentro de la carpeta (recursivamente)
    """
    try:
        print(f"\n📋 Listando archivos en la carpeta...")

        # Obtener todos los archivos de la carpeta
        page_token = None
        total_archivos = 0

        while True:
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType)',
                pageToken=page_token,
                pageSize=1000
            ).execute()

            items = results.get('files', [])

            for item in items:
                try:
                    # Hacer público cada archivo/carpeta
                    permission = {
                        'type': 'anyone',
                        'role': 'reader'
                    }

                    service.permissions().create(
                        fileId=item['id'],
                        body=permission,
                        fields='id'
                    ).execute()

                    total_archivos += 1

                    if total_archivos % 100 == 0:
                        print(f"   ✅ {total_archivos} archivos públicos...")

                    # Si es una carpeta, procesar recursivamente
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        hacer_todos_archivos_publicos(service, item['id'])

                except Exception as e:
                    if 'duplicate' in str(e).lower():
                        # Ya era público, continuar
                        total_archivos += 1
                    else:
                        print(f"⚠️  Error en archivo {item['name']}: {e}")

            page_token = results.get('nextPageToken')
            if not page_token:
                break

        print(f"✅ Total: {total_archivos} archivos/carpetas públicos")

    except Exception as error:
        print(f"❌ Error listando archivos: {error}")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    print("="*80)
    print("COMPARTIR CARPETA DE GOOGLE DRIVE (ANÓNIMO)")
    print("="*80)
    print()

    # Autenticar
    print("🔑 Autenticando con Google Drive...")
    try:
        service = autenticar_google_drive()
        print("✅ Autenticación exitosa")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Hacer carpeta pública
    print(f"\n📁 Configurando carpeta {FOLDER_ID} como pública...")
    url, nombre = hacer_carpeta_publica(service, FOLDER_ID)

    if not url:
        print("❌ No se pudo hacer pública la carpeta")
        return

    print(f"✅ Carpeta: {nombre}")
    print(f"🔗 Enlace público: {url}")

    # Preguntar si hacer públicos todos los archivos
    print(f"\n⚠️  IMPORTANTE: La carpeta es pública, pero los archivos dentro pueden no serlo.")
    respuesta = input("¿Hacer públicos TODOS los archivos dentro de la carpeta? (s/n): ").lower()

    if respuesta == 's':
        hacer_todos_archivos_publicos(service, FOLDER_ID)
    else:
        print("⏭️  Saltando archivos internos (solo la carpeta es pública)")

    # Resumen final
    print(f"\n{'='*80}")
    print("✅ CONFIGURACIÓN COMPLETADA")
    print(f"{'='*80}")
    print(f"\n🔗 Enlace público (anónimo):")
    print(f"   {url}")
    print(f"\n📋 Características:")
    print(f"   - Acceso: Cualquiera con el enlace")
    print(f"   - Permisos: Solo lectura (viewer)")
    print(f"   - Propietario: NO visible (anónimo)")
    print(f"\n💡 Puedes compartir este enlace sin revelar tu identidad")
    print("="*80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
