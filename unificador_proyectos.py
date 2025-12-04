import pandas as pd
import os
import glob
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class UnificadorProyectos:
    def __init__(self, datos_folder='datos', output_folder='datos_unificados'):
        self.datos_folder = datos_folder
        self.output_folder = output_folder
        self.crear_carpeta_output()
    
    def crear_carpeta_output(self):
        """Crear carpeta de salida para datos unificados"""
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
            print(f"📁 Carpeta creada: {self.output_folder}")
        else:
            print(f"📁 Carpeta existente: {self.output_folder}")
    
    def escanear_proyectos(self):
        """Escanear y listar todos los proyectos disponibles"""
        proyectos = {}
        
        if not os.path.exists(self.datos_folder):
            print(f"❌ No se encuentra la carpeta: {self.datos_folder}")
            return proyectos
        
        for item in os.listdir(self.datos_folder):
            item_path = os.path.join(self.datos_folder, item)
            
            if os.path.isdir(item_path) and item.startswith('proyecto_'):
                proyecto_id = item.replace('proyecto_', '')
                proyectos[proyecto_id] = item_path
                print(f"🔍 Encontrado: Proyecto {proyecto_id}")
        
        return proyectos
    
    def leer_csvs_proyecto(self, proyecto_path, proyecto_id):
        """Leer todos los CSV de un proyecto específico"""
        todos_los_datos = []
        archivos_procesados = []
        
        print(f"\n📊 Procesando Proyecto {proyecto_id}...")
        
        # Recorrer estructura: proyecto/dispositivo/fecha/*.csv
        for dispositivo in os.listdir(proyecto_path):
            dispositivo_path = os.path.join(proyecto_path, dispositivo)
            
            if not os.path.isdir(dispositivo_path):
                continue
                
            print(f"  📱 Dispositivo: {dispositivo}")
            
            for fecha_carpeta in os.listdir(dispositivo_path):
                fecha_path = os.path.join(dispositivo_path, fecha_carpeta)
                
                if not os.path.isdir(fecha_path):
                    continue
                
                print(f"    📅 Fecha: {fecha_carpeta}")
                
                # Buscar archivos CSV en la carpeta de fecha
                patron_csv = os.path.join(fecha_path, "*.csv")
                archivos_csv = glob.glob(patron_csv)
                
                for archivo_csv in archivos_csv:
                    try:
                        # Leer CSV
                        df = pd.read_csv(archivo_csv)
                        
                        if df.empty:
                            continue
                        
                        # Agregar información de contexto
                        df['proyecto'] = proyecto_id
                        df['dispositivo'] = dispositivo
                        df['fecha_carpeta'] = fecha_carpeta
                        df['archivo_origen'] = os.path.basename(archivo_csv)
                        
                        todos_los_datos.append(df)
                        archivos_procesados.append({
                            'proyecto': proyecto_id,
                            'dispositivo': dispositivo,
                            'fecha': fecha_carpeta,
                            'archivo': os.path.basename(archivo_csv),
                            'registros': len(df),
                            'ruta': archivo_csv
                        })
                        
                        print(f"      📄 {os.path.basename(archivo_csv)} ({len(df)} registros)")
                        
                    except Exception as e:
                        print(f"    ⚠️ Error leyendo {archivo_csv}: {e}")
                        continue
        
        return todos_los_datos, archivos_procesados
    
    def unificar_proyecto(self, proyecto_id, proyecto_path):
        """Unificar todos los datos de un proyecto en un solo CSV"""
        # Leer todos los CSV del proyecto
        todos_los_datos, archivos_info = self.leer_csvs_proyecto(proyecto_path, proyecto_id)
        
        if not todos_los_datos:
            print(f"  ❌ No se encontraron datos para el Proyecto {proyecto_id}")
            return None
        
        # Concatenar todos los DataFrames
        print(f"  🔄 Unificando {len(todos_los_datos)} archivos...")
        df_unificado = pd.concat(todos_los_datos, ignore_index=True)
        
        # Ordenar por fecha de inserción y luego por fecha de medición
        columnas_ordenamiento = []
        if 'fecha_insercion' in df_unificado.columns:
            columnas_ordenamiento.append('fecha_insercion')
        if 'fecha' in df_unificado.columns:
            columnas_ordenamiento.append('fecha')
        
        if columnas_ordenamiento:
            # Crear una copia para ordenamiento sin modificar las columnas originales
            df_temp = df_unificado.copy()
            
            # Convertir fechas a datetime solo para ordenamiento
            for col in columnas_ordenamiento:
                df_temp[f'{col}_temp'] = pd.to_datetime(df_temp[col], errors='coerce')
            
            # Ordenar usando las columnas temporales
            columnas_temp = [f'{col}_temp' for col in columnas_ordenamiento]
            df_temp_sorted = df_temp.sort_values(columnas_temp, ascending=True)
            
            # Obtener el índice ordenado y aplicarlo al DataFrame original
            df_unificado = df_unificado.iloc[df_temp_sorted.index].reset_index(drop=True)
            
            print(f"    ✓ Datos ordenados por: {', '.join(columnas_ordenamiento)}")
        
        # Reorganizar columnas (poner las de contexto al final)
        columnas_contexto = ['proyecto', 'dispositivo', 'fecha_carpeta', 'archivo_origen']
        columnas_datos = [col for col in df_unificado.columns if col not in columnas_contexto]
        df_unificado = df_unificado[columnas_datos + columnas_contexto]
        
        # Guardar CSV unificado
        archivo_salida = os.path.join(self.output_folder, f"proyecto_{proyecto_id}_unificado.csv")
        df_unificado.to_csv(archivo_salida, index=False, encoding='utf-8-sig')
        
        # Generar reporte de resumen
        total_registros = len(df_unificado)
        total_archivos = len(archivos_info)
        dispositivos_unicos = df_unificado['dispositivo'].nunique()
        fechas_unicas = df_unificado['fecha_carpeta'].nunique()
        
        # Rango de fechas para el reporte
        fecha_inicio = fecha_final = "N/A"
        if 'fecha_insercion' in df_unificado.columns:
            # Convertir temporalmente para obtener el rango sin modificar los datos originales
            fechas_temp = pd.to_datetime(df_unificado['fecha_insercion'], errors='coerce').dropna()
            if not fechas_temp.empty:
                fecha_inicio = fechas_temp.min().strftime('%Y-%m-%d %H:%M:%S')
                fecha_final = fechas_temp.max().strftime('%Y-%m-%d %H:%M:%S')
        
        resumen = {
            'proyecto_id': proyecto_id,
            'archivo_salida': archivo_salida,
            'total_registros': total_registros,
            'total_archivos': total_archivos,
            'dispositivos': dispositivos_unicos,
            'fechas_carpetas': fechas_unicas,
            'fecha_inicio': fecha_inicio,
            'fecha_final': fecha_final,
            'archivos_detalle': archivos_info
        }
        
        print(f"  ✅ Unificado guardado: {os.path.basename(archivo_salida)}")
        print(f"     📊 {total_registros:,} registros de {total_archivos} archivos")
        print(f"     📱 {dispositivos_unicos} dispositivos en {fechas_unicas} fechas")
        print(f"     📅 Período: {fecha_inicio} → {fecha_final}")
        
        return resumen
    
    def generar_reporte_general(self, resumenes_proyectos):
        """Generar reporte general de la unificación"""
        if not resumenes_proyectos:
            print("❌ No hay datos para generar reporte")
            return
        
        print(f"\n📋 REPORTE GENERAL DE UNIFICACIÓN")
        print("=" * 60)
        
        total_archivos_generados = len(resumenes_proyectos)
        total_registros_globales = sum(r['total_registros'] for r in resumenes_proyectos)
        total_archivos_procesados = sum(r['total_archivos'] for r in resumenes_proyectos)
        
        print(f"🗂️  Proyectos procesados: {total_archivos_generados}")
        print(f"📊 Total registros unificados: {total_registros_globales:,}")
        print(f"📄 Total archivos CSV procesados: {total_archivos_procesados}")
        print(f"📁 Archivos unificados generados:")
        
        for i, resumen in enumerate(resumenes_proyectos, 1):
            print(f"  {i}. {os.path.basename(resumen['archivo_salida'])} ({resumen['total_registros']:,} registros)")
        
        print(f"\n📁 Ubicación: {os.path.abspath(self.output_folder)}")
        
        # Generar archivo de resumen detallado
        archivo_resumen = os.path.join(self.output_folder, "resumen_unificacion.txt")
        with open(archivo_resumen, 'w', encoding='utf-8') as f:
            f.write(f"REPORTE DE UNIFICACIÓN DE DATOS\n")
            f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            
            for resumen in resumenes_proyectos:
                f.write(f"PROYECTO {resumen['proyecto_id']}\n")
                f.write(f"Archivo: {os.path.basename(resumen['archivo_salida'])}\n")
                f.write(f"Registros: {resumen['total_registros']:,}\n")
                f.write(f"Archivos procesados: {resumen['total_archivos']}\n")
                f.write(f"Dispositivos: {resumen['dispositivos']}\n")
                f.write(f"Fechas: {resumen['fechas_carpetas']}\n")
                f.write(f"Período: {resumen['fecha_inicio']} → {resumen['fecha_final']}\n")
                f.write("\nArchivos detalle:\n")
                for archivo in resumen['archivos_detalle']:
                    f.write(f"  - {archivo['dispositivo']}/{archivo['fecha']}/{archivo['archivo']} ({archivo['registros']} registros)\n")
                f.write("\n" + "-" * 30 + "\n\n")
        
        print(f"📝 Reporte detallado: {os.path.basename(archivo_resumen)}")
    
    def ejecutar_unificacion(self):
        """Ejecutar el proceso completo de unificación"""
        print("🚀 INICIANDO UNIFICACIÓN DE DATOS POR PROYECTO")
        print("=" * 50)
        
        # Escanear proyectos disponibles
        proyectos = self.escanear_proyectos()
        
        if not proyectos:
            print("❌ No se encontraron proyectos para procesar")
            return []
        
        print(f"\n🎯 Se procesarán {len(proyectos)} proyectos")
        
        # Procesar cada proyecto
        resumenes = []
        for proyecto_id, proyecto_path in proyectos.items():
            resumen = self.unificar_proyecto(proyecto_id, proyecto_path)
            if resumen:
                resumenes.append(resumen)
        
        # Generar reporte general
        self.generar_reporte_general(resumenes)
        
        return resumenes


# ===== EJECUCIÓN PRINCIPAL =====
if __name__ == "__main__":
    print("📊 Iniciando unificación de datos por proyecto...")
    
    unificador = UnificadorProyectos()
    resultados = unificador.ejecutar_unificacion()
    
    if resultados:
        print(f"\n🎉 Proceso completado exitosamente!")
        print(f"✅ {len(resultados)} archivos CSV unificados generados")
    else:
        print(f"\n❌ No se generaron archivos unificados")