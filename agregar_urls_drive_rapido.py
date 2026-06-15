#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script RÁPIDO para agregar URLs de Google Drive al JSON
Versión con procesamiento asíncrono en lotes para 19,000 actas
"""

import json
import os
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

JSON_INPUT = 'resultados_jrv_detallado.json'
JSON_OUTPUT = 'resultados_jrv_detallado_con_urls.json'
JSON_REFERENCIA = 'resultados_jrvs_faltantes.json'  # JSON con datos actualizados (votos_nulos, votos_blanco)
LOG_FALTANTES = 'actas_sin_url_drive.json'
LOG_TEXTO = 'actas_sin_url_drive.log'
PARENT_FOLDER_ID = '1PqARS1zO82dv1S7_lokXHswBCAUaCZ2F'
SCOPES = ['https://www.googleapis.com/auth/drive.file']
HACER_PUBLICOS = True
ACTUALIZAR_VOTOS = True  # Si True, actualiza votos_nulos y votos_blanco desde JSON_REFERENCIA

# Configuración de concurrencia
CONCURRENCIA_ARCHIVOS = 50  # Procesar 50 archivos en paraleloe
MAX_WORKERS = 10  # Threads para Google Drive API

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
# FUNCIONES DE GOOGLE DRIVE
# ============================================================================

def buscar_carpeta(service, nombre_carpeta, parent_id=None):
    """Busca carpeta por nombre"""
    try:
        query = f"name='{nombre_carpeta}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        return items[0]['id'] if items else None
    except HttpError as error:
        print(f"Error buscando carpeta '{nombre_carpeta}': {error}")
        return None

def listar_archivos_carpeta(service, folder_id):
    """
    Lista TODOS los archivos de una carpeta de una vez
    Retorna dict: {nombre_archivo: {id, webViewLink}}
    """
    try:
        archivos = {}
        page_token = None

        while True:
            query = f"'{folder_id}' in parents and trashed=false"
            results = service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, webViewLink)',
                pageSize=1000,
                pageToken=page_token
            ).execute()

            items = results.get('files', [])
            for item in items:
                archivos[item['name']] = {
                    'id': item['id'],
                    'webViewLink': item.get('webViewLink', '')
                }

            page_token = results.get('nextPageToken')
            if not page_token:
                break

        return archivos

    except HttpError as error:
        print(f"Error listando archivos: {error}")
        return {}

def hacer_publico(service, file_id):
    """Hace archivo público"""
    try:
        permission = {'type': 'anyone', 'role': 'reader'}
        service.permissions().create(fileId=file_id, body=permission).execute()
        return True
    except HttpError as error:
        if 'duplicate' in str(error).lower():
            return True
        return False

# ============================================================================
# PROCESAMIENTO ASÍNCRONO
# ============================================================================

async def procesar_acta(service, acta, archivos_drive, hacer_publico_flag):
    """Procesa una acta individual"""
    numero_jrv = acta.get('numero_jrv', 'DESCONOCIDO')
    nombre_archivo = f"JRV_{numero_jrv}.pdf"

    # Buscar en el dict de archivos (ya precargado)
    if nombre_archivo not in archivos_drive:
        return None, 'archivo_no_encontrado'

    archivo_info = archivos_drive[nombre_archivo]
    file_id = archivo_info['id']
    url_drive = archivo_info['webViewLink']

    # Hacer público si está configurado
    if hacer_publico_flag and not url_drive:
        # Ejecutar en thread pool (Google API no es async)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, hacer_publico, service, file_id)

        # Obtener URL después de hacer público
        try:
            file = service.files().get(fileId=file_id, fields='webViewLink').execute()
            url_drive = file.get('webViewLink', '')
        except Exception as e:
            return None, f'error_obtener_url: {str(e)}'

    if not url_drive:
        return None, 'url_vacia'

    return url_drive, 'ok'

async def procesar_departamento(service, departamento, actas_dept, actas_faltantes):
    """Procesa todas las actas de un departamento en paralelo"""
    print(f"\n{'='*80}")
    print(f"📍 DEPARTAMENTO: {departamento} ({len(actas_dept)} actas)")
    print(f"{'='*80}")

    # Buscar carpeta del departamento
    folder_id = buscar_carpeta(service, departamento, PARENT_FOLDER_ID)

    if not folder_id:
        print(f"⚠️  Carpeta no encontrada: {departamento}")
        # Agregar todas las actas al log de faltantes
        for acta in actas_dept:
            actas_faltantes.append({
                'numero_jrv': acta.get('numero_jrv'),
                'departamento': acta.get('departamento'),
                'municipio': acta.get('municipio'),
                'razon': 'carpeta_departamento_no_encontrada'
            })
        return 0, len(actas_dept)

    print(f"📁 Carpeta encontrada: {departamento}")

    # CLAVE: Listar TODOS los archivos de la carpeta DE UNA VEZ
    print(f"📋 Listando archivos en Drive...")
    archivos_drive = listar_archivos_carpeta(service, folder_id)
    print(f"✅ {len(archivos_drive)} archivos encontrados en Drive")

    # Procesar actas en lotes
    urls_agregadas = 0
    no_encontrados = 0

    for i in range(0, len(actas_dept), CONCURRENCIA_ARCHIVOS):
        lote = actas_dept[i:i + CONCURRENCIA_ARCHIVOS]

        # Procesar lote en paralelo
        tareas = [
            procesar_acta(service, acta, archivos_drive, HACER_PUBLICOS)
            for acta in lote
        ]

        resultados = await asyncio.gather(*tareas)

        # Agregar URLs al JSON y registrar faltantes
        for acta, (url_drive, estado) in zip(lote, resultados):
            if url_drive:
                acta['url_drive'] = url_drive
                # Eliminar URL del CNE (expira en 2h, ya no la necesitamos)
                if 'url_acta_pdf' in acta:
                    del acta['url_acta_pdf']
                urls_agregadas += 1
            else:
                no_encontrados += 1
                # Agregar al log de faltantes
                actas_faltantes.append({
                    'numero_jrv': acta.get('numero_jrv'),
                    'departamento': acta.get('departamento'),
                    'municipio': acta.get('municipio'),
                    'zona': acta.get('zona'),
                    'puesto': acta.get('puesto'),
                    'razon': estado,
                    'nombre_archivo_esperado': f"JRV_{acta.get('numero_jrv')}.pdf"
                })

        # Progreso
        procesadas = min(i + CONCURRENCIA_ARCHIVOS, len(actas_dept))
        print(f"   [{procesadas}/{len(actas_dept)}] URLs agregadas: {urls_agregadas}, No encontrados: {no_encontrados}")

    return urls_agregadas, no_encontrados

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

async def main_async(actas, service):
    """Función principal asíncrona"""
    # Agrupar actas por departamento
    actas_por_departamento = {}
    for acta in actas:
        dept = acta.get('departamento', 'DESCONOCIDO')
        if dept not in actas_por_departamento:
            actas_por_departamento[dept] = []
        actas_por_departamento[dept].append(acta)

    print(f"\n📊 Actas agrupadas en {len(actas_por_departamento)} departamentos")

    # Estadísticas
    total_urls = 0
    total_no_encontrados = 0
    actas_faltantes = []  # Lista para registrar actas sin URL

    # Procesar departamentos secuencialmente (pero actas en paralelo)
    for departamento, actas_dept in actas_por_departamento.items():
        urls, no_encontrados = await procesar_departamento(service, departamento, actas_dept, actas_faltantes)
        total_urls += urls
        total_no_encontrados += no_encontrados

    return total_urls, total_no_encontrados, actas_faltantes

def main():
    """Función principal"""
    print("=" * 80)
    print("AGREGAR URLs DE GOOGLE DRIVE - VERSIÓN RÁPIDA")
    print("=" * 80)
    print(f"⚡ Configuración: {CONCURRENCIA_ARCHIVOS} archivos en paralelo")
    print()

    # Cargar JSON
    print(f"📄 Cargando JSON: {JSON_INPUT}")
    try:
        with open(JSON_INPUT, 'r', encoding='utf-8') as f:
            actas = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: No se encontró {JSON_INPUT}")
        return
    except json.JSONDecodeError:
        print(f"❌ Error: {JSON_INPUT} no es un JSON válido")
        return

    print(f"✅ {len(actas)} actas cargadas")

    # Cargar JSON de referencia para actualizar votos si está habilitado
    datos_referencia = {}
    if ACTUALIZAR_VOTOS:
        print(f"\n📄 Cargando JSON de referencia: {JSON_REFERENCIA}")
        try:
            with open(JSON_REFERENCIA, 'r', encoding='utf-8') as f:
                actas_referencia = json.load(f)

            # Crear diccionario para búsqueda rápida por numero_jrv
            datos_referencia = {
                acta['numero_jrv']: {
                    'votos_nulos': acta.get('votos_nulos', 0),
                    'votos_blanco': acta.get('votos_blanco', 0)
                }
                for acta in actas_referencia if 'numero_jrv' in acta
            }
            print(f"✅ {len(datos_referencia)} actas de referencia cargadas")

            # Actualizar votos_nulos y votos_blanco
            print(f"\n🔄 Actualizando votos_nulos y votos_blanco...")
            actualizados = 0
            for acta in actas:
                numero_jrv = acta.get('numero_jrv')
                if numero_jrv in datos_referencia:
                    acta['votos_nulos'] = datos_referencia[numero_jrv]['votos_nulos']
                    acta['votos_blanco'] = datos_referencia[numero_jrv]['votos_blanco']
                    actualizados += 1

            print(f"✅ {actualizados} actas actualizadas con votos_nulos y votos_blanco")

        except FileNotFoundError:
            print(f"⚠️  Advertencia: No se encontró {JSON_REFERENCIA}")
            print(f"   Se continuará sin actualizar votos_nulos y votos_blanco")
        except json.JSONDecodeError:
            print(f"⚠️  Advertencia: {JSON_REFERENCIA} no es un JSON válido")
            print(f"   Se continuará sin actualizar votos_nulos y votos_blanco")
        except Exception as e:
            print(f"⚠️  Advertencia: Error leyendo {JSON_REFERENCIA}: {e}")
            print(f"   Se continuará sin actualizar votos_nulos y votos_blanco")

    # Autenticar
    print(f"\n🔑 Autenticando con Google Drive...")
    try:
        service = autenticar_google_drive()
        print("✅ Autenticación exitosa")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Procesar de forma asíncrona
    tiempo_inicio = time.time()

    # Ejecutar función asíncrona
    total_urls, total_no_encontrados, actas_faltantes = asyncio.run(main_async(actas, service))

    tiempo_total = time.time() - tiempo_inicio

    # Guardar JSON
    print(f"\n{'='*80}")
    print("💾 GUARDANDO JSON ACTUALIZADO")
    print(f"{'='*80}")

    try:
        with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(actas, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON guardado: {JSON_OUTPUT}")
    except Exception as e:
        print(f"❌ Error guardando JSON: {e}")
        return

    # Guardar logs de actas faltantes
    if actas_faltantes:
        print(f"\n{'='*80}")
        print("📝 GUARDANDO LOGS DE ACTAS FALTANTES")
        print(f"{'='*80}")

        # Guardar como JSON
        try:
            with open(LOG_FALTANTES, 'w', encoding='utf-8') as f:
                json.dump(actas_faltantes, f, ensure_ascii=False, indent=2)
            print(f"✅ Log JSON guardado: {LOG_FALTANTES}")
        except Exception as e:
            print(f"❌ Error guardando log JSON: {e}")

        # Guardar como texto legible
        try:
            with open(LOG_TEXTO, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("ACTAS SIN URL DE GOOGLE DRIVE - REPORTE DETALLADO\n")
                f.write("="*80 + "\n\n")

                f.write(f"Total actas sin URL: {len(actas_faltantes)}\n")
                f.write(f"Total actas procesadas: {len(actas)}\n")
                f.write(f"Porcentaje faltante: {len(actas_faltantes)/len(actas)*100:.2f}%\n\n")

                # Agrupar por razón
                razones = {}
                for acta in actas_faltantes:
                    razon = acta.get('razon', 'desconocido')
                    if razon not in razones:
                        razones[razon] = []
                    razones[razon].append(acta)

                f.write("="*80 + "\n")
                f.write("RESUMEN POR TIPO DE ERROR\n")
                f.write("="*80 + "\n\n")

                for razon, actas_razon in sorted(razones.items(), key=lambda x: len(x[1]), reverse=True):
                    f.write(f"{razon}: {len(actas_razon)} actas\n")

                f.write("\n" + "="*80 + "\n")
                f.write("DETALLE DE ACTAS FALTANTES\n")
                f.write("="*80 + "\n\n")

                for razon, actas_razon in sorted(razones.items()):
                    f.write(f"\n--- {razon.upper()} ({len(actas_razon)} actas) ---\n\n")
                    for acta in actas_razon:
                        f.write(f"  JRV: {acta.get('numero_jrv', 'N/A')}\n")
                        f.write(f"  Departamento: {acta.get('departamento', 'N/A')}\n")
                        f.write(f"  Municipio: {acta.get('municipio', 'N/A')}\n")
                        if acta.get('zona'):
                            f.write(f"  Zona: {acta.get('zona')}\n")
                        if acta.get('puesto'):
                            f.write(f"  Puesto: {acta.get('puesto')}\n")
                        f.write(f"  Archivo esperado: {acta.get('nombre_archivo_esperado', 'N/A')}\n")
                        f.write("\n")

            print(f"✅ Log de texto guardado: {LOG_TEXTO}")
        except Exception as e:
            print(f"❌ Error guardando log de texto: {e}")

    # Resumen final
    print(f"\n{'='*80}")
    print("✅ PROCESO COMPLETADO")
    print(f"{'='*80}")
    print(f"📊 Total actas: {len(actas)}")
    if ACTUALIZAR_VOTOS and datos_referencia:
        print(f"🔄 Votos actualizados: {len([a for a in actas if a.get('numero_jrv') in datos_referencia])}")
    print(f"✅ URLs agregadas: {total_urls}")
    print(f"⚠️  Archivos no encontrados: {total_no_encontrados}")
    print(f"⏱️  Tiempo total: {tiempo_total/60:.1f} minutos")
    print(f"⚡ Velocidad: {len(actas)/tiempo_total:.1f} actas/seg")
    print()
    print(f"📁 Archivo generado: {JSON_OUTPUT}")
    if ACTUALIZAR_VOTOS:
        print(f"   ✅ Con votos_nulos y votos_blanco actualizados")
    if actas_faltantes:
        print(f"📝 Logs de faltantes: {LOG_FALTANTES}, {LOG_TEXTO}")
    print(f"{'='*80}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
