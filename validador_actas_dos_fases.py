#!/usr/bin/env python3
"""
Validador de Actas en DOS FASES - Máxima Precisión y Costo Optimizado
FASE 1: Claude Sonnet 4 valida TODAS las actas (~$60 para 20k actas)
FASE 2: Claude Opus 4.5 RE-VALIDA solo las inconsistentes (~$3-5)
"""

import json
import requests
import base64
import time
from pathlib import Path
from anthropic import Anthropic
from typing import Dict, List
import sys

# Configuración
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")  # export ANTHROPIC_API_KEY='sk-ant-...'
DELAY_ENTRE_PETICIONES = 2

# Modelos
MODELO_FASE1 = "claude-sonnet-4-20250514"  # Rápido y económico
MODELO_FASE2 = "claude-opus-4-5-20251101"  # Máxima precisión

def cargar_json(ruta_json: str) -> List[Dict]:
    """Carga el JSON con los datos del CNE"""
    print(f"📂 Cargando datos desde: {ruta_json}")
    with open(ruta_json, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    if isinstance(datos, dict):
        print("ℹ️  Detectado un solo registro, convirtiéndolo a lista")
        datos = [datos]

    print(f"✅ Cargados {len(datos)} registros\n")
    return datos

def descargar_pdf(url: str) -> bytes:
    """Descarga el PDF desde la URL de S3"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"❌ Error descargando PDF: {e}")
        return None

def extraer_votos_con_claude(pdf_content: bytes, client: Anthropic, modelo: str, fase: str = "") -> Dict:
    """
    Envía el PDF a Claude y extrae los votos de cada partido
    """
    pdf_base64 = base64.standard_b64encode(pdf_content).decode('utf-8')

    prompt = """Analiza esta acta electoral de Honduras y extrae EXACTAMENTE los votos de cada partido.

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

PARTIDOS A EXTRAER:
- DC (Partido Demócrata Cristiano) - Casilla verde
- LIBRE (Libertad y Refundación) - Casilla roja
- PINU (Innovación y Unidad) - Casilla naranja
- Liberal - Casilla roja con blanco
- Nacional - Casilla azul con estrella
- VOTOS EN BLANCO
- VOTOS NULOS
- GRAN TOTAL (última fila)

TAMBIÉN EXTRAE:
- TOTAL VOTANTES (de la sección I. BALANCE GENERAL, última fila)
- JRV (número en el encabezado "JRV N° XXXXX")

CAMPOS ADICIONALES A EXTRAER:
- PAPELETAS (de la sección I. BALANCE GENERAL):
  * RECIBIDAS SEGÚN ACTA DE APERTURA (primera fila)
  * NO UTILIZADAS / SOBRANTES (segunda fila)
  * UTILIZADAS (tercera fila)
- QR: Código QR en la esquina superior derecha (si es legible)
- CÓDIGO DE BARRAS: Código de barras en la parte inferior derecha (si es legible)

VALIDACIÓN CRUZADA CRÍTICA:
- Para cada partido y totales, compara la columna "EN NÚMEROS" vs "EN LETRAS"
- Si ambas columnas coinciden, usa ese valor con alta confianza
- Si NO coinciden, prioriza "EN LETRAS" pero marca como dudoso poniendo null
- Esto ayuda a evitar errores cuando la escritura es difusa o poco clara

Si algún dato está ilegible o no lo encuentras, pon null.

Responde ÚNICAMENTE con un JSON en este formato exacto (sin markdown, sin explicaciones):
{
  "votos_dc": 0,
  "votos_libre": 0,
  "votos_pinu": 0,
  "votos_liberal": 0,
  "votos_nacional": 0,
  "votos_blanco": 0,
  "votos_nulos": 0,
  "gran_total": 0,
  "total_votantes": 0,
  "jrv": 0,
  "papeletas_recibidas": 0,
  "papeletas_no_utilizadas": 0,
  "papeletas_utilizadas": 0,
  "numero_acta_qr": "texto_del_qr",
  "numero_acta_barra": "texto_codigo_barras"
}"""

    try:
        marca_modelo = "🔵 Sonnet 4" if "sonnet" in modelo else "💎 Opus 4.5"
        print(f"   {marca_modelo} {fase}")

        message = client.messages.create(
            model=modelo,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        respuesta = message.content[0].text.strip()

        # Limpiar markdown si viene
        if respuesta.startswith('```'):
            respuesta = respuesta.split('```')[1]
            if respuesta.startswith('json'):
                respuesta = respuesta[4:]
            respuesta = respuesta.strip()

        votos = json.loads(respuesta)
        return votos

    except Exception as e:
        print(f"❌ Error al procesar con Claude: {e}")
        return None

def procesar_acta(acta: Dict, client: Anthropic, modelo: str, fase: str = "") -> Dict:
    """Procesa una acta individual"""

    resultado = acta.copy()
    numero_jrv = acta.get('numero_jrv', 'N/A')
    url_pdf = acta.get('url_acta_pdf', '')

    # Inicializar campos
    resultado['pdf_votos_dc'] = None
    resultado['pdf_votos_libre'] = None
    resultado['pdf_votos_pinu'] = None
    resultado['pdf_votos_liberal'] = None
    resultado['pdf_votos_nacional'] = None
    resultado['pdf_votos_blanco'] = None
    resultado['pdf_votos_nulos'] = None
    resultado['pdf_gran_total'] = None
    resultado['pdf_total_votantes'] = None
    resultado['pdf_jrv'] = None
    resultado['pdf_papeletas_recibidas'] = None
    resultado['pdf_papeletas_no_utilizadas'] = None
    resultado['pdf_papeletas_utilizadas'] = None
    resultado['pdf_numero_acta_qr'] = None
    resultado['pdf_numero_acta_barra'] = None
    resultado['codigo_jrv'] = numero_jrv
    resultado['SumatoriaManualPorPartido'] = None
    resultado['InconsistenciaDatosDigitados'] = 0
    resultado['InconsistenciaGrandTotalPorVotantes'] = 0
    resultado['InconsistenciaJrv'] = 0
    resultado['InconsistenciaPapeletas'] = 0
    resultado['NumeroActaInconsistente'] = 0

    if not url_pdf:
        print("⚠️  Sin URL de PDF")
        return resultado

    # Descargar PDF
    print("📥 Descargando PDF...")
    pdf_content = descargar_pdf(url_pdf)

    if not pdf_content:
        print("❌ Error descargando PDF")
        return resultado

    # Extraer votos con Claude
    print("🤖 Analizando PDF con Claude AI...")
    votos_extraidos = extraer_votos_con_claude(pdf_content, client, modelo, fase)

    if not votos_extraidos:
        print("❌ Error al extraer votos con IA")
        return resultado

    # Guardar datos extraídos
    resultado['pdf_votos_dc'] = votos_extraidos.get('votos_dc')
    resultado['pdf_votos_libre'] = votos_extraidos.get('votos_libre')
    resultado['pdf_votos_pinu'] = votos_extraidos.get('votos_pinu')
    resultado['pdf_votos_liberal'] = votos_extraidos.get('votos_liberal')
    resultado['pdf_votos_nacional'] = votos_extraidos.get('votos_nacional')
    resultado['pdf_votos_blanco'] = votos_extraidos.get('votos_blanco')
    resultado['pdf_votos_nulos'] = votos_extraidos.get('votos_nulos')
    resultado['pdf_gran_total'] = votos_extraidos.get('gran_total')
    resultado['pdf_total_votantes'] = votos_extraidos.get('total_votantes')
    resultado['pdf_jrv'] = votos_extraidos.get('jrv')
    resultado['pdf_papeletas_recibidas'] = votos_extraidos.get('papeletas_recibidas')
    resultado['pdf_papeletas_no_utilizadas'] = votos_extraidos.get('papeletas_no_utilizadas')
    resultado['pdf_papeletas_utilizadas'] = votos_extraidos.get('papeletas_utilizadas')
    resultado['pdf_numero_acta_qr'] = votos_extraidos.get('numero_acta_qr')
    resultado['pdf_numero_acta_barra'] = votos_extraidos.get('numero_acta_barra')

    # Calcular sumatoria
    votos_lista = [
        resultado['pdf_votos_dc'],
        resultado['pdf_votos_libre'],
        resultado['pdf_votos_pinu'],
        resultado['pdf_votos_liberal'],
        resultado['pdf_votos_nacional'],
        resultado['pdf_votos_blanco'],
        resultado['pdf_votos_nulos']
    ]

    if all(v is not None for v in votos_lista):
        resultado['SumatoriaManualPorPartido'] = sum(votos_lista)

    # Validaciones
    partidos_a_comparar = [
        ('votos_dc', 'pdf_votos_dc', 'DC'),
        ('votos_libre', 'pdf_votos_libre', 'LIBRE'),
        ('votos_pinu', 'pdf_votos_pinu', 'PINU'),
        ('votos_liberal', 'pdf_votos_liberal', 'LIBERAL'),
        ('votos_nacional', 'pdf_votos_nacional', 'NACIONAL'),
        ('votos_blanco', 'pdf_votos_blanco', 'BLANCO'),
        ('votos_nulos', 'pdf_votos_nulos', 'NULOS')
    ]

    tiene_inconsistencia = False
    discrepancias = []

    for campo_digitado, campo_pdf, nombre in partidos_a_comparar:
        voto_digitado = acta.get(campo_digitado, 0)
        voto_pdf = resultado.get(campo_pdf)

        if voto_pdf is not None and voto_digitado != voto_pdf:
            tiene_inconsistencia = True
            diferencia = voto_pdf - voto_digitado
            discrepancias.append(f"{nombre}: Digitado={voto_digitado}, PDF={voto_pdf}, Diff={diferencia:+d}")

    resultado['InconsistenciaDatosDigitados'] = 1 if tiene_inconsistencia else 0

    # Otras validaciones
    sumatoria = resultado['SumatoriaManualPorPartido']
    gran_total = resultado['pdf_gran_total']
    total_votantes = resultado['pdf_total_votantes']

    if sumatoria is not None and gran_total is not None and total_votantes is not None:
        if total_votantes != gran_total or sumatoria != gran_total:
            resultado['InconsistenciaGrandTotalPorVotantes'] = 1

    jrv_json = acta.get('numero_jrv')
    jrv_pdf = resultado['pdf_jrv']
    if jrv_pdf is not None and jrv_json is not None and jrv_json != jrv_pdf:
        resultado['InconsistenciaJrv'] = 1

    papeletas_recibidas = resultado['pdf_papeletas_recibidas']
    papeletas_no_utilizadas = resultado['pdf_papeletas_no_utilizadas']
    papeletas_utilizadas = resultado['pdf_papeletas_utilizadas']

    if all(v is not None for v in [papeletas_recibidas, papeletas_no_utilizadas, papeletas_utilizadas, total_votantes]):
        papeletas_esperadas = papeletas_recibidas - papeletas_no_utilizadas
        if papeletas_utilizadas != papeletas_esperadas or papeletas_utilizadas != total_votantes:
            resultado['InconsistenciaPapeletas'] = 1

    qr = resultado['pdf_numero_acta_qr']
    barra = resultado['pdf_numero_acta_barra']
    if qr is not None and barra is not None and qr != barra:
        resultado['NumeroActaInconsistente'] = 1

    # Mostrar resultado
    print("🔍 Validación completada:")
    if resultado['InconsistenciaDatosDigitados'] == 1:
        print("⚠️  DATOS DIGITADOS INCONSISTENTES:")
        for disc in discrepancias:
            print(f"   {disc}")
    else:
        print("✅ Datos digitados consistentes")

    return resultado

def validar_actas_dos_fases(ruta_json: str):
    """
    FASE 1: Valida todas con Sonnet 4
    FASE 2: Re-valida inconsistentes con Opus 4.5
    """

    if not ANTHROPIC_API_KEY:
        print("❌ ERROR: Debes configurar tu ANTHROPIC_API_KEY")
        sys.exit(1)

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    actas = cargar_json(ruta_json)

    # ==================== FASE 1: SONNET 4 ====================
    print("=" * 80)
    print("🔵 FASE 1: Validación con Claude Sonnet 4 (TODAS las actas)")
    print("=" * 80)
    print()

    resultados_fase1 = []
    total = len(actas)

    for idx, acta in enumerate(actas, 1):
        numero_jrv = acta.get('numero_jrv', 'N/A')
        municipio = acta.get('municipio', 'N/A')

        print(f"\n[FASE 1: {idx}/{total}] JRV {numero_jrv} - {municipio}")
        print("-" * 80)

        resultado = procesar_acta(acta, client, MODELO_FASE1, "FASE 1")
        resultados_fase1.append(resultado)

        if idx < total:
            time.sleep(DELAY_ENTRE_PETICIONES)

    # Guardar resultados de Fase 1
    ruta_fase1 = "resultados_fase1_sonnet.json"
    print(f"\n💾 Guardando resultados Fase 1 en: {ruta_fase1}")
    with open(ruta_fase1, 'w', encoding='utf-8') as f:
        json.dump(resultados_fase1, f, ensure_ascii=False, indent=2)

    # Identificar actas con inconsistencias
    actas_inconsistentes = [
        r for r in resultados_fase1
        if r['InconsistenciaDatosDigitados'] == 1 or
           r['InconsistenciaGrandTotalPorVotantes'] == 1 or
           r['InconsistenciaJrv'] == 1 or
           r['InconsistenciaPapeletas'] == 1 or
           r['NumeroActaInconsistente'] == 1
    ]

    print(f"\n📊 Resumen Fase 1:")
    print(f"   Total procesadas: {total}")
    print(f"   Con inconsistencias: {len(actas_inconsistentes)}")
    print(f"   Sin inconsistencias: {total - len(actas_inconsistentes)}")

    if len(actas_inconsistentes) == 0:
        print("\n✅ ¡No hay inconsistencias! Todas las actas están correctas.")
        return

    # ==================== FASE 2: OPUS 4.5 ====================
    print("\n" + "=" * 80)
    print(f"💎 FASE 2: Re-validación con Claude Opus 4.5 ({len(actas_inconsistentes)} actas)")
    print("=" * 80)
    print()

    resultados_fase2 = []

    for idx, acta_inconsistente in enumerate(actas_inconsistentes, 1):
        numero_jrv = acta_inconsistente.get('numero_jrv', 'N/A')
        municipio = acta_inconsistente.get('municipio', 'N/A')

        print(f"\n[FASE 2: {idx}/{len(actas_inconsistentes)}] JRV {numero_jrv} - {municipio}")
        print("-" * 80)

        # Re-procesar con Opus 4.5
        resultado_opus = procesar_acta(acta_inconsistente, client, MODELO_FASE2, "FASE 2")
        resultados_fase2.append(resultado_opus)

        if idx < len(actas_inconsistentes):
            time.sleep(DELAY_ENTRE_PETICIONES)

    # Combinar resultados: Opus sobrescribe Sonnet para inconsistentes
    resultados_finales = []
    jrvs_revalidados = {r['numero_jrv'] for r in resultados_fase2}

    for r in resultados_fase1:
        if r['numero_jrv'] in jrvs_revalidados:
            # Buscar la versión de Opus
            resultado_opus = next((ro for ro in resultados_fase2 if ro['numero_jrv'] == r['numero_jrv']), None)
            if resultado_opus:
                resultados_finales.append(resultado_opus)
        else:
            resultados_finales.append(r)

    # Guardar resultados finales
    ruta_final = "resultados_validados_dos_fases.json"
    print(f"\n💾 Guardando resultados finales en: {ruta_final}")
    with open(ruta_final, 'w', encoding='utf-8') as f:
        json.dump(resultados_finales, f, ensure_ascii=False, indent=2)

    # Resumen final
    inconsistentes_final = sum(1 for r in resultados_finales if r['InconsistenciaDatosDigitados'] == 1)

    print("\n" + "=" * 80)
    print("📊 RESUMEN FINAL - VALIDACIÓN EN DOS FASES")
    print("=" * 80)
    print(f"Total actas procesadas:           {total}")
    print(f"Fase 1 (Sonnet 4):                {total} actas")
    print(f"Fase 2 (Opus 4.5):                {len(actas_inconsistentes)} actas")
    print(f"Inconsistencias detectadas:       {inconsistentes_final}")
    print(f"Actas correctas:                  {total - inconsistentes_final}")
    print(f"Tasa de éxito:                    {((total - inconsistentes_final)/total*100):.1f}%")
    print(f"\n💰 Costo estimado:")
    print(f"   Fase 1 (Sonnet): ~${total * 0.003:.2f}")
    print(f"   Fase 2 (Opus):   ~${len(actas_inconsistentes) * 0.015:.2f}")
    print(f"   TOTAL:           ~${total * 0.003 + len(actas_inconsistentes) * 0.015:.2f}")

def main():
    print("=" * 80)
    print("🗳️  VALIDADOR DE ACTAS EN DOS FASES")
    print("   FASE 1: Claude Sonnet 4 (todas las actas)")
    print("   FASE 2: Claude Opus 4.5 (solo inconsistentes)")
    print("   Máxima Precisión + Costo Optimizado")
    print("=" * 80)
    print()

    archivo_entrada = "resultados_jrv_detallado.json"

    if not Path(archivo_entrada).exists():
        print(f"❌ ERROR: No se encuentra {archivo_entrada}")
        sys.exit(1)

    try:
        validar_actas_dos_fases(archivo_entrada)
    except KeyboardInterrupt:
        print("\n\n⚠️  Validación interrumpida")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
