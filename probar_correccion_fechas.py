#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar la corrección de fechas N/A
"""

import pandas as pd
import sys
import os
sys.path.append('.')

from generador_pdf_dispositivos import GeneradorPDFDispositivos

# Crear instancia del generador
generador = GeneradorPDFDispositivos()

print('🔍 PROBANDO CORRECCIÓN DE FECHAS N/A')

# Obtener datos de prueba
df_datos, info = generador.leer_datos_dispositivo_con_filtro(
    proyecto_id=14, 
    codigo_interno='LVAG-05', 
    fecha_inicio='2025-11-24', 
    fecha_fin='2025-11-27'
)

if not df_datos.empty:
    print(f'📊 Datos obtenidos: {len(df_datos)} registros')
    
    # Aplicar formateo
    df_formateado = generador.formatear_datos_para_tabla(df_datos)
    
    # Verificar si hay N/A en fechas
    fechas_na = df_formateado['fecha'] == 'N/A'
    fecha_ins_na = df_formateado['fecha_insercion'] == 'N/A'
    
    print(f'\n📋 RESULTADOS:')
    print(f'Registros con fecha N/A: {fechas_na.sum()}')
    print(f'Registros con fecha_insercion N/A: {fecha_ins_na.sum()}')
    
    if fechas_na.sum() > 0 or fecha_ins_na.sum() > 0:
        print('\n❌ AÚN HAY FECHAS N/A')
        if fechas_na.sum() > 0:
            print('Primeras fechas problemáticas:')
            print(df_formateado[fechas_na][['fecha']].head())
        if fecha_ins_na.sum() > 0:
            print('Primeras fechas_insercion problemáticas:')
            print(df_formateado[fecha_ins_na][['fecha_insercion']].head())
    else:
        print('\n✅ TODAS LAS FECHAS SE FORMATEARON CORRECTAMENTE')
    
    # Mostrar muestra
    print(f'\n📋 MUESTRA DE FECHAS FORMATEADAS:')
    muestra = df_formateado[['fecha', 'fecha_insercion']].head(5)
    print(muestra)
    
else:
    print('❌ No se obtuvieron datos para probar')