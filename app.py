from O365 import Account, FileSystemTokenBackend
import os
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import glob
import re

# ==== CONFIGURACIÓN ====
CLIENT_ID = 'b348e54d-583a-4bb7-9444-ba00b058d887'
CLIENT_SECRET = ''  # o deja en blanco si usas solo ID
LOCAL_FOLDER = 'datos'  # carpeta con tus CSVs locales
ONEDRIVE_FOLDER = 'DatosSensores'  # nombre de la carpeta destino en OneDrive
# API_URL = 'http://localhost:8084/listarUltimasMediciones?tabla=datos&disp.id_proyecto=1&limite=25&offset=0&disp.codigo_interno=EMMA-01&formato=csv'  # URL de tu API
# API_URL = 'http://api-sensores.cmasccp.cl/listarUltimasMediciones?tabla=datos&disp.id_proyecto=1&limite=25&offset=0&disp.codigo_interno=EMMA-01&formato=csv'  # URL de tu API
# ========================


def obtener_ultima_fecha_csv(codigo_interno, datos_folder):
    """
    Obtiene la última fecha de medición desde los archivos CSV existentes.
    
    Args:
        codigo_interno (str): Código interno del dispositivo (ej: AIRE-03)
        datos_folder (str): Carpeta donde están los archivos CSV
    
    Returns:
        str: Última fecha en formato YYYY-MM-DD o None si no hay datos
    """
    try:
        # Buscar archivos CSV que contengan el código interno
        patron = os.path.join(datos_folder, f"{codigo_interno}*.csv")
        archivos_csv = glob.glob(patron)
        
        if not archivos_csv:
            print(f"🔍 No se encontraron archivos CSV para {codigo_interno}")
            return None
        
        ultima_fecha = None
        
        for archivo in archivos_csv:
            try:
                df = pd.read_csv(archivo)
                
                # Buscar columnas que puedan contener fechas
                columnas_fecha = [col for col in df.columns if any(palabra in col.lower() 
                                for palabra in ['fecha_insercion'])]
                
                if columnas_fecha:
                    # Usar la primera columna de fecha encontrada
                    col_fecha = columnas_fecha[0]
                    print(col_fecha)
                    df[col_fecha] = pd.to_datetime(df[col_fecha], errors='coerce')
                    fecha_max = df[col_fecha].max()
                    
                    if pd.notna(fecha_max):
                        fecha_str = fecha_max.strftime('%Y-%m-%d')
                        if ultima_fecha is None or fecha_str > ultima_fecha:
                            ultima_fecha = fecha_str
            except Exception as e:
                print(f"⚠️  Error leyendo {archivo}: {e}")
                continue
        
        return ultima_fecha
    
    except Exception as e:
        print(f"❌ Error obteniendo última fecha para {codigo_interno}: {e}")
        return None


