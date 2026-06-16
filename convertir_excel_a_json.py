#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to convert resultados_validados_gemini.xlsx to JSON
Converts the Excel file to JSON format with the specified structure
"""

import pandas as pd
import json
import numpy as np

def convertir_excel_a_json(archivo_excel, archivo_json_salida):
    """
    Convert the Excel file to JSON with the required structure

    Args:
        archivo_excel: Path to the Excel file
        archivo_json_salida: Path where to save the JSON
    """

    print(f"Leyendo archivo Excel: {archivo_excel}")
    df = pd.read_excel(archivo_excel)

    print(f"Total de registros encontrados: {len(df)}")
    print(f"Total de columnas: {len(df.columns)}")

    # Replace NaN with None so it becomes null in JSON
    df = df.replace({np.nan: None})

    # Convert DataFrame to list of dictionaries
    resultados = []

    for index, row in df.iterrows():
        # Create JSON object with the specified structure
        registro = {
            "id_departamento": str(row.get("id_departamento", "")).zfill(2) if row.get("id_departamento") is not None else None,
            "departamento": row.get("departamento"),
            "id_municipio": str(row.get("id_municipio", "")).zfill(3) if row.get("id_municipio") is not None else None,
            "municipio": row.get("municipio"),
            "id_zona": str(row.get("id_zona", "")).zfill(2) if row.get("id_zona") is not None else None,
            "zona": row.get("zona"),
            "id_puesto": str(row.get("id_puesto", "")).zfill(3) if row.get("id_puesto") is not None else None,
            "puesto": row.get("puesto"),
            "numero_jrv": int(row.get("numero_jrv")) if pd.notna(row.get("numero_jrv")) else None,
            "fecha_corte": str(row.get("fecha_corte")) if row.get("fecha_corte") is not None else None,

            # Votes entered in the CNE system
            "votos_dc": int(row.get("votos_dc")) if pd.notna(row.get("votos_dc")) else 0,
            "votos_libre": int(row.get("votos_libre")) if pd.notna(row.get("votos_libre")) else 0,
            "votos_pinu": int(row.get("votos_pinu")) if pd.notna(row.get("votos_pinu")) else 0,
            "votos_liberal": int(row.get("votos_liberal")) if pd.notna(row.get("votos_liberal")) else 0,
            "votos_nacional": int(row.get("votos_nacional")) if pd.notna(row.get("votos_nacional")) else 0,
            "votos_nulos": int(row.get("votos_nulos")) if pd.notna(row.get("votos_nulos")) else 0,
            "votos_blanco": int(row.get("votos_blanco")) if pd.notna(row.get("votos_blanco")) else 0,

            # Ballot statistics
            "cantidad_total_actas": int(row.get("cantidad_total_actas")) if pd.notna(row.get("cantidad_total_actas")) else 0,
            "verificado": int(row.get("verificado")) if pd.notna(row.get("verificado")) else 0,
            "cantidad_inconsistencias": int(row.get("cantidad_inconsistencias")) if pd.notna(row.get("cantidad_inconsistencias")) else 0,
            "publicado": int(row.get("publicado")) if pd.notna(row.get("publicado")) else 0,
            "en_espera": int(row.get("en_espera")) if pd.notna(row.get("en_espera")) else 0,
            "correctas": int(row.get("correctas")) if pd.notna(row.get("correctas")) else 0,
            "inconsistencias": int(row.get("inconsistencias")) if pd.notna(row.get("inconsistencias")) else 0,
            "error_suma": int(row.get("error_suma")) if pd.notna(row.get("error_suma")) else 0,
            "etiquetas": str(row.get("etiquetas", "")) if row.get("etiquetas") else "",

            # PDF URL
            "url_drive": str(row.get("url_drive")) if row.get("url_drive") is not None else None,

            # Data extracted from PDF by AI
            "pdf_votos_dc": int(row.get("pdf_votos_dc")) if pd.notna(row.get("pdf_votos_dc")) else None,
            "pdf_votos_libre": int(row.get("pdf_votos_libre")) if pd.notna(row.get("pdf_votos_libre")) else None,
            "pdf_votos_pinu": int(row.get("pdf_votos_pinu")) if pd.notna(row.get("pdf_votos_pinu")) else None,
            "pdf_votos_liberal": int(row.get("pdf_votos_liberal")) if pd.notna(row.get("pdf_votos_liberal")) else None,
            "pdf_votos_nacional": int(row.get("pdf_votos_nacional")) if pd.notna(row.get("pdf_votos_nacional")) else None,
            "pdf_votos_blanco": int(row.get("pdf_votos_blanco")) if pd.notna(row.get("pdf_votos_blanco")) else None,
            "pdf_votos_nulos": int(row.get("pdf_votos_nulos")) if pd.notna(row.get("pdf_votos_nulos")) else None,
            "pdf_gran_total": int(row.get("pdf_gran_total")) if pd.notna(row.get("pdf_gran_total")) else None,
            "pdf_total_votantes": int(row.get("pdf_total_votantes")) if pd.notna(row.get("pdf_total_votantes")) else None,
            "pdf_jrv": int(row.get("pdf_jrv")) if pd.notna(row.get("pdf_jrv")) else None,
            "pdf_papeletas_recibidas": int(row.get("pdf_papeletas_recibidas")) if pd.notna(row.get("pdf_papeletas_recibidas")) else None,
            "pdf_papeletas_no_utilizadas": int(row.get("pdf_papeletas_no_utilizadas")) if pd.notna(row.get("pdf_papeletas_no_utilizadas")) else None,
            "pdf_papeletas_utilizadas": int(row.get("pdf_papeletas_utilizadas")) if pd.notna(row.get("pdf_papeletas_utilizadas")) else None,
            "pdf_numero_acta_qr": str(row.get("pdf_numero_acta_qr")) if row.get("pdf_numero_acta_qr") is not None else None,
            "pdf_numero_acta_barra": str(row.get("pdf_numero_acta_barra")) if row.get("pdf_numero_acta_barra") is not None else None,

            # Calculated fields
            "SumatoriaManualPorPartido": int(row.get("SumatoriaManualPorPartido")) if pd.notna(row.get("SumatoriaManualPorPartido")) else None,
            "codigo_jrv": int(row.get("codigo_jrv")) if pd.notna(row.get("codigo_jrv")) else None,

            # Inconsistency flags
            "InconsistenciaDatosDigitados": int(row.get("InconsistenciaDatosDigitados")) if pd.notna(row.get("InconsistenciaDatosDigitados")) else 0,
            "InconsistenciaGrandTotalPorVotantes": int(row.get("InconsistenciaGrandTotalPorVotantes")) if pd.notna(row.get("InconsistenciaGrandTotalPorVotantes")) else 0,
            "InconsistenciaJrv": int(row.get("InconsistenciaJrv")) if pd.notna(row.get("InconsistenciaJrv")) else 0,
            "InconsistenciaPapeletas": int(row.get("InconsistenciaPapeletas")) if pd.notna(row.get("InconsistenciaPapeletas")) else 0,
            "NumeroActaInconsistente": int(row.get("NumeroActaInconsistente")) if pd.notna(row.get("NumeroActaInconsistente")) else 0,
        }

        resultados.append(registro)

        # Show progress every 1000 records
        if (index + 1) % 1000 == 0:
            print(f"Procesados {index + 1} registros...")

    # Save JSON
    print(f"\nGuardando JSON en: {archivo_json_salida}")
    with open(archivo_json_salida, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"✓ Conversión completada exitosamente!")
    print(f"  Total de registros: {len(resultados)}")
    print(f"  Archivo generado: {archivo_json_salida}")

    # Statistics
    actas_con_url_drive = sum(1 for r in resultados if r.get("url_drive"))
    actas_con_inconsistencias = sum(1 for r in resultados if r.get("InconsistenciaDatosDigitados") == 1)

    print(f"\n📊 Estadísticas:")
    print(f"  Actas con url_drive: {actas_con_url_drive} ({actas_con_url_drive/len(resultados)*100:.1f}%)")
    print(f"  Actas con inconsistencias: {actas_con_inconsistencias} ({actas_con_inconsistencias/len(resultados)*100:.1f}%)")


if __name__ == "__main__":
    # Configuration
    archivo_excel = "resultados_validados_gemini.xlsx"
    archivo_json_salida = "resultados_validados_gemini.json"

    try:
        convertir_excel_a_json(archivo_excel, archivo_json_salida)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
