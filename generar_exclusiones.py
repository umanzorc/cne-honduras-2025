#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar archivo de exclusiones de JRVs ya procesadas
Lee el JSON con URLs de Drive y genera un Set de JRVs a excluir en el navegador
"""

import json
import os

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

JSON_INPUT = 'resultados_jrv_detallado_con_urls.json'
OUTPUT_JS = 'jrvs_a_excluir.js'

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    print("="*80)
    print("GENERADOR DE EXCLUSIONES DE JRVs")
    print("="*80)

    # Verificar que existe el archivo
    if not os.path.exists(JSON_INPUT):
        print(f"❌ Error: No se encontró {JSON_INPUT}")
        print(f"💡 Tip: Primero ejecuta agregar_urls_drive_rapido.py")
        return

    # Cargar JSON
    print(f"\n📄 Cargando: {JSON_INPUT}")
    try:
        with open(JSON_INPUT, 'r', encoding='utf-8') as f:
            actas = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ Error: {JSON_INPUT} no es un JSON válido")
        return

    print(f"✅ {len(actas)} actas cargadas")

    # Filtrar JRVs que YA TIENEN url_drive
    jrvs_con_url = set()
    jrvs_sin_url = []

    for acta in actas:
        numero_jrv = acta.get('numero_jrv')
        url_drive = acta.get('url_drive')

        if url_drive and numero_jrv:
            jrvs_con_url.add(str(numero_jrv))
        elif numero_jrv:
            jrvs_sin_url.append({
                'numero_jrv': numero_jrv,
                'departamento': acta.get('departamento'),
                'municipio': acta.get('municipio')
            })

    # Estadísticas
    total = len(actas)
    con_url = len(jrvs_con_url)
    sin_url = len(jrvs_sin_url)
    porcentaje_completo = (con_url / total * 100) if total > 0 else 0

    print(f"\n📊 ESTADÍSTICAS")
    print(f"{'='*80}")
    print(f"Total actas:           {total:,}")
    print(f"✅ Con URL Drive:      {con_url:,} ({porcentaje_completo:.1f}%)")
    print(f"⚠️  Sin URL Drive:      {sin_url:,} ({100-porcentaje_completo:.1f}%)")

    # Generar archivo JavaScript
    print(f"\n💾 Generando: {OUTPUT_JS}")

    try:
        with open(OUTPUT_JS, 'w', encoding='utf-8') as f:
            f.write("// Archivo auto-generado por generar_exclusiones.py\n")
            f.write("// JRVs que YA TIENEN url_drive y deben ser EXCLUIDAS del procesamiento\n")
            f.write(f"// Total JRVs a excluir: {con_url:,} ({porcentaje_completo:.1f}%)\n")
            f.write(f"// Generado: {import_datetime()}\n\n")

            f.write("const JRVS_A_EXCLUIR = new Set([\n")

            # Escribir JRVs en bloques de 20 por línea (más compacto)
            jrvs_lista = sorted(list(jrvs_con_url), key=lambda x: int(x))

            for i in range(0, len(jrvs_lista), 20):
                bloque = jrvs_lista[i:i+20]
                f.write("    " + ", ".join(f'"{jrv}"' for jrv in bloque))
                if i + 20 < len(jrvs_lista):
                    f.write(",\n")
                else:
                    f.write("\n")

            f.write("]);\n\n")

            f.write("// Función helper para verificar si una JRV debe procesarse\n")
            f.write("function debeExcluirJRV(numeroJRV) {\n")
            f.write("    return JRVS_A_EXCLUIR.has(String(numeroJRV));\n")
            f.write("}\n\n")

            f.write("console.log(`📋 Cargadas ${JRVS_A_EXCLUIR.size:,} JRVs a excluir`);\n")

        print(f"✅ Archivo generado exitosamente")

    except Exception as e:
        print(f"❌ Error generando archivo: {e}")
        return

    # Generar también un log legible de JRVs faltantes
    if jrvs_sin_url:
        log_faltantes = 'jrvs_faltantes.txt'
        print(f"\n📝 Generando log de faltantes: {log_faltantes}")

        try:
            with open(log_faltantes, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write(f"JRVs SIN URL DE DRIVE ({len(jrvs_sin_url)} actas)\n")
                f.write("="*80 + "\n\n")

                # Agrupar por departamento
                por_depto = {}
                for jrv in jrvs_sin_url:
                    depto = jrv['departamento']
                    if depto not in por_depto:
                        por_depto[depto] = []
                    por_depto[depto].append(jrv)

                for depto in sorted(por_depto.keys()):
                    f.write(f"\n{depto} ({len(por_depto[depto])} JRVs)\n")
                    f.write("-" * 80 + "\n")
                    for jrv in sorted(por_depto[depto], key=lambda x: x['numero_jrv']):
                        f.write(f"  JRV {jrv['numero_jrv']:5} - {jrv['municipio']}\n")

            print(f"✅ Log de faltantes generado")

        except Exception as e:
            print(f"⚠️  Error generando log: {e}")

    # Resumen final
    print(f"\n{'='*80}")
    print("✅ PROCESO COMPLETADO")
    print(f"{'='*80}")
    print(f"\n📁 Archivos generados:")
    print(f"   - {OUTPUT_JS} (para usar en el navegador)")
    if jrvs_sin_url:
        print(f"   - {log_faltantes} (log de JRVs faltantes)")
    print(f"\n💡 SIGUIENTE PASO:")
    print(f"   1. En el navegador, ejecuta primero: copy(await fetch('./{OUTPUT_JS}').then(r => r.text()))")
    print(f"   2. O copia manualmente el contenido de {OUTPUT_JS}")
    print(f"   3. Luego ejecuta el script_navegador_detallado_completo.js")
    print(f"\n⚡ El script del navegador procesará solo {sin_url:,} JRVs faltantes")
    print("="*80)

def import_datetime():
    """Helper para importar datetime sin poner el import arriba"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
