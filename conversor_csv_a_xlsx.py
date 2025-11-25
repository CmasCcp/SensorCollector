import pandas as pd
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class ConversorCSVaXLSX:
    def __init__(self, carpeta_origen='datos_unificados', carpeta_destino='datos_excel'):
        self.carpeta_origen = carpeta_origen
        self.carpeta_destino = carpeta_destino
        self.archivos_convertidos = []
        self.errores = []
        
        # Crear carpeta de destino
        os.makedirs(self.carpeta_destino, exist_ok=True)
        print(f"📁 Carpeta de destino creada: {self.carpeta_destino}")
    
    def obtener_archivos_csv(self):
        """Busca todos los archivos CSV en la carpeta origen"""
        archivos_csv = []
        
        if not os.path.exists(self.carpeta_origen):
            print(f"❌ Error: La carpeta {self.carpeta_origen} no existe")
            return archivos_csv
        
        for archivo in os.listdir(self.carpeta_origen):
            if archivo.lower().endswith('.csv'):
                ruta_completa = os.path.join(self.carpeta_origen, archivo)
                archivos_csv.append({
                    'nombre': archivo,
                    'ruta': ruta_completa,
                    'nombre_xlsx': archivo.replace('.csv', '.xlsx')
                })
        
        print(f"🔍 Encontrados {len(archivos_csv)} archivos CSV para convertir")
        return archivos_csv
    
    def convertir_csv_a_xlsx(self, info_archivo):
        """Convierte un archivo CSV individual a XLSX"""
        try:
            print(f"\n📄 Procesando: {info_archivo['nombre']}")
            
            # Leer CSV
            df = pd.read_csv(info_archivo['ruta'], encoding='utf-8')
            print(f"   📊 Leídos {len(df)} registros, {len(df.columns)} columnas")
            
            # Ruta de destino
            ruta_xlsx = os.path.join(self.carpeta_destino, info_archivo['nombre_xlsx'])
            
            # Convertir fechas si existen
            columnas_fecha = ['fecha', 'fecha_insercion']
            for col in columnas_fecha:
                if col in df.columns:
                    try:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                        print(f"   📅 Columna '{col}' convertida a fecha")
                    except:
                        print(f"   ⚠️ No se pudo convertir columna '{col}' a fecha")
            
            # Crear writer para Excel con opciones
            with pd.ExcelWriter(ruta_xlsx, engine='openpyxl') as writer:
                
                # Escribir datos principales
                df.to_excel(writer, sheet_name='Datos', index=False)
                
                # Crear hoja de resumen
                resumen_data = {
                    'Métrica': [
                        'Total de Registros',
                        'Total de Columnas', 
                        'Periodo de Datos',
                        'Archivo Original',
                        'Fecha de Conversión'
                    ],
                    'Valor': [
                        len(df),
                        len(df.columns),
                        self._obtener_periodo_datos(df),
                        info_archivo['nombre'],
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ]
                }
                
                df_resumen = pd.DataFrame(resumen_data)
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
                
                # Crear hoja de columnas
                columnas_info = {
                    'Columna': df.columns.tolist(),
                    'Tipo de Dato': [str(df[col].dtype) for col in df.columns],
                    'Valores Únicos': [df[col].nunique() for col in df.columns],
                    'Valores Nulos': [df[col].isnull().sum() for col in df.columns],
                    'Completitud %': [round((1 - df[col].isnull().sum() / len(df)) * 100, 2) for col in df.columns]
                }
                
                df_columnas = pd.DataFrame(columnas_info)
                df_columnas.to_excel(writer, sheet_name='Columnas', index=False)
            
            print(f"   ✅ Convertido exitosamente a: {info_archivo['nombre_xlsx']}")
            
            # Información del archivo creado
            tamano_mb = round(os.path.getsize(ruta_xlsx) / (1024*1024), 2)
            print(f"   📏 Tamaño: {tamano_mb} MB")
            
            return {
                'archivo_origen': info_archivo['nombre'],
                'archivo_destino': info_archivo['nombre_xlsx'],
                'registros': len(df),
                'columnas': len(df.columns),
                'tamano_mb': tamano_mb,
                'ruta_xlsx': ruta_xlsx,
                'estado': 'EXITOSO'
            }
            
        except Exception as e:
            error_msg = f"Error procesando {info_archivo['nombre']}: {str(e)}"
            print(f"   ❌ {error_msg}")
            
            return {
                'archivo_origen': info_archivo['nombre'],
                'error': error_msg,
                'estado': 'ERROR'
            }
    
    def _obtener_periodo_datos(self, df):
        """Obtiene el periodo de datos basado en columnas de fecha"""
        try:
            if 'fecha' in df.columns:
                fechas = pd.to_datetime(df['fecha'], errors='coerce')
                fecha_min = fechas.min()
                fecha_max = fechas.max()
                if pd.notna(fecha_min) and pd.notna(fecha_max):
                    return f"{fecha_min.date()} a {fecha_max.date()}"
            
            if 'fecha_insercion' in df.columns:
                fechas = pd.to_datetime(df['fecha_insercion'], errors='coerce')
                fecha_min = fechas.min()
                fecha_max = fechas.max()
                if pd.notna(fecha_min) and pd.notna(fecha_max):
                    return f"{fecha_min.date()} a {fecha_max.date()}"
            
            return "No disponible"
        except:
            return "Error al calcular"
    
    def convertir_todos(self):
        """Convierte todos los archivos CSV encontrados"""
        print("🚀 Iniciando conversión de archivos CSV a XLSX...\n")
        
        # Obtener archivos CSV
        archivos_csv = self.obtener_archivos_csv()
        
        if not archivos_csv:
            print("❌ No se encontraron archivos CSV para convertir")
            return
        
        resultados = []
        
        # Convertir cada archivo
        for info_archivo in archivos_csv:
            resultado = self.convertir_csv_a_xlsx(info_archivo)
            resultados.append(resultado)
            
            if resultado['estado'] == 'EXITOSO':
                self.archivos_convertidos.append(resultado)
            else:
                self.errores.append(resultado)
        
        # Generar reporte final
        self._generar_reporte_conversion(resultados)
        
        print(f"\n🎉 Conversión completada!")
        print(f"✅ Archivos convertidos exitosamente: {len(self.archivos_convertidos)}")
        print(f"❌ Errores: {len(self.errores)}")
        print(f"📁 Archivos XLSX guardados en: {os.path.abspath(self.carpeta_destino)}")
    
    def _generar_reporte_conversion(self, resultados):
        """Genera un reporte de la conversión"""
        try:
            ruta_reporte = os.path.join(self.carpeta_destino, 'reporte_conversion.txt')
            
            with open(ruta_reporte, 'w', encoding='utf-8') as f:
                f.write("REPORTE DE CONVERSIÓN CSV A XLSX\n")
                f.write("=" * 50 + "\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Carpeta origen: {self.carpeta_origen}\n")
                f.write(f"Carpeta destino: {self.carpeta_destino}\n\n")
                
                f.write("ARCHIVOS CONVERTIDOS EXITOSAMENTE:\n")
                f.write("-" * 40 + "\n")
                for resultado in self.archivos_convertidos:
                    f.write(f"• {resultado['archivo_origen']} → {resultado['archivo_destino']}\n")
                    f.write(f"  Registros: {resultado['registros']:,}\n")
                    f.write(f"  Columnas: {resultado['columnas']}\n")
                    f.write(f"  Tamaño: {resultado['tamano_mb']} MB\n\n")
                
                if self.errores:
                    f.write("\nERRORES:\n")
                    f.write("-" * 40 + "\n")
                    for error in self.errores:
                        f.write(f"• {error['archivo_origen']}: {error['error']}\n")
                
                f.write(f"\nRESUMEN:\n")
                f.write("-" * 40 + "\n")
                f.write(f"Total archivos procesados: {len(resultados)}\n")
                f.write(f"Convertidos exitosamente: {len(self.archivos_convertidos)}\n")
                f.write(f"Errores: {len(self.errores)}\n")
                
                if self.archivos_convertidos:
                    total_registros = sum(r['registros'] for r in self.archivos_convertidos)
                    total_tamano = sum(r['tamano_mb'] for r in self.archivos_convertidos)
                    f.write(f"Total registros convertidos: {total_registros:,}\n")
                    f.write(f"Tamaño total archivos XLSX: {total_tamano:.2f} MB\n")
            
            print(f"\n📋 Reporte de conversión guardado en: {ruta_reporte}")
            
        except Exception as e:
            print(f"⚠️ Error generando reporte: {e}")


# ===== EJECUCIÓN PRINCIPAL =====
if __name__ == "__main__":
    print("📊 Conversor de CSV a XLSX")
    print("=" * 40)
    
    # Crear instancia del conversor
    conversor = ConversorCSVaXLSX()
    
    # Ejecutar conversión
    conversor.convertir_todos()
    
    # Mostrar archivos creados
    if conversor.archivos_convertidos:
        print("\n📋 ARCHIVOS XLSX CREADOS:")
        for i, archivo in enumerate(conversor.archivos_convertidos, 1):
            print(f"{i}. {archivo['archivo_destino']} ({archivo['registros']:,} registros)")