#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convertidor de JSON a Excel con Formato Profesional
Convierte resultados_validados_gemini.json a Excel con:
- Formato de tabla
- Columnas autoajustadas al contenido
- Links clicleables
- Sumatorias al final
- Formato bonito y profesional
"""

import json
import sys
import os
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo
except ImportError:
    print("❌ Error: Necesitas instalar openpyxl")
    print("💡 Ejecuta: pip install openpyxl")
    sys.exit(1)

import argparse
import glob
import re

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Carpeta de archivos JSON por departamento
OUTPUT_DIR = 'OutputDepartamentos'

# Archivos por defecto (si no se especifica departamento)
JSON_INPUT = 'resultados_validados_gemini.json'
EXCEL_OUTPUT = 'resultados_validados_gemini.xlsx'

# Archivo con JRVs faltantes
JRVS_FALTANTES_FILE = 'jrvs_faltantes.js'

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

# Colores (RGB en hexadecimal)
COLOR_HEADER = 'FF2E75B6'  # Azul profesional
COLOR_TOTAL = 'FFF4B084'    # Naranja suave
COLOR_INCONSISTENCIA = 'FFFFC7CE'  # Rojo claro
COLOR_OK = 'FFC6EFCE'  # Verde claro
COLOR_LINK = 'FF0563C1'  # Azul para links
COLOR_AMARILLO = 'FFFFFF00'  # Amarillo para diferencias CNE vs IA
COLOR_ROJO = 'FFFF0000'  # Rojo para suma incorrecta

# ============================================================================
# FUNCIONES
# ============================================================================

def cargar_jrvs_faltantes() -> set:
    """Carga el set de JRVs faltantes desde jrvs_faltantes.js"""
    print(f"📂 Cargando JRVs faltantes desde: {JRVS_FALTANTES_FILE}")

    if not os.path.exists(JRVS_FALTANTES_FILE):
        print(f"❌ Error: Archivo no encontrado: {JRVS_FALTANTES_FILE}")
        sys.exit(1)

    with open(JRVS_FALTANTES_FILE, 'r', encoding='utf-8') as f:
        contenido = f.read()

    # Extraer el array JRVS_FALTANTES usando regex
    # Buscar: const JRVS_FALTANTES = [ ... ];
    match = re.search(r'const\s+JRVS_FALTANTES\s*=\s*\[([\s\S]*?)\];', contenido)

    if not match:
        print(f"❌ Error: No se pudo encontrar JRVS_FALTANTES en {JRVS_FALTANTES_FILE}")
        sys.exit(1)

    # Extraer números del array
    array_contenido = match.group(1)
    numeros = re.findall(r'\d+', array_contenido)
    jrvs_faltantes = set(int(num) for num in numeros)

    print(f"✅ Cargados {len(jrvs_faltantes):,} JRVs faltantes\n")
    return jrvs_faltantes

def cargar_json(ruta: str) -> list:
    """Carga el JSON con los datos validados"""
    print(f"📂 Cargando datos desde: {ruta}")

    if not os.path.exists(ruta):
        print(f"❌ Error: Archivo no encontrado: {ruta}")
        sys.exit(1)

    with open(ruta, 'r', encoding='utf-8') as f:
        datos = json.load(f)

    if isinstance(datos, dict):
        datos = [datos]

    # Procesar cada registro para agregar campos calculados
    print("🔄 Procesando datos y agregando campos calculados...")
    for registro in datos:
        # Calcular SumCneManual (suma de votos individuales del CNE)
        sum_cne_manual = (
            registro.get('votos_dc', 0) +
            registro.get('votos_libre', 0) +
            registro.get('votos_pinu', 0) +
            registro.get('votos_liberal', 0) +
            registro.get('votos_nacional', 0) +
            registro.get('votos_blanco', 0) +
            registro.get('votos_nulos', 0)
        )

        # Agregar campo SumCneManual
        registro['SumCneManual'] = sum_cne_manual

        # Verificar si hay inconsistencia entre SumCneManual y pdf_gran_total
        pdf_gran_total = registro.get('pdf_gran_total')
        if pdf_gran_total is not None and sum_cne_manual != pdf_gran_total:
            registro['InconsistenciaGrandTotalManual'] = 1
        else:
            registro['InconsistenciaGrandTotalManual'] = 0

        # ===================================================================
        # NUEVO: RequiereRevisionActaSumada y MotivoRevision
        # ===================================================================
        motivos = []
        requiere_revision = 0

        # 1. Verificar InconsistenciaDatosDigitados
        if registro.get('InconsistenciaDatosDigitados', 0) == 1:
            requiere_revision = 1
            motivos.append("Inconsistencia en datos digitados CNE vs IA")

        # 2. Verificar si sumatoria manual no coincide con el del CNE
        if registro.get('InconsistenciaGrandTotalManual', 0) == 1:
            requiere_revision = 1
            motivos.append(f"Suma manual ({sum_cne_manual}) ≠ Gran Total IA ({pdf_gran_total})")

        # 3. Verificar papeletas: recibidas - no_utilizadas = utilizadas
        pdf_recibidas = registro.get('pdf_papeletas_recibidas')
        pdf_no_utilizadas = registro.get('pdf_papeletas_no_utilizadas')
        pdf_utilizadas = registro.get('pdf_papeletas_utilizadas')

        if pdf_recibidas is not None and pdf_no_utilizadas is not None and pdf_utilizadas is not None:
            if (pdf_recibidas - pdf_no_utilizadas) != pdf_utilizadas:
                requiere_revision = 1
                motivos.append(f"Papeletas: Recibidas({pdf_recibidas}) - No utilizadas({pdf_no_utilizadas}) ≠ Utilizadas({pdf_utilizadas})")

        # 4. Verificar papeletas utilizadas = total votantes
        pdf_total_votantes = registro.get('pdf_total_votantes')
        if pdf_utilizadas is not None and pdf_total_votantes is not None:
            if pdf_utilizadas != pdf_total_votantes:
                requiere_revision = 1
                motivos.append(f"Papeletas utilizadas({pdf_utilizadas}) ≠ Total votantes({pdf_total_votantes})")

        # Agregar campos
        registro['RequiereRevisionActaSumada'] = requiere_revision
        registro['MotivoRevision'] = "; ".join(motivos) if motivos else "OK - No requiere revisión"

        # ===================================================================
        # NUEVO: Detección de fraude en contra de Liberal
        # ===================================================================

        # LiberalVotosFaltantes: CNE < IA (Liberal tiene menos votos de los que debería)
        votos_liberal_cne = registro.get('votos_liberal', 0)
        pdf_votos_liberal = registro.get('pdf_votos_liberal')

        if pdf_votos_liberal is not None and votos_liberal_cne < pdf_votos_liberal:
            registro['LiberalVotosFaltantes'] = 1
        else:
            registro['LiberalVotosFaltantes'] = 0

        # NacionalVotosSobrantes: CNE > IA (Nacional tiene más votos de los que debería)
        votos_nacional_cne = registro.get('votos_nacional', 0)
        pdf_votos_nacional = registro.get('pdf_votos_nacional')

        if pdf_votos_nacional is not None and votos_nacional_cne > pdf_votos_nacional:
            registro['NacionalVotosSobrantes'] = 1
        else:
            registro['NacionalVotosSobrantes'] = 0

    print(f"✅ Cargados {len(datos)} registros\n")
    return datos

def es_campo_numerico(valor) -> bool:
    """Verifica si un campo es numérico"""
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)

def es_campo_link(nombre_campo: str) -> bool:
    """Verifica si un campo es un link"""
    return 'url' in nombre_campo.lower() or 'link' in nombre_campo.lower()

def es_campo_inconsistencia(nombre_campo: str) -> bool:
    """Verifica si un campo es de inconsistencia"""
    nombre_lower = nombre_campo.lower()
    return 'inconsistencia' in nombre_lower or nombre_lower.startswith('es_inconsistente')

def aplicar_estilo_header(ws, fila: int, total_columnas: int):
    """Aplica estilo al encabezado"""
    for col in range(1, total_columnas + 1):
        celda = ws.cell(row=fila, column=col)
        celda.font = Font(bold=True, color='FFFFFFFF', size=11)
        celda.fill = PatternFill(start_color=COLOR_HEADER, end_color=COLOR_HEADER, fill_type='solid')
        celda.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        celda.border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

def aplicar_estilo_total(ws, fila: int, total_columnas: int):
    """Aplica estilo a la fila de totales"""
    for col in range(1, total_columnas + 1):
        celda = ws.cell(row=fila, column=col)
        celda.font = Font(bold=True, size=11)
        celda.fill = PatternFill(start_color=COLOR_TOTAL, end_color=COLOR_TOTAL, fill_type='solid')
        celda.alignment = Alignment(horizontal='center', vertical='center')
        celda.border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='medium'),
            bottom=Side(style='medium')
        )

def aplicar_formato_condicional(ws, fila: int, col: int, valor, nombre_campo: str, registro: dict):
    """Aplica formato condicional según el tipo de dato"""
    celda = ws.cell(row=fila, column=col)

    # Bordes para todas las celdas
    celda.border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Alineación
    if es_campo_numerico(valor):
        celda.alignment = Alignment(horizontal='right', vertical='center')
    else:
        celda.alignment = Alignment(horizontal='left', vertical='center')

    # FORMATO AMARILLO: Diferencias entre CNE e IA
    # Comparar votos_X (CNE) con pdf_votos_X (IA)
    campos_comparacion = {
        'votos_dc': 'pdf_votos_dc',
        'votos_libre': 'pdf_votos_libre',
        'votos_pinu': 'pdf_votos_pinu',
        'votos_liberal': 'pdf_votos_liberal',
        'votos_nacional': 'pdf_votos_nacional',
        'votos_blanco': 'pdf_votos_blanco',
        'votos_nulos': 'pdf_votos_nulos',
        'pdf_votos_dc': 'votos_dc',
        'pdf_votos_libre': 'votos_libre',
        'pdf_votos_pinu': 'votos_pinu',
        'pdf_votos_liberal': 'votos_liberal',
        'pdf_votos_nacional': 'votos_nacional',
        'pdf_votos_blanco': 'votos_blanco',
        'pdf_votos_nulos': 'votos_nulos',
    }

    # Verificar si este campo tiene diferencia CNE vs IA
    if nombre_campo in campos_comparacion:
        campo_comparar = campos_comparacion[nombre_campo]
        valor_cne = registro.get(nombre_campo) if nombre_campo.startswith('votos_') else registro.get(campo_comparar)
        valor_ia = registro.get(campo_comparar) if nombre_campo.startswith('votos_') else registro.get(nombre_campo)

        if valor_cne != valor_ia and valor_ia is not None:
            celda.fill = PatternFill(start_color=COLOR_AMARILLO, end_color=COLOR_AMARILLO, fill_type='solid')
            celda.font = Font(bold=True)
            return

    # Comparar GrandTotal (SumCneManual vs pdf_gran_total)
    if nombre_campo == 'SumCneManual' or nombre_campo == 'pdf_gran_total':
        sum_cne = registro.get('SumCneManual')
        pdf_total = registro.get('pdf_gran_total')

        if sum_cne != pdf_total and pdf_total is not None:
            celda.fill = PatternFill(start_color=COLOR_AMARILLO, end_color=COLOR_AMARILLO, fill_type='solid')
            celda.font = Font(bold=True)
            return

    # FORMATO ROJO: SumCneManual cuando no coincide con pdf_gran_total
    if nombre_campo == 'SumCneManual' and registro.get('InconsistenciaGrandTotalManual', 0) == 1:
        celda.fill = PatternFill(start_color=COLOR_ROJO, end_color=COLOR_ROJO, fill_type='solid')
        celda.font = Font(bold=True, color='FFFFFFFF')
        return

    # FORMATO ROJO: InconsistenciaGrandTotalManual cuando es 1
    if nombre_campo == 'InconsistenciaGrandTotalManual' and valor == 1:
        celda.fill = PatternFill(start_color=COLOR_ROJO, end_color=COLOR_ROJO, fill_type='solid')
        celda.font = Font(bold=True, color='FFFFFFFF')
        return

    # FORMATO ROJO: RequiereRevisionActaSumada cuando es 1
    if nombre_campo == 'RequiereRevisionActaSumada' and valor == 1:
        celda.fill = PatternFill(start_color=COLOR_ROJO, end_color=COLOR_ROJO, fill_type='solid')
        celda.font = Font(bold=True, color='FFFFFFFF')
        return

    # FORMATO AMARILLO: MotivoRevision cuando no es "OK"
    if nombre_campo == 'MotivoRevision' and valor != "OK - No requiere revisión":
        celda.fill = PatternFill(start_color=COLOR_AMARILLO, end_color=COLOR_AMARILLO, fill_type='solid')
        celda.font = Font(bold=True)
        celda.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
        return

    # FORMATO ROJO: LiberalVotosFaltantes cuando es 1 (fraude)
    if nombre_campo == 'LiberalVotosFaltantes' and valor == 1:
        celda.fill = PatternFill(start_color=COLOR_ROJO, end_color=COLOR_ROJO, fill_type='solid')
        celda.font = Font(bold=True, color='FFFFFFFF')
        return

    # FORMATO ROJO: NacionalVotosSobrantes cuando es 1 (fraude)
    if nombre_campo == 'NacionalVotosSobrantes' and valor == 1:
        celda.fill = PatternFill(start_color=COLOR_ROJO, end_color=COLOR_ROJO, fill_type='solid')
        celda.font = Font(bold=True, color='FFFFFFFF')
        return

    # Color de fondo para inconsistencias
    if es_campo_inconsistencia(nombre_campo) and valor == 1:
        celda.fill = PatternFill(start_color=COLOR_INCONSISTENCIA, end_color=COLOR_INCONSISTENCIA, fill_type='solid')
        celda.font = Font(bold=True)
    elif nombre_campo == 'SumatoriaManualPorPartido' or nombre_campo == 'pdf_gran_total':
        celda.font = Font(bold=True)

def autoajustar_columnas(ws, datos: list, headers: list):
    """Autoajusta el ancho de las columnas según el contenido"""
    for idx, header in enumerate(headers, 1):
        max_length = len(str(header))

        # Revisar el contenido de todas las filas
        for dato in datos:
            valor = dato.get(header, '')
            if valor is not None:
                valor_str = str(valor)
                # Limitar el ancho máximo a 80 caracteres
                if es_campo_link(header):
                    # Para links, usar el texto "Ver acta" que es más corto
                    max_length = max(max_length, len("Ver acta"))
                elif header == 'MotivoRevision':
                    # Para MotivoRevision, usar un ancho mayor (hasta 100 caracteres)
                    max_length = max(max_length, min(len(valor_str), 100))
                else:
                    max_length = max(max_length, min(len(valor_str), 80))

        # Establecer el ancho de la columna (agregar padding)
        adjusted_width = max_length + 2
        ws.column_dimensions[get_column_letter(idx)].width = adjusted_width

def crear_excel(datos: list, archivo_salida: str):
    """Crea el archivo Excel con formato profesional"""
    print("📊 Creando archivo Excel...")

    if len(datos) == 0:
        print("⚠️  No hay datos para exportar")
        return

    # Crear workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados Validados"

    # Obtener headers (todas las claves del primer registro)
    headers_originales = list(datos[0].keys())

    # Reordenar headers: numero_jrv y url_drive al inicio, RequiereRevisionActaSumada y MotivoRevision al final
    headers = []

    # Columnas al inicio
    columnas_inicio = ['numero_jrv', 'url_drive']

    # Columnas al final
    columnas_final = ['RequiereRevisionActaSumada', 'MotivoRevision', 'LiberalVotosFaltantes', 'NacionalVotosSobrantes']

    # Agregar columnas del inicio
    for col in columnas_inicio:
        if col in headers_originales:
            headers.append(col)

    # Agregar el resto de columnas (excluyendo las del inicio y del final)
    for h in headers_originales:
        if h not in columnas_inicio and h not in columnas_final:
            headers.append(h)

    # Agregar columnas del final
    for col in columnas_final:
        if col in headers_originales:
            headers.append(col)

    total_columnas = len(headers)

    # Identificar columnas numéricas para sumar
    columnas_numericas = {}
    for idx, header in enumerate(headers, 1):
        primer_valor = datos[0].get(header)
        if es_campo_numerico(primer_valor):
            columnas_numericas[idx] = header

    # Escribir encabezados
    print("✍️  Escribiendo encabezados...")
    for idx, header in enumerate(headers, 1):
        ws.cell(row=1, column=idx, value=header)

    # Escribir datos
    print(f"✍️  Escribiendo {len(datos)} filas de datos...")
    for fila_idx, dato in enumerate(datos, 2):
        for col_idx, header in enumerate(headers, 1):
            valor = dato.get(header, '')

            # Convertir None a string vacío
            if valor is None:
                valor = ''

            # Escribir el valor
            ws.cell(row=fila_idx, column=col_idx, value=valor)

            # Si es un link, convertirlo en hipervínculo
            if es_campo_link(header) and valor and str(valor).startswith('http'):
                celda = ws.cell(row=fila_idx, column=col_idx)
                celda.hyperlink = str(valor)
                celda.font = Font(color=COLOR_LINK, underline='single')
                celda.value = "Ver acta"  # Texto más corto y limpio

            # Aplicar formato condicional (pasar el registro completo)
            aplicar_formato_condicional(ws, fila_idx, col_idx, valor, header, dato)

    # Aplicar formato de tabla a los datos (sin incluir totales)
    print("📋 Aplicando formato de tabla con filtros...")
    ultima_fila_datos = len(datos) + 1
    ultima_columna = get_column_letter(total_columnas)

    # Crear tabla de Excel (incluye encabezados y datos, NO totales)
    tabla_rango = f"A1:{ultima_columna}{ultima_fila_datos}"
    tabla = Table(displayName="TablaResultados", ref=tabla_rango)

    # Estilo de tabla (azul medio con bandas)
    estilo_tabla = TableStyleInfo(
        name="TableStyleMedium9",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False
    )
    tabla.tableStyleInfo = estilo_tabla
    ws.add_table(tabla)

    # Dejar una fila en blanco como separador
    fila_separador = len(datos) + 2

    # Agregar fila de TOTALES (después de la fila en blanco)
    print("🔢 Calculando totales...")
    fila_total = len(datos) + 3

    # Primera columna: texto "TOTAL"
    ws.cell(row=fila_total, column=1, value="TOTAL")

    # Sumar columnas numéricas (excluyendo la fila de separación)
    for col_idx, nombre_campo in columnas_numericas.items():
        # Usar fórmula SUM para calcular el total (solo datos, no separador)
        letra_col = get_column_letter(col_idx)
        formula = f"=SUM({letra_col}2:{letra_col}{ultima_fila_datos})"
        ws.cell(row=fila_total, column=col_idx, value=formula)

    # Aplicar estilo a la fila de totales
    aplicar_estilo_total(ws, fila_total, total_columnas)

    # Autoajustar columnas
    print("📏 Autoajustando ancho de columnas...")
    autoajustar_columnas(ws, datos, headers)

    # Congelar paneles: Primera fila + columnas numero_jrv y url_drive
    # Encontrar columnas clave para fijar
    columnas_clave = ['numero_jrv', 'url_drive']
    ultima_col_fija = 0

    for col_clave in columnas_clave:
        if col_clave in headers:
            idx = headers.index(col_clave) + 1
            ultima_col_fija = max(ultima_col_fija, idx)

    # Si encontramos columnas clave, congelar hasta después de la última
    if ultima_col_fija > 0:
        letra_col = get_column_letter(ultima_col_fija + 1)
        ws.freeze_panes = f'{letra_col}2'  # Congela columnas hasta ultima_col_fija y fila 1
        columnas_fijadas = [headers[i] for i in range(ultima_col_fija)]
        print(f"🔒 Columnas fijadas: 1-{ultima_col_fija} ({', '.join(columnas_fijadas)})")
    else:
        # Si no hay columnas clave, solo fijar encabezado
        ws.freeze_panes = 'A2'
        print(f"🔒 Solo encabezado fijado")

    # Guardar archivo
    print(f"💾 Guardando archivo: {archivo_salida}")
    wb.save(archivo_salida)
    print(f"✅ Archivo Excel creado exitosamente!\n")

def mostrar_resumen(datos: list):
    """Muestra un resumen de las estadísticas"""
    print("=" * 80)
    print("📊 RESUMEN DE DATOS")
    print("=" * 80)
    print(f"Total de registros: {len(datos)}")

    # Contar inconsistencias
    inconsistencias = sum(1 for d in datos if d.get('InconsistenciaDatosDigitados', 0) == 1)
    print(f"Actas con inconsistencias: {inconsistencias}")
    print(f"Actas correctas: {len(datos) - inconsistencias}")

    if len(datos) > 0:
        porcentaje = ((len(datos) - inconsistencias) / len(datos)) * 100
        print(f"Porcentaje de precisión: {porcentaje:.1f}%")

    # Sumar votos
    total_nacional = sum(d.get('pdf_votos_nacional', 0) or 0 for d in datos)
    total_liberal = sum(d.get('pdf_votos_liberal', 0) or 0 for d in datos)
    total_libre = sum(d.get('pdf_votos_libre', 0) or 0 for d in datos)

    print(f"\n🗳️  TOTALES DE VOTOS (desde PDF):")
    print(f"   Partido Nacional: {total_nacional:,}")
    print(f"   Partido Liberal: {total_liberal:,}")
    print(f"   Partido LIBRE: {total_libre:,}")
    print("=" * 80)
    print()

def main():
    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser(
        description='Conversor JSON a Excel - Resultados Validados',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Ejemplos de uso:
  python json_to_excel_formateado.py --depto 05          # Solo CORTES
  python json_to_excel_formateado.py --depto 08          # Solo FRANCISCO MORAZAN
  python json_to_excel_formateado.py                      # Todos los departamentos (consolidado)
  python json_to_excel_formateado.py --solofaltantes 1   # Solo JRVs faltantes

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
    parser.add_argument('--solofaltantes', type=int, default=0, choices=[0, 1],
                        help='Si es 1, solo convierte JRVs que existen en jrvs_faltantes.js (default: 0)')
    args = parser.parse_args()

    print("=" * 80)
    print("CONVERSOR JSON A EXCEL - RESULTADOS VALIDADOS")
    print("=" * 80)
    print()

    # Mostrar información de filtrado si está habilitado
    if args.solofaltantes == 1:
        print("⚠️  FILTRO ACTIVO: Solo se procesarán JRVs faltantes")
        print(f"📋 Archivo de referencia: {JRVS_FALTANTES_FILE}\n")

    # Determinar archivos de entrada y salida según parámetro
    archivo_entrada = JSON_INPUT
    archivo_salida = EXCEL_OUTPUT

    if args.depto:
        # Procesar departamento específico
        id_departamento = args.depto.zfill(2)  # Asegurar 2 dígitos

        if id_departamento not in DEPARTAMENTOS:
            print(f"❌ Error: Departamento '{id_departamento}' no válido")
            print("\n📋 Departamentos disponibles:")
            for id_dep, nombre in sorted(DEPARTAMENTOS.items()):
                print(f"   {id_dep} = {nombre}")
            sys.exit(1)

        nombre_departamento = DEPARTAMENTOS[id_departamento]
        archivo_entrada = os.path.join(OUTPUT_DIR, f"{id_departamento}_{nombre_departamento.replace(' ', '_')}.json")
        archivo_salida = f"{id_departamento}_{nombre_departamento.replace(' ', '_')}.xlsx"

        print(f"🎯 Departamento seleccionado: {id_departamento} - {nombre_departamento}")
        print(f"📂 Archivo JSON: {archivo_entrada}")
        print(f"📊 Archivo Excel: {archivo_salida}\n")
    else:
        # Consolidar todos los departamentos
        print(f"📋 Consolidando TODOS los departamentos...")
        print(f"📂 Buscando archivos en: {OUTPUT_DIR}/\n")

        # Buscar todos los archivos JSON en OutputDepartamentos
        patron = os.path.join(OUTPUT_DIR, "*.json")
        archivos_json = glob.glob(patron)

        if not archivos_json:
            print(f"⚠️  No se encontraron archivos JSON en {OUTPUT_DIR}/")
            print(f"   Usando archivo por defecto: {archivo_entrada}\n")
        else:
            # Consolidar todos los JSONs
            print(f"✅ Encontrados {len(archivos_json)} archivos JSON")
            datos_consolidados = []

            for archivo in sorted(archivos_json):
                try:
                    with open(archivo, 'r', encoding='utf-8') as f:
                        datos_depto = json.load(f)
                        if isinstance(datos_depto, list):
                            datos_consolidados.extend(datos_depto)
                            print(f"   ✅ {os.path.basename(archivo)}: {len(datos_depto)} actas")
                except Exception as e:
                    print(f"   ⚠️  Error en {os.path.basename(archivo)}: {e}")

            if datos_consolidados:
                # Guardar consolidado temporalmente
                archivo_temp = "temp_consolidado.json"
                with open(archivo_temp, 'w', encoding='utf-8') as f:
                    json.dump(datos_consolidados, f, ensure_ascii=False, indent=2)

                archivo_entrada = archivo_temp
                print(f"\n📊 Total consolidado: {len(datos_consolidados)} actas\n")
            else:
                print(f"\n⚠️  No se pudo consolidar datos, usando archivo por defecto\n")

    # Cargar datos
    datos = cargar_json(archivo_entrada)

    if len(datos) == 0:
        print("⚠️  El archivo JSON está vacío. No se generará Excel.")
        return

    # Filtrar solo JRVs faltantes si solofaltantes=1
    if args.solofaltantes == 1:
        print("🔍 Aplicando filtro: Solo JRVs faltantes")
        jrvs_faltantes = cargar_jrvs_faltantes()

        total_antes = len(datos)
        datos = [d for d in datos if d.get('numero_jrv') in jrvs_faltantes]
        total_despues = len(datos)

        print(f"📊 Registros antes del filtro: {total_antes:,}")
        print(f"📊 Registros después del filtro: {total_despues:,}")
        print(f"📊 Registros filtrados: {total_antes - total_despues:,}\n")

        if total_despues == 0:
            print("⚠️  No hay JRVs faltantes en el archivo JSON. No se generará Excel.")
            return

        # Modificar el nombre del archivo de salida para incluir "_faltantes"
        base_name, ext = os.path.splitext(archivo_salida)
        archivo_salida = f"{base_name}_faltantes{ext}"
        print(f"📝 Archivo de salida modificado: {archivo_salida}\n")

    # Ordenar datos por numero_jrv (de menor a mayor)
    print("🔢 Ordenando datos por numero_jrv...")
    datos.sort(key=lambda x: x.get('numero_jrv', 0))
    print(f"✅ Datos ordenados: JRV {datos[0].get('numero_jrv', 'N/A')} → {datos[-1].get('numero_jrv', 'N/A')}\n")

    # Mostrar resumen
    mostrar_resumen(datos)

    # Crear Excel
    crear_excel(datos, archivo_salida)

    # Limpiar archivo temporal si existe
    if 'archivo_temp' in locals() and os.path.exists(archivo_temp):
        os.remove(archivo_temp)

    # Mensaje final
    print("=" * 80)
    print("✅ CONVERSIÓN COMPLETADA")
    print("=" * 80)
    print(f"📁 Archivo generado: {archivo_salida}")
    print(f"📊 Total de filas: {len(datos)}")
    print(f"📏 Total de columnas: {len(datos[0].keys()) if datos else 0}")
    print()
    print("💡 Características del archivo:")
    print("   ✅ Formato de tabla de Excel con filtros automáticos")
    print("   ✅ Bandas de colores para mejor lectura")
    print("   ✅ Columnas autoajustadas al contenido")
    print("   ✅ Links clicleables (columna url_drive)")
    print("   ✅ Fila de totales con sumatorias (separada por fila en blanco)")
    print("   ✅ Formato condicional para inconsistencias")
    print("   ✅ Encabezados congelados")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
