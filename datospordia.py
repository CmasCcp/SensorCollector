import pandas as pd
import os
from datetime import datetime, timedelta, date
import glob

def encontrar_dias_faltantes():
    """
    Encuentra los días faltantes en los datos CSV de cada carpeta en 'datos'
    y los exporta a Excel agrupados por codigo_interno.
    Identifica fechas futuras como aquellas donde fecha > fecha_insercion.
    """
    carpeta_datos = "datos"
    resultados = {}
    fecha_hoy = date.today()
    fechas_futuras_encontradas = []
    
    # Recorrer cada carpeta en la carpeta datos
    for carpeta in os.listdir(carpeta_datos):
        ruta_carpeta = os.path.join(carpeta_datos, carpeta)
        
        if os.path.isdir(ruta_carpeta):
            # Buscar archivos CSV en la carpeta
            archivos_csv = glob.glob(os.path.join(ruta_carpeta, "*.csv"))
            
            for archivo_csv in archivos_csv:
                try:
                    # Leer el archivo CSV
                    df = pd.read_csv(archivo_csv)
                    
                    # Verificar que existan las columnas necesarias
                    if 'fecha' not in df.columns or 'codigo_interno' not in df.columns or 'fecha_insercion' not in df.columns:
                        continue
                    
                    # Convertir las columnas de fecha a datetime
                    df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
                    df['fecha_insercion'] = pd.to_datetime(df['fecha_insercion'], errors='coerce')
                    df = df.dropna(subset=['fecha', 'fecha_insercion'])
                    
                    # Verificar fechas futuras (fecha > fecha_insercion)
                    fechas_futuras = df[df['fecha'] > df['fecha_insercion']]
                    if not fechas_futuras.empty:
                        for _, fila in fechas_futuras.iterrows():
                            fechas_futuras_encontradas.append({
                                'archivo': archivo_csv,
                                'codigo_interno': fila['codigo_interno'],
                                'fecha': fila['fecha'],
                                'fecha_insercion': fila['fecha_insercion']
                            })
                    
                    # Procesar cada codigo_interno
                    for codigo in df['codigo_interno'].unique():
                        df_codigo = df[df['codigo_interno'] == codigo]
                        
                        # Filtrar solo fechas válidas (fecha <= fecha_insercion)
                        df_codigo_valido = df_codigo[df_codigo['fecha'] <= df_codigo['fecha_insercion']]
                        
                        if df_codigo_valido.empty:
                            continue
                            
                        fechas_existentes = df_codigo_valido['fecha'].dt.date.unique()
                        
                        if len(fechas_existentes) > 0:
                            fecha_min = min(fechas_existentes)
                            fecha_max = max(fechas_existentes)
                            
                            # Crear rango completo de fechas
                            fechas_completas = pd.date_range(
                                start=fecha_min, 
                                end=fecha_max, 
                                freq='D'
                            ).date
                            
                            # Encontrar fechas faltantes
                            fechas_faltantes = [
                                fecha for fecha in fechas_completas 
                                if fecha not in fechas_existentes
                            ]
                            
                            if fechas_faltantes:
                                clave = f"{carpeta}_{os.path.basename(archivo_csv)}_{codigo}"
                                resultados[clave] = {
                                    'carpeta': carpeta,
                                    'archivo': os.path.basename(archivo_csv),
                                    'codigo_interno': codigo,
                                    'fechas_faltantes': fechas_faltantes,
                                    'total_faltantes': len(fechas_faltantes)
                                }
                
                except Exception as e:
                    print(f"Error procesando {archivo_csv}: {e}")
    
        # Mostrar advertencias sobre fechas futuras si las hay
        if fechas_futuras_encontradas:
            print(f"\n⚠️  ADVERTENCIA: Se encontraron {len(fechas_futuras_encontradas)} registros con fechas posteriores a fecha_insercion:")
            for registro in fechas_futuras_encontradas:
                print(f"   - {os.path.basename(registro['archivo'])} | {registro['codigo_interno']} | Fecha: {registro['fecha'].strftime('%Y-%m-%d %H:%M:%S')} | Inserción: {registro['fecha_insercion'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   (Estas fechas fueron excluidas del análisis)\n")
    
    # Crear DataFrame para exportar
    if resultados:
        datos_excel = []
        for clave, info in resultados.items():
            for fecha in info['fechas_faltantes']:
                datos_excel.append({
                    'Carpeta': info['carpeta'],
                    'Archivo': info['archivo'],
                    'Codigo_Interno': info['codigo_interno'],
                    'Fecha_Faltante': fecha,
                })
        
        df_resultado = pd.DataFrame(datos_excel)
        
        # Exportar a Excel con múltiples hojas
        nombre_archivo = f"dias_faltantes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
            # Hoja principal con días faltantes
            df_resultado.to_excel(writer, sheet_name='Días Faltantes', index=False)
            
            # Hoja adicional con fechas futuras si las hay
            if fechas_futuras_encontradas:
                datos_fechas_futuras = []
                for registro in fechas_futuras_encontradas:
                    datos_fechas_futuras.append({
                        'Carpeta': os.path.dirname(registro['archivo']).split(os.sep)[-1],
                        'Archivo': os.path.basename(registro['archivo']),
                        'Codigo_Interno': registro['codigo_interno'],
                        'Fecha': registro['fecha'],
                        'Fecha_Insercion': registro['fecha_insercion']
                    })
                
                df_fechas_futuras = pd.DataFrame(datos_fechas_futuras)
                df_fechas_futuras.to_excel(writer, sheet_name='Fechas Futuras', index=False)
        
        print(f"Archivo creado: {nombre_archivo}")
        
        # Mostrar resumen
        print(f"\nResumen:")
        print(f"Total de códigos con datos faltantes: {len(resultados)}")
        print(f"Total de días faltantes: {len(df_resultado)}")
        if fechas_futuras_encontradas:
            print(f"Total de registros con fechas futuras: {len(fechas_futuras_encontradas)} (ver hoja 'Fechas Futuras')")
        
    else:
        # Si no hay días faltantes pero sí fechas futuras, crear Excel solo con fechas futuras
        if fechas_futuras_encontradas:
            nombre_archivo = f"fechas_futuras_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            datos_fechas_futuras = []
            for registro in fechas_futuras_encontradas:
                datos_fechas_futuras.append({
                    'Carpeta': os.path.dirname(registro['archivo']).split(os.sep)[-1],
                    'Archivo': os.path.basename(registro['archivo']),
                    'Codigo_Interno': registro['codigo_interno'],
                    'Fecha': registro['fecha'],
                    'Fecha_Insercion': registro['fecha_insercion']
                })
            
            df_fechas_futuras = pd.DataFrame(datos_fechas_futuras)
            df_fechas_futuras.to_excel(nombre_archivo, index=False)
            print(f"Archivo creado: {nombre_archivo}")
            print(f"Total de registros con fechas futuras: {len(fechas_futuras_encontradas)}")
        else:
            print("No se encontraron datos faltantes ni fechas futuras")

if __name__ == "__main__":
    encontrar_dias_faltantes()