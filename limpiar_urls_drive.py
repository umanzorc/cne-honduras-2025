#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para limpiar URLs de Google Drive
Elimina parámetros comprometedores (ouid, rtpof, sd) de las URLs

IMPORTANTE: Este script solo limpia las URLs, NO transfiere archivos a otra cuenta.
Las URLs seguirán apuntando a tu cuenta personal, pero sin el ID de usuario visible.
"""

import json
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def limpiar_url_drive(url):
    """
    Limpia una URL de Google Drive eliminando parámetros comprometedores

    Args:
        url: URL original de Google Drive

    Returns:
        URL limpia sin parámetros de rastreo
    """
    if not url or 'drive.google.com' not in url:
        return url

    try:
        # Parsear URL
        parsed = urlparse(url)

        # Construir nueva URL limpia
        # Solo mantener el parámetro usp=sharing
        if 'spreadsheets' in url:
            # Para Google Sheets
            nueva_url = url.split('?')[0] + '?usp=sharing'
        else:
            # Para archivos normales (PDFs)
            nueva_url = url.split('?')[0] + '?usp=sharing'

        return nueva_url

    except Exception as e:
        print(f"  ⚠️ Error al limpiar URL: {e}")
        return url


def limpiar_urls_en_json(archivo_entrada, archivo_salida):
    """
    Limpia todas las URLs de Drive en un archivo JSON

    Args:
        archivo_entrada: Archivo JSON original
        archivo_salida: Archivo JSON con URLs limpias
    """

    print("=" * 80)
    print("LIMPIEZA DE URLs DE GOOGLE DRIVE")
    print("=" * 80)

    # Leer JSON
    print(f"\nLeyendo archivo: {archivo_entrada}")
    with open(archivo_entrada, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    print(f"Total de registros: {len(datos)}")

    # Limpiar URLs
    urls_limpias = 0
    urls_sin_cambios = 0

    for registro in datos:
        if 'url_drive' in registro and registro['url_drive']:
            url_original = registro['url_drive']
            url_limpia = limpiar_url_drive(url_original)

            if url_original != url_limpia:
                registro['url_drive'] = url_limpia
                urls_limpias += 1
            else:
                urls_sin_cambios += 1

    # Guardar JSON actualizado
    print(f"\nGuardando JSON limpio: {archivo_salida}")
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"URLs limpiadas: {urls_limpias}")
    print(f"URLs sin cambios: {urls_sin_cambios}")
    print(f"\nArchivo generado: {archivo_salida}")
    print("\n✓ Proceso completado!")

    # Mostrar ejemplos
    if urls_limpias > 0:
        print("\n" + "=" * 80)
        print("EJEMPLOS DE URLS LIMPIADAS")
        print("=" * 80)

        count = 0
        for registro in datos:
            if count >= 3:  # Mostrar solo 3 ejemplos
                break

            if 'url_drive' in registro and registro['url_drive']:
                print(f"\nJRV {registro.get('numero_jrv')}:")
                print(f"  URL limpia: {registro['url_drive']}")
                count += 1

    # Advertencia
    print("\n" + "⚠️" * 40)
    print("ADVERTENCIA IMPORTANTE:")
    print("=" * 80)
    print("""
Este script SOLO limpia las URLs eliminando parámetros comprometedores.

Las URLs seguirán apuntando a TU CUENTA PERSONAL de Google Drive.

Cuando alguien haga clic en el enlace, Google puede mostrar:
- "Compartido por [Tu Nombre]"
- Tu email
- Tu foto de perfil

Para MÁXIMA SEGURIDAD, usa el script 'transferir_drive_a_drive.py'
que transfiere los archivos a una cuenta anónima.

Alternativamente:
1. Cambia el nombre de tu cuenta de Google temporalmente
2. O haz que los archivos sean públicos sin mostrar propietario
    """)
    print("=" * 80)


if __name__ == "__main__":
    # CONFIGURACIÓN
    archivo_entrada = "resultados_validados_gemini.json"
    archivo_salida = "resultados_validados_gemini_URLS_LIMPIAS.json"

    try:
        limpiar_urls_en_json(archivo_entrada, archivo_salida)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