def obtener_datos_desde_api(config_path='config.json', output_folder=LOCAL_FOLDER):
    """
    Colector de datos que obtiene información desde una API basándose en la configuración.
    
    Args:
        config_path (str): Ruta al archivo de configuración JSON
        output_folder (str): Carpeta donde guardar los archivos CSV descargados
    
    Returns:
        list: Lista de archivos CSV creados
    """
    archivos_creados = []
    
    try:
        # Leer configuración
        with open(config_path, 'r', encoding='utf-8') as f:
            dispositivos = json.load(f)
        
        print(f"� Procesando {len(dispositivos)} dispositivos desde {config_path}")
        
        # Asegurar que existe el directorio de salida
        os.makedirs(output_folder, exist_ok=True)
        
        # Procesar cada dispositivo
        for i, dispositivo in enumerate(dispositivos):
            proyecto = dispositivo['proyecto']
            codigo_interno = dispositivo['codigo_interno']
            
            # Crear carpeta específica del proyecto
            proyecto_folder = os.path.join(output_folder, f"proyecto_{proyecto}")
            
            # Crear carpeta del dispositivo dentro del proyecto  
            dispositivo_folder = os.path.join(proyecto_folder, codigo_interno)
            os.makedirs(dispositivo_folder, exist_ok=True)
            
            print(f"\n🔄 [{i+1}/{len(dispositivos)}] Procesando {codigo_interno} (Proyecto {proyecto})...")
            print(f"📁 Carpeta de proyecto: {proyecto_folder}")
            print(f"🔧 Carpeta de dispositivo: {dispositivo_folder}")
            
            # Determinar fecha de inicio
            fecha_inicio = None
            
            # 1. Verificar si hay última fecha en config
            if 'ultima_fecha' in dispositivo:
                # Manejar ambos formatos de fecha (con y sin hora)
                fecha_str = dispositivo['ultima_fecha']
                try:
                    # Intentar formato con hora primero
                    ultima_fecha = datetime.strptime(fecha_str, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    # Si falla, usar formato solo fecha
                    ultima_fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
                fecha_inicio = (ultima_fecha).strftime('%Y-%m-%d')
                # fecha_inicio = (ultima_fecha + timedelta(days=1)).strftime('%Y-%m-%d')
                print(f"📅 Última fecha en config: {dispositivo['ultima_fecha']}")
                print(f"📅 Iniciando desde el día siguiente: {fecha_inicio}")
            else:
                # 2. Buscar última fecha en archivos CSV existentes en la carpeta del dispositivo
                ultima_fecha_csv = obtener_ultima_fecha_csv(codigo_interno, dispositivo_folder)
                if ultima_fecha_csv:
                    # Manejar ambos formatos de fecha (con y sin hora)
                    try:
                        # Intentar formato con hora primero
                        ultima_fecha = datetime.strptime(ultima_fecha_csv, '%Y-%m-%dT%H:%M:%S')
                    except ValueError:
                        # Si falla, usar formato solo fecha
                        ultima_fecha = datetime.strptime(ultima_fecha_csv, '%Y-%m-%d')
                    fecha_inicio = (ultima_fecha + timedelta(days=1)).strftime('%Y-%m-%d')
                    print(f"📅 Última fecha encontrada en CSV: {ultima_fecha_csv}")
                    print(f"📅 Iniciando desde el día siguiente: {fecha_inicio}")
                else:
                    # 3. Si no hay datos, usar fecha específica: 2025-10-23
                    fecha_inicio = '2005-10-23'
                    print(f"📅 No hay datos previos, iniciando desde: {fecha_inicio}")
            
            # Crear carpeta específica para esta fecha de inicio
            fecha_folder = os.path.join(dispositivo_folder, fecha_inicio)
            os.makedirs(fecha_folder, exist_ok=True)
            print(f"📅 Carpeta de fecha: {fecha_folder}")

            # Descargar datos en paquetes de 100 registros (para evitar timeouts)
            limite = 100
            offset = 0
            total_registros = 0
            datos_completos = []
            ultima_fecha_procesada = None
            max_paquetes = 50  # Límite de seguridad para evitar loops infinitos
            paquetes_procesados = 0
            
            try:
                print(f"📡 Descargando datos para {codigo_interno} en paquetes de {limite} registros...")
                
                headers = {
                    'Accept': 'text/csv',
                }
                
                # Descargar datos en paquetes hasta que no haya más
                while True:
                    paquetes_procesados += 1
                    
                    # Verificar límite de seguridad
                    if paquetes_procesados > max_paquetes:
                        print(f"⚠️  Alcanzado límite de seguridad de {max_paquetes} paquetes")
                        break
                    # Construir URL de la API - verificar si hay URL personalizada en config
                    if 'api_url' in dispositivo and dispositivo['api_url']:
                        # Usar la URL personalizada del dispositivo
                        api_base_url = dispositivo['api_url']
                        print(f"🔧 Usando URL personalizada: {api_base_url}")
                        api_url = f"{api_base_url}?tabla=datos&order_by=fecha_insercion&disp.id_proyecto={proyecto}&limite={limite}&offset={offset}&disp.codigo_interno={codigo_interno}&fecha_inicio={fecha_inicio}&formato=csv"
                    else:
                        # Usar la URL por defecto
                        api_base_url = "https://api-sensores.cmasccp.cl/listarUltimasMediciones"
                        print(f"🔧 Usando URL por defecto: {api_base_url}")
                        api_url = f"{api_base_url}?tabla=datos&order_by=fecha_insercion&disp.id_proyecto={proyecto}&limite={limite}&offset={offset}&disp.codigo_interno={codigo_interno}&fecha_inicio={fecha_inicio}&formato=csv"
                    
                    print(f"📦 Paquete {offset//limite + 1}: Descargando registros {offset + 1} al {offset + limite}")
                    print(f"🔗 URL: {api_url}")
                    
                    response = requests.get(api_url, headers=headers, timeout=180)
                    print(f"📡 Respuesta HTTP: {response.status_code}")
                    
                    # Agregar más información sobre la respuesta
                    if response.status_code != 200:
                        print(f"❌ Error HTTP {response.status_code}: {response.reason}")
                        print(f"📄 Contenido de error: {response.text[:500]}")  # Primeros 500 caracteres
                        # Para ciertos errores, intentar continuar con el siguiente paquete
                        if response.status_code in [404, 524]:  # Not Found o Gateway Timeout
                            print(f"⚠️  Saltando paquete debido a error {response.status_code}")
                            offset += limite
                            if offset > limite * 10:  # Evitar loops infinitos
                                print(f"❌ Demasiados errores consecutivos, deteniéndose")
                                break
                            continue
                        else:
                            response.raise_for_status()
                    
                    # Verificar que tenemos contenido CSV
                    response_text = response.text.strip()
                    print(f"📄 Contenido recibido: {len(response_text)} caracteres")
                    
                    if not response_text:
                        print(f"📭 No hay más datos disponibles (respuesta vacía)")
                        break
                    
                    # Mostrar primeras líneas para debug
                    primeras_lineas = '\n'.join(response_text.split('\n')[:3])
                    print(f"🔍 Primeras líneas:\n{primeras_lineas}")
                    
                    # Leer CSV directamente desde la respuesta
                    from io import StringIO
                    try:
                        df_paquete = pd.read_csv(StringIO(response_text))
                        print(f"📊 DataFrame creado: {len(df_paquete)} filas, {len(df_paquete.columns)} columnas")
                        if not df_paquete.empty:
                            print(f"🏷️  Columnas: {list(df_paquete.columns)}")
                    except Exception as csv_error:
                        print(f"❌ Error leyendo CSV en paquete {paquetes_procesados}: {csv_error}")
                        print(f"📄 Contenido completo:\n{response_text}")
                        
                        # Si es un error de CSV, intentar continuar con el siguiente paquete
                        if "Expected" in str(csv_error) or "could not convert" in str(csv_error):
                            print(f"⚠️  Error de formato CSV, saltando al siguiente paquete")
                            offset += limite
                            if paquetes_procesados > 5:  # Evitar demasiados errores
                                print(f"❌ Demasiados errores de CSV, deteniéndose")
                                break
                            continue
                        else:
                            break
                    
                    # Si el paquete está vacío, no hay más datos
                    if df_paquete.empty:
                        print(f"📭 Paquete vacío, fin de datos")
                        break
                    
                    # Para el endpoint listarUltimasMediciones, procesar todos los datos sin filtrar por fecha
                    # ya que está diseñado para traer las últimas mediciones disponibles
                    print(f"� Procesando todos los {len(df_paquete)} registros del paquete")
                    
                    # Si existe columna de fecha_insercion, actualizar la última fecha procesada
                    if 'fecha_insercion' in df_paquete.columns:
                        col_fecha = 'fecha_insercion'
                        df_paquete[col_fecha] = pd.to_datetime(df_paquete[col_fecha], errors='coerce')
                        
                        # Mostrar rango de fechas para información
                        fecha_min = df_paquete[col_fecha].min()
                        fecha_max = df_paquete[col_fecha].max()
                        print(f"🗓️  Rango de fechas en paquete: {fecha_min} a {fecha_max}")
                        
                        # Actualizar la última fecha procesada
                        ultima_fecha_paquete = df_paquete[col_fecha].max()
                        if pd.notna(ultima_fecha_paquete):
                            fecha_str = ultima_fecha_paquete.strftime('%Y-%m-%dT%H:%M:%S')
                            if ultima_fecha_procesada is None or fecha_str > ultima_fecha_procesada:
                                ultima_fecha_procesada = fecha_str
                                print(f"📅 Última fecha actualizada: {ultima_fecha_procesada}")
                    
                    # Guardar inmediatamente cada paquete como archivo CSV
                    paquete_num = offset//limite + 1
                    
                    # Usar la fecha_insercion de los datos para el nombre del archivo
                    if 'fecha_insercion' in df_paquete.columns:
                        col_fecha = 'fecha_insercion'
                        # Si ya se procesó la fecha anteriormente, usar esa columna
                        if col_fecha in df_paquete.columns and pd.api.types.is_datetime64_any_dtype(df_paquete[col_fecha]):
                            fecha_datos = df_paquete[col_fecha].max()
                        else:
                            # Convertir la fecha si no se ha hecho aún
                            df_temp = df_paquete.copy()
                            df_temp[col_fecha] = pd.to_datetime(df_temp[col_fecha], errors='coerce')
                            fecha_datos = df_temp[col_fecha].max()
                        
                        if pd.notna(fecha_datos):
                            fecha_str = fecha_datos.strftime("%Y%m%d")
                            filename = f"{codigo_interno}_paquete_{paquete_num:03d}_{fecha_str}.csv"
                        else:
                            # Si no se puede obtener la fecha, usar timestamp actual como fallback
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"{codigo_interno}_paquete_{paquete_num:03d}_{timestamp}.csv"
                    else:
                        # Si no hay columna de fecha, usar timestamp actual
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"{codigo_interno}_paquete_{paquete_num:03d}_{timestamp}.csv"
                    
                    filepath = os.path.join(fecha_folder, filename)
                    
                    df_paquete.to_csv(filepath, index=False, encoding='utf-8')
                    archivos_creados.append(filename)
                    
                    # Agregar datos al conjunto completo para estadísticas
                    datos_completos.append(df_paquete)
                    total_registros += len(df_paquete)
                    
                    print(f"💾 Paquete guardado: {filename} ({len(df_paquete)} registros)")
                    
                    # Si el paquete tiene menos registros que el límite, es el último
                    if len(df_paquete) < limite:
                        print(f"📭 Último paquete recibido (menos de {limite} registros)")
                        break
                    elif len(df_paquete) == limite:
                        print(f"🔄 Paquete completo ({limite} registros), continuando con siguiente paquete...")
                    
                    # Preparar para el siguiente paquete
                    offset += limite
                    print(f"➡️  Preparando paquete siguiente: offset = {offset}")
                    
                    # Agregar una pequeña pausa para evitar saturar la API
                    import time
                    time.sleep(1)
                
                # Si no se descargaron datos, continuar con el siguiente dispositivo
                if not datos_completos:
                    print(f"ℹ️  No hay nuevos datos para {codigo_interno}")
                    continue
                
                print(f"📊 Resumen para {codigo_interno}: {len(archivos_creados)} archivos, {total_registros} registros total")
                
                # Actualizar última fecha en la configuración
                if ultima_fecha_procesada:
                    dispositivo['ultima_fecha'] = ultima_fecha_procesada
                    print(f"📅 Configuración actualizada: última fecha = {ultima_fecha_procesada}")
                else:
                    print(f"⚠️  No se pudo determinar la última fecha para {codigo_interno}")
                
            except requests.RequestException as e:
                print(f"❌ Error de API para {codigo_interno}: {e}")
                continue
            except Exception as e:
                print(f"❌ Error procesando {codigo_interno}: {e}")
                continue
        
        # Guardar configuración actualizada
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(dispositivos, f, indent=4, ensure_ascii=False)
        print(f"\n💾 Configuración actualizada en {config_path}")
        
        print(f"\n✅ Colección completada: {len(archivos_creados)} archivos creados")
        return archivos_creados
        
    except FileNotFoundError:
        print(f"❌ No se encontró el archivo de configuración: {config_path}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Error leyendo JSON de configuración: {e}")
        return []
    except Exception as e:
        print(f"❌ Error general en colector: {e}")
        return []


def subir_archivos_a_onedrive(local_folder=LOCAL_FOLDER, onedrive_folder=ONEDRIVE_FOLDER):
    """
    Función para subir archivos CSV desde una carpeta local a OneDrive.
    
    Args:
        local_folder (str): Carpeta local con archivos CSV
        onedrive_folder (str): Nombre de la carpeta destino en OneDrive
    
    Returns:
        bool: True si la sincronización fue exitosa, False en caso contrario
    """
    try:
        print(f"☁️  Iniciando sincronización con OneDrive...")
        
        # Configurar credenciales y autenticación
        credentials = (CLIENT_ID, CLIENT_SECRET)
        token_backend = FileSystemTokenBackend(token_path='.', token_filename='token.txt')
        account = Account(credentials, token_backend=token_backend)
        
        # Autenticación inicial (solo la primera vez abrirá un link en el navegador)
        if not account.is_authenticated:
            account.authenticate(scopes=['offline_access', 'Files.ReadWrite.All'])
        
        # Obtener acceso a OneDrive
        storage = account.storage()
        onedrive = storage.get_default_drive()
        root_folder = onedrive.get_item_by_path(onedrive_folder)
        
        # Crear carpeta si no existe
        if root_folder is None:
            root_folder = onedrive.create_folder(onedrive_folder)
            print(f"📁 Carpeta '{onedrive_folder}' creada en OneDrive")
        
        # Verificar que existe la carpeta local
        if not os.path.exists(local_folder):
            print(f"❌ La carpeta local '{local_folder}' no existe")
            return False
        
        # Subir archivos CSV
        archivos_subidos = 0
        for file_name in os.listdir(local_folder):
            if file_name.lower().endswith('.csv'):
                local_path = os.path.join(local_folder, file_name)
                print(f'📤 Subiendo: {file_name} ...')
                root_folder.upload_file(local_path, conflict_behavior='replace')
                archivos_subidos += 1
        
        print(f"✅ Sincronización completada: {archivos_subidos} archivos subidos")
        print(f"🕒 Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except Exception as e:
        print(f"❌ Error durante la sincronización: {e}")
        return False


def main():
    """Función principal que ejecuta el colector de datos."""
    print("🚀 Iniciando colector de datos de sensores")
    print("=" * 50)
    
    # Obtener datos desde la API y guardar localmente
    archivos_descargados = obtener_datos_desde_api()
    
    if archivos_descargados:
        print(f"\n🎉 Colección completada exitosamente")
        print(f"📁 {len(archivos_descargados)} archivos guardados en: {LOCAL_FOLDER}")
        print("📋 Archivos creados:")
        for archivo in archivos_descargados:
            print(f"   • {archivo}")
    else:
        print("\n ℹ️  No se crearon nuevos archivos")
        print("   (Todos los dispositivos ya están actualizados o no hay datos nuevos)")


if __name__ == "__main__":
    main()
