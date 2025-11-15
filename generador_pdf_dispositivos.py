import pandas as pd
import os
import glob
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
import warnings
warnings.filterwarnings('ignore')

class GeneradorPDFDispositivos:
    def __init__(self, datos_folder='datos'):
        self.datos_folder = datos_folder
        self.pdfs_folder = 'reportes_pdf_dispositivos'
        
        # Columnas a ignorar en las tablas
        # self.columns_to_ignore = [
        #     'Carpeta',
        #     'Archivo',
        #     'archivo_origen',
        #     'fecha_carpeta',
        #     'dispositivo',
        #     'proyecto'
        # ]

        self.columns_to_ignore = ["id_sesion","sesion_descripcion", "fecha_inicio", "ubicacion", "dispositivo_descripcion", "Carpeta", "Archivo", "fecha_insercion_dt"]
        self.non_variable_columns = ["fecha","fecha_insercion","id_proyecto","codigo_interno","id_sesion","sesion_descripcion", "fecha_inicio", "ubicacion", "dispositivo_descripcion", "Carpeta", "Archivo", "fecha_insercion_dt"] 
        
        self.crear_carpeta_pdfs()
        self.styles = getSampleStyleSheet()
        self.configurar_estilos()
        
    def crear_carpeta_pdfs(self):
        """Crear carpeta para guardar los PDFs"""
        os.makedirs(self.pdfs_folder, exist_ok=True)
        print(f"📁 Carpeta de PDFs creada: {self.pdfs_folder}")
    
    def configurar_estilos(self):
        """Configurar estilos personalizados para el PDF"""
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.darkblue,
            alignment=1  # Centro
        )
        
        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=15,
            textColor=colors.darkgreen,
            alignment=1  # Centro
        )
        
        self.info_style = ParagraphStyle(
            'InfoStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=10,
            textColor=colors.black,
            alignment=1  # Centro
        )
        
        self.header_style = ParagraphStyle(
            'HeaderStyle',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.whitesmoke,
            alignment=1,  # Centro
            fontName='Helvetica-Bold',
            leading=10  # Espaciado entre líneas
        )
        
        self.cell_style = ParagraphStyle(
            'CellStyle',
            parent=self.styles['Normal'],
            fontSize=7,
            textColor=colors.black,
            alignment=1,  # Centro
            fontName='Helvetica',
            leading=9  # Espaciado entre líneas
        )
    
    def escanear_estructura(self):
        """Escanea la estructura de carpetas proyecto/dispositivo/fecha"""
        estructura = {}
        
        if not os.path.exists(self.datos_folder):
            print(f"❌ No existe la carpeta: {self.datos_folder}")
            return estructura
            
        # Buscar proyectos (proyecto_X)
        for proyecto_folder in glob.glob(os.path.join(self.datos_folder, "proyecto_*")):
            proyecto_nombre = os.path.basename(proyecto_folder)
            proyecto_id = proyecto_nombre.replace("proyecto_", "")
            
            estructura[proyecto_id] = {}
            
            # Buscar dispositivos dentro del proyecto
            for dispositivo_folder in glob.glob(os.path.join(proyecto_folder, "*")):
                if os.path.isdir(dispositivo_folder):
                    dispositivo_nombre = os.path.basename(dispositivo_folder)
                    estructura[proyecto_id][dispositivo_nombre] = {}
                    
                    # Buscar carpetas de fechas dentro del dispositivo
                    for fecha_folder in glob.glob(os.path.join(dispositivo_folder, "*")):
                        if os.path.isdir(fecha_folder):
                            fecha_nombre = os.path.basename(fecha_folder)
                            
                            # Buscar archivos CSV en la carpeta de fecha
                            archivos_csv = glob.glob(os.path.join(fecha_folder, "*.csv"))
                            estructura[proyecto_id][dispositivo_nombre][fecha_nombre] = archivos_csv
        
        return estructura
    
    def leer_datos_dispositivo(self, proyecto_id, dispositivo_nombre, fechas_datos):
        """Lee todos los datos CSV de un dispositivo y los combina"""
        todos_los_datos = []
        archivos_procesados = []
        info_archivos = []
        
        for fecha, archivos in fechas_datos.items():
            for archivo in archivos:
                try:
                    df = pd.read_csv(archivo)
                    
                    # Agregar información de contexto
                    df['Carpeta'] = fecha
                    df['Archivo'] = os.path.basename(archivo)
                    
                    todos_los_datos.append(df)
                    archivos_procesados.append(archivo)
                    info_archivos.append({
                        'archivo': os.path.basename(archivo),
                        'fecha_carpeta': fecha,
                        'registros': len(df)
                    })
                    
                    print(f"📄 Leído: {os.path.basename(archivo)} ({len(df)} registros)")
                    
                except Exception as e:
                    print(f"⚠️ Error leyendo {archivo}: {e}")
                    continue
        
        if todos_los_datos:
            df_completo = pd.concat(todos_los_datos, ignore_index=True)
            return df_completo, info_archivos
        else:
            return pd.DataFrame(), []
    
    def formatear_datos_para_tabla(self, df):
        """Formatea los datos para mostrar mejor en el PDF"""
        df_display = df.copy()
        
        # Calcular diferencias de tiempo ANTES del filtrado
        if 'fecha_insercion' in df_display.columns:
            try:
                # Convertir fecha_insercion a datetime para cálculos
                df_display['fecha_insercion_dt'] = pd.to_datetime(df_display['fecha_insercion'], errors='coerce')
                # Ordenar por fecha_insercion para cálculo correcto
                df_display = df_display.sort_values('fecha_insercion_dt').reset_index(drop=True)
                
                # Calcular diferencia en minutos con la fila anterior
                df_display['diff_insercion_anterior'] = df_display['fecha_insercion_dt'].diff()
                df_display['⏰ Min. Dif. Inserción'] = df_display['diff_insercion_anterior'].dt.total_seconds() / 60
                
                # Formatear la columna de diferencia
                df_display['⏰ Min. Dif. Inserción'] = df_display['⏰ Min. Dif. Inserción'].apply(
                    lambda x: 'Primera' if pd.isna(x) else f"{x:.1f}"
                )
                
                print(f"✅ Columna de diferencia temporal fecha_insercion agregada")
                
            except Exception as e:
                print(f"⚠️ Error calculando diferencias temporales fecha_insercion: {e}")
                df_display['⏰ Min. Dif. Inserción'] = 'N/A'
        else:
            df_display['⏰ Min. Dif. Inserción'] = 'N/A'
        
        # Calcular diferencias para fecha de medición
        if 'fecha' in df_display.columns:
            try:
                # Convertir fecha a datetime para cálculos
                df_display['fecha_dt'] = pd.to_datetime(df_display['fecha'], errors='coerce')
                # Ya está ordenado por fecha_insercion, pero calculamos diff para fecha
                
                # Calcular diferencia en minutos con la fila anterior
                df_display['diff_fecha_anterior'] = df_display['fecha_dt'].diff()
                df_display['📊 Min. Dif. Medicion'] = df_display['diff_fecha_anterior'].dt.total_seconds() / 60
                
                # Formatear la columna de diferencia
                df_display['📊 Min. Dif. Medicion'] = df_display['📊 Min. Dif. Medicion'].apply(
                    lambda x: 'Primera' if pd.isna(x) else f"{x:.1f}"
                )
                
                print(f"✅ Columna de diferencia temporal fecha agregada")
                
            except Exception as e:
                print(f"⚠️ Error calculando diferencias temporales fecha: {e}")
                df_display['📊 Min. Dif. Medicion'] = 'N/A'
        else:
            df_display['📊 Min. Dif. Medicion'] = 'N/A'
        
        # Calcular diferencias para fecha de medición
        if 'fecha' in df_display.columns:
            try:
                # Convertir fecha a datetime para cálculos
                df_display['fecha_dt'] = pd.to_datetime(df_display['fecha'], errors='coerce')
                # Ya está ordenado por fecha_insercion, pero calculamos diff para fecha
                
                # Calcular diferencia en minutos con la fila anterior
                df_display['diff_fecha_anterior'] = df_display['fecha_dt'].diff()
                df_display['📊 Min. Dif. Medicion'] = df_display['diff_fecha_anterior'].dt.total_seconds() / 60
                
                # Formatear la columna de diferencia
                df_display['📊 Min. Dif. Medicion'] = df_display['📊 Min. Dif. Medicion'].apply(
                    lambda x: 'Primera' if pd.isna(x) else f"{x:.1f}"
                )
                
                print(f"✅ Columna de diferencia temporal fecha agregada")
                
            except Exception as e:
                print(f"⚠️ Error calculando diferencias temporales fecha: {e}")
                df_display['📊 Min. Dif. Medicion'] = 'N/A'
        else:
            df_display['📊 Min. Dif. Medicion'] = 'N/A'
        
        # Filtrar columnas no deseadas (agregamos las columnas auxiliares)
        columnas_auxiliares = ['fecha_insercion_dt', 'diff_insercion_anterior', 'fecha_dt', 'diff_fecha_anterior']
        columnas_a_mostrar = [col for col in df_display.columns 
                             if col not in self.columns_to_ignore + columnas_auxiliares]
        df_display = df_display[columnas_a_mostrar]
        
        print(f"🔍 Columnas filtradas: {len(df.columns)} → {len(df_display.columns)}")
        print(f"📋 Columnas mostradas: {list(df_display.columns)}")
        
        # Formatear fechas
        for col in df_display.columns:
            if 'fecha' in col.lower():
                try:
                    df_display[col] = pd.to_datetime(df_display[col], errors='coerce')
                    df_display[col] = df_display[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                    # Limpiar valores NaT
                    df_display[col] = df_display[col].fillna('N/A')
                except:
                    pass
        
        # Limitar longitud de texto
        for col in df_display.select_dtypes(include=['object']).columns:
            df_display[col] = df_display[col].astype(str).apply(
                lambda x: x[:25] + '...' if len(x) > 25 else x
            )
        
        # Reemplazar NaN con valores más legibles
        df_display = df_display.fillna('N/A')
        
        return df_display
    
    def crear_header_con_wrap(self, texto, max_chars=15):
        """Crea un Paragraph para headers que permite wrap de texto"""
        # Si el texto es corto, devolverlo tal como está
        if len(texto) <= max_chars:
            return Paragraph(f"<b>{texto}</b>", self.header_style)
        
        # Si es largo, insertar saltos de línea estratégicos
        palabras = texto.split('_')  # Dividir por underscores comunes en CSV
        if len(palabras) > 1:
            # Reagrupar palabras para que no excedan max_chars por línea
            lineas = []
            linea_actual = []
            longitud_actual = 0
            
            for palabra in palabras:
                if longitud_actual + len(palabra) + 1 <= max_chars:  # +1 por el underscore
                    linea_actual.append(palabra)
                    longitud_actual += len(palabra) + 1
                else:
                    if linea_actual:
                        lineas.append('_'.join(linea_actual))
                    linea_actual = [palabra]
                    longitud_actual = len(palabra)
            
            if linea_actual:
                lineas.append('_'.join(linea_actual))
            
            texto_wrapped = '<br/>'.join(lineas)
        else:
            # Si no hay underscores, dividir por caracteres
            texto_wrapped = '<br/>'.join([texto[i:i+max_chars] for i in range(0, len(texto), max_chars)])
        
        return Paragraph(f"<b>{texto_wrapped}</b>", self.header_style)
    
    def crear_celda_con_wrap(self, texto, max_chars=20):
        """Crea un Paragraph para celdas de datos que permite wrap de texto"""
        texto_str = str(texto)
        
        # Si el texto es corto, devolverlo tal como está
        if len(texto_str) <= max_chars:
            return Paragraph(texto_str, self.cell_style)
        
        # Si es largo, insertar saltos de línea
        # Primero intentar dividir por espacios o guiones
        if ' ' in texto_str or '-' in texto_str or '_' in texto_str:
            # Dividir por separadores naturales
            separadores = [' ', '-', '_']
            mejor_division = texto_str
            
            for sep in separadores:
                if sep in texto_str:
                    partes = texto_str.split(sep)
                    lineas = []
                    linea_actual = []
                    longitud_actual = 0
                    
                    for parte in partes:
                        if longitud_actual + len(parte) + 1 <= max_chars:
                            linea_actual.append(parte)
                            longitud_actual += len(parte) + 1
                        else:
                            if linea_actual:
                                lineas.append(sep.join(linea_actual))
                            linea_actual = [parte]
                            longitud_actual = len(parte)
                    
                    if linea_actual:
                        lineas.append(sep.join(linea_actual))
                    
                    if len(max(lineas, key=len)) < len(mejor_division):
                        mejor_division = '<br/>'.join(lineas)
                    break
            
            texto_wrapped = mejor_division
        else:
            # Si no hay separadores naturales, dividir por caracteres
            texto_wrapped = '<br/>'.join([texto_str[i:i+max_chars] for i in range(0, len(texto_str), max_chars)])
        
        return Paragraph(texto_wrapped, self.cell_style)
    
    def crear_tabla_pdf(self, df, ancho_disponible):
        """Crea una tabla ReportLab a partir del DataFrame"""
        if df.empty:
            return None
        
        # Identificar las columnas de diferencia temporal
        col_diferencia_insercion = '⏰ Min. Dif. Inserción'
        col_diferencia_medicion = '📊 Min. Dif. Medicion'
        idx_col_diferencia_insercion = None
        idx_col_diferencia_medicion = None
        
        # Preparar headers con wrap
        headers_originales = list(df.columns)
        headers_con_wrap = []
        
        for i, header in enumerate(headers_originales):
            if header == col_diferencia_insercion:
                idx_col_diferencia_insercion = i
                # Header especial para la columna de diferencia inserción
                header_style_especial = ParagraphStyle(
                    'HeaderDiferenciaInsercion',
                    parent=self.header_style,
                    textColor=colors.white,
                    fontSize=8,
                    fontName='Helvetica-Bold',
                    leading=10,
                    alignment=1
                )
                headers_con_wrap.append(Paragraph(f"<b>{header}</b>", header_style_especial))
            elif header == col_diferencia_medicion:
                idx_col_diferencia_medicion = i
                # Header especial para la columna de diferencia medición
                header_style_especial = ParagraphStyle(
                    'HeaderDiferenciaMedicion',
                    parent=self.header_style,
                    textColor=colors.white,
                    fontSize=8,
                    fontName='Helvetica-Bold',
                    leading=10,
                    alignment=1
                )
                headers_con_wrap.append(Paragraph(f"<b>{header}</b>", header_style_especial))
            else:
                headers_con_wrap.append(self.crear_header_con_wrap(header))
        
        data = [headers_con_wrap]  # Primera fila: headers con wrap
        
        # Agregar filas de datos con wrap
        for _, row in df.iterrows():
            fila_con_wrap = []
            for i, val in enumerate(row):
                if i == idx_col_diferencia_insercion:
                    # Celda especial para la columna de diferencia inserción (verde)
                    cell_style_especial = ParagraphStyle(
                        'CellDiferenciaInsercion',
                        parent=self.cell_style,
                        textColor=colors.darkgreen,
                        fontSize=7,
                        fontName='Helvetica-Bold',
                        leading=9,
                        alignment=1
                    )
                    fila_con_wrap.append(Paragraph(str(val), cell_style_especial))
                elif i == idx_col_diferencia_medicion:
                    # Celda especial para la columna de diferencia medición (azul)
                    cell_style_especial = ParagraphStyle(
                        'CellDiferenciaMedicion',
                        parent=self.cell_style,
                        textColor=colors.darkblue,
                        fontSize=7,
                        fontName='Helvetica-Bold',
                        leading=9,
                        alignment=1
                    )
                    fila_con_wrap.append(Paragraph(str(val), cell_style_especial))
                else:
                    fila_con_wrap.append(self.crear_celda_con_wrap(str(val)))
            data.append(fila_con_wrap)
        
        # Calcular ancho de columnas dinámicamente
        num_cols = len(headers_originales)
        col_width = ancho_disponible / num_cols
        
        # Crear tabla
        table = Table(data, colWidths=[col_width] * num_cols)
        
        # Aplicar estilos
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),  # Centrado vertical para headers
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),  # Centrado vertical para datos
            
            # Data rows style - removido porque ahora son Paragraphs
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            
            # Altura mínima para headers (permite wrap)
            ('ROWBACKGROUNDS', (0, 0), (-1, 0), [colors.navy]),
            ('MINHEIGHT', (0, 0), (-1, 0), 25),  # Altura mínima para headers
            ('MINHEIGHT', (0, 1), (-1, -1), 18), # Altura mínima para datos
        ]))
        
        return table
    
    def calcular_estadisticas_descriptivas(self, df):
        """Calcula estadísticas descriptivas para columnas numéricas"""
        # Filtrar columnas numéricas que no están en non_variable_columns
        columnas_numericas = []
        
        for col in df.columns:
            if col not in self.non_variable_columns:
                # Verificar si la columna es numérica
                try:
                    pd.to_numeric(df[col], errors='raise')
                    columnas_numericas.append(col)
                except:
                    continue
        
        if not columnas_numericas:
            return None
        
        # Calcular estadísticas
        estadisticas = []
        
        for col in columnas_numericas:
            datos_numericos = pd.to_numeric(df[col], errors='coerce')
            datos_validos = datos_numericos.dropna()
            
            if len(datos_validos) == 0:
                continue
                
            stats = {
                'Variable': col,
                'Media': f"{datos_validos.mean():.4f}",
                'Mediana': f"{datos_validos.median():.4f}",
                'Moda': f"{datos_validos.mode().iloc[0]:.4f}" if len(datos_validos.mode()) > 0 else "N/A",
                'Desv. Estándar': f"{datos_validos.std():.4f}",
                'Varianza': f"{datos_validos.var():.4f}",
                'Mínimo': f"{datos_validos.min():.4f}",
                'Máximo': f"{datos_validos.max():.4f}",
                'Q1': f"{datos_validos.quantile(0.25):.4f}",
                'Q3': f"{datos_validos.quantile(0.75):.4f}",
                'Valores válidos': f"{len(datos_validos)}"
            }
            estadisticas.append(stats)
        
        return estadisticas
    
    def calcular_metricas_calidad(self, df):
        """Calcula métricas de calidad y aceptabilidad de datos"""
        if df.empty:
            return None
        
        # Filtrar columnas numéricas que no están en non_variable_columns
        columnas_numericas = []
        
        for col in df.columns:
            if col not in self.non_variable_columns:
                try:
                    pd.to_numeric(df[col], errors='raise')
                    columnas_numericas.append(col)
                except:
                    continue
        
        if not columnas_numericas:
            return None
        
        metricas_calidad = []
        
        for col in columnas_numericas:
            try:
                datos_numericos = pd.to_numeric(df[col], errors='coerce')
                total_datos = len(datos_numericos)
                datos_validos = datos_numericos.dropna()
                n_validos = len(datos_validos)
                
                if n_validos == 0:
                    continue
                
                # 1. COMPLETITUD (% datos válidos)
                completitud = (n_validos / total_datos) * 100
                
                # 2. CONSISTENCIA (detección de outliers por IQR)
                Q1 = datos_validos.quantile(0.25)
                Q3 = datos_validos.quantile(0.75)
                IQR = Q3 - Q1
                limite_inferior = Q1 - 1.5 * IQR
                limite_superior = Q3 + 1.5 * IQR
                
                outliers = datos_validos[(datos_validos < limite_inferior) | (datos_validos > limite_superior)]
                consistencia = ((n_validos - len(outliers)) / n_validos) * 100
                
                # 3. ESTABILIDAD (Coeficiente de Variación)
                media = datos_validos.mean()
                std_dev = datos_validos.std()
                coef_variacion = (std_dev / media) * 100 if media != 0 else 0
                
                # Interpretación del coeficiente de variación
                if coef_variacion <= 15:
                    estabilidad = 100  # Muy estable
                elif coef_variacion <= 30:
                    estabilidad = 80   # Estable
                elif coef_variacion <= 50:
                    estabilidad = 60   # Moderadamente variable
                else:
                    estabilidad = 30   # Muy variable
                
                # 4. CONTINUIDAD TEMPORAL (solo si hay columna fecha)
                continuidad = 100  # Default si no se puede calcular
                if 'fecha' in df.columns:
                    try:
                        df_temp = df.copy()
                        df_temp['fecha_dt'] = pd.to_datetime(df_temp['fecha'], errors='coerce')
                        df_temp = df_temp.dropna(subset=['fecha_dt']).sort_values('fecha_dt')
                        
                        if len(df_temp) > 1:
                            # Calcular intervalos entre mediciones
                            intervalos = df_temp['fecha_dt'].diff().dt.total_seconds() / 60  # en minutos
                            intervalos = intervalos.dropna()
                            
                            if len(intervalos) > 0:
                                # Detectar intervalos "normales" (moda de los intervalos)
                                intervalo_normal = intervalos.mode().iloc[0] if len(intervalos.mode()) > 0 else intervalos.median()
                                
                                # Contar intervalos que están dentro del rango normal (±50% del intervalo normal)
                                rango_aceptable = intervalo_normal * 0.5
                                intervalos_normales = intervalos[
                                    (intervalos >= intervalo_normal - rango_aceptable) & 
                                    (intervalos <= intervalo_normal + rango_aceptable)
                                ]
                                
                                continuidad = (len(intervalos_normales) / len(intervalos)) * 100
                    except:
                        continuidad = 100  # Si hay error, asumir 100%
                
                # 5. QUALITY SCORE GENERAL (promedio ponderado)
                quality_score = (completitud * 0.3 + consistencia * 0.3 + estabilidad * 0.25 + continuidad * 0.15)
                
                # 6. CLASIFICACIÓN DE CALIDAD
                if quality_score >= 90:
                    clasificacion = "EXCELENTE"
                    color_clase = "🟢"
                elif quality_score >= 80:
                    clasificacion = "BUENA"
                    color_clase = "🟡"
                elif quality_score >= 70:
                    clasificacion = "ACEPTABLE"
                    color_clase = "🟠"
                else:
                    clasificacion = "DEFICIENTE"
                    color_clase = "🔴"
                
                metricas = {
                    'Variable': col,
                    'Completitud %': f"{completitud:.1f}%",
                    'Consistencia %': f"{consistencia:.1f}%", 
                    'Estabilidad %': f"{estabilidad:.1f}%",
                    'Continuidad %': f"{continuidad:.1f}%",
                    'Quality Score': f"{quality_score:.1f}%",
                    'Clasificación': f"{color_clase} {clasificacion}",
                    'N Outliers': f"{len(outliers)}",
                    'Coef. Variación': f"{coef_variacion:.2f}%"
                }
                
                metricas_calidad.append(metricas)
                
            except Exception as e:
                print(f"⚠️ Error calculando métricas de calidad para {col}: {e}")
                continue
        
        return metricas_calidad
    
    def crear_tabla_calidad(self, metricas_calidad, ancho_disponible):
        """Crea una tabla con las métricas de calidad de datos"""
        if not metricas_calidad:
            return None
        
        # Preparar headers
        headers = ['Variable', 'Completitud %', 'Consistencia %', 'Estabilidad %', 'Continuidad %', 'Quality Score', 'Clasificación', 'N Outliers', 'Coef. Variación']
        headers_con_wrap = [self.crear_header_con_wrap(header, max_chars=12) for header in headers]
        
        # Preparar datos
        data = [headers_con_wrap]
        
        for metrica in metricas_calidad:
            fila = [
                self.crear_celda_con_wrap(metrica['Variable'], max_chars=15),
                self.crear_celda_con_wrap(metrica['Completitud %'], max_chars=10),
                self.crear_celda_con_wrap(metrica['Consistencia %'], max_chars=10),
                self.crear_celda_con_wrap(metrica['Estabilidad %'], max_chars=10),
                self.crear_celda_con_wrap(metrica['Continuidad %'], max_chars=10),
                self.crear_celda_con_wrap(metrica['Quality Score'], max_chars=10),
                self.crear_celda_con_wrap(metrica['Clasificación'], max_chars=15),
                self.crear_celda_con_wrap(metrica['N Outliers'], max_chars=8),
                self.crear_celda_con_wrap(metrica['Coef. Variación'], max_chars=10)
            ]
            data.append(fila)
        
        # Calcular ancho de columnas
        num_cols = len(headers)
        col_width = ancho_disponible / num_cols
        
        # Crear tabla
        tabla = Table(data, colWidths=[col_width] * num_cols)
        
        # Estilo de tabla
        style = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]
        
        tabla.setStyle(TableStyle(style))
        return tabla
    
    def calcular_metricas_rendimiento(self, df):
        """Calcula métricas de rendimiento del sistema"""
        if df.empty:
            return None
        
        try:
            # Convertir fechas
            df_temp = df.copy()
            df_temp['fecha_dt'] = pd.to_datetime(df_temp['fecha'], errors='coerce')
            df_temp['fecha_insercion_dt'] = pd.to_datetime(df_temp['fecha_insercion'], errors='coerce')
            
            # Filtrar datos válidos
            df_temp = df_temp.dropna(subset=['fecha_dt', 'fecha_insercion_dt'])
            
            if df_temp.empty:
                return None
            
            # Ordenar por fecha de medición
            df_temp = df_temp.sort_values('fecha_dt')
            
            # 1. MEDICIONES POR DÍA
            df_temp['fecha_dia'] = df_temp['fecha_dt'].dt.date
            mediciones_por_dia = df_temp.groupby('fecha_dia').size()
            
            total_dias = len(mediciones_por_dia)
            total_mediciones = len(df_temp)
            promedio_mediciones_dia = mediciones_por_dia.mean()
            min_mediciones_dia = mediciones_por_dia.min()
            max_mediciones_dia = mediciones_por_dia.max()
            
            # 2. ESTADÍSTICAS DE INTERVALOS ENTRE MEDICIONES
            intervalos_medicion = df_temp['fecha_dt'].diff().dt.total_seconds() / 60  # en minutos
            intervalos_medicion = intervalos_medicion.dropna()
            
            # 3. ESTADÍSTICAS DE INTERVALOS ENTRE INSERCIONES
            df_temp_insercion = df_temp.sort_values('fecha_insercion_dt')
            intervalos_insercion = df_temp_insercion['fecha_insercion_dt'].diff().dt.total_seconds() / 60  # en minutos
            intervalos_insercion = intervalos_insercion.dropna()
            
            # 4. CALCULAR ESTADÍSTICAS DESCRIPTIVAS
            metricas = {
                'total_dias': total_dias,
                'total_mediciones': total_mediciones,
                'promedio_mediciones_dia': promedio_mediciones_dia,
                'min_mediciones_dia': min_mediciones_dia,
                'max_mediciones_dia': max_mediciones_dia,
                'mediciones_por_dia_detalle': mediciones_por_dia.to_dict(),
                
                # Estadísticas intervalos medición
                'intervalos_medicion': {
                    'media': intervalos_medicion.mean() if not intervalos_medicion.empty else 0,
                    'mediana': intervalos_medicion.median() if not intervalos_medicion.empty else 0,
                    'desv_std': intervalos_medicion.std() if not intervalos_medicion.empty else 0,
                    'min': intervalos_medicion.min() if not intervalos_medicion.empty else 0,
                    'max': intervalos_medicion.max() if not intervalos_medicion.empty else 0,
                    'q1': intervalos_medicion.quantile(0.25) if not intervalos_medicion.empty else 0,
                    'q3': intervalos_medicion.quantile(0.75) if not intervalos_medicion.empty else 0,
                    'total_intervalos': len(intervalos_medicion)
                },
                
                # Estadísticas intervalos inserción
                'intervalos_insercion': {
                    'media': intervalos_insercion.mean() if not intervalos_insercion.empty else 0,
                    'mediana': intervalos_insercion.median() if not intervalos_insercion.empty else 0,
                    'desv_std': intervalos_insercion.std() if not intervalos_insercion.empty else 0,
                    'min': intervalos_insercion.min() if not intervalos_insercion.empty else 0,
                    'max': intervalos_insercion.max() if not intervalos_insercion.empty else 0,
                    'q1': intervalos_insercion.quantile(0.25) if not intervalos_insercion.empty else 0,
                    'q3': intervalos_insercion.quantile(0.75) if not intervalos_insercion.empty else 0,
                    'total_intervalos': len(intervalos_insercion)
                }
            }
            
            return metricas
            
        except Exception as e:
            print(f"⚠️ Error calculando métricas de rendimiento: {e}")
            return None
    
    def crear_seccion_diagnostico_rendimiento(self, metricas_rendimiento):
        """Crea la sección de diagnóstico del rendimiento del sistema"""
        if not metricas_rendimiento:
            return [Paragraph("⚠️ No se pudieron calcular métricas de rendimiento", self.info_style)]
        
        elementos = []
        
        # Título de la sección
        elementos.append(Paragraph("🚀 DIAGNÓSTICO DEL RENDIMIENTO DEL SISTEMA", self.subtitle_style))
        elementos.append(Spacer(1, 10))
        
        # 1. RESUMEN GENERAL DE MEDICIONES
        resumen_text = (
            f"📊 <b>RESUMEN GENERAL:</b><br/>"
            f"• Total de días con datos: <b>{metricas_rendimiento['total_dias']}</b><br/>"
            f"• Total de mediciones: <b>{metricas_rendimiento['total_mediciones']:,}</b><br/>"
            f"• Promedio de mediciones por día: <b>{metricas_rendimiento['promedio_mediciones_dia']:.1f}</b><br/>"
            f"• Rango de mediciones diarias: <b>{metricas_rendimiento['min_mediciones_dia']} - {metricas_rendimiento['max_mediciones_dia']}</b>"
        )
        elementos.append(Paragraph(resumen_text, self.info_style))
        elementos.append(Spacer(1, 15))
        
        # 2. TABLA DE ESTADÍSTICAS DE INTERVALOS
        tabla_data = [
            ['📏 Métrica', '⏰ Intervalos Medición (min)', '📥 Intervalos Inserción (min)']
        ]
        
        int_med = metricas_rendimiento['intervalos_medicion']
        int_ins = metricas_rendimiento['intervalos_insercion']
        
        filas_metricas = [
            ('Media', f"{int_med['media']:.2f}", f"{int_ins['media']:.2f}"),
            ('Mediana', f"{int_med['mediana']:.2f}", f"{int_ins['mediana']:.2f}"),
            ('Desv. Estándar', f"{int_med['desv_std']:.2f}", f"{int_ins['desv_std']:.2f}"),
            ('Mínimo', f"{int_med['min']:.2f}", f"{int_ins['min']:.2f}"),
            ('Máximo', f"{int_med['max']:.2f}", f"{int_ins['max']:.2f}"),
            ('Q1 (25%)', f"{int_med['q1']:.2f}", f"{int_ins['q1']:.2f}"),
            ('Q3 (75%)', f"{int_med['q3']:.2f}", f"{int_ins['q3']:.2f}"),
            ('Total Intervalos', f"{int_med['total_intervalos']}", f"{int_ins['total_intervalos']}")
        ]
        
        for fila in filas_metricas:
            tabla_data.append(list(fila))
        
        # Crear tabla
        tabla_intervalos = Table(tabla_data, colWidths=[2.5*inch, 2*inch, 2*inch])
        tabla_intervalos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elementos.append(tabla_intervalos)
        elementos.append(Spacer(1, 15))
        
        # 3. DETALLE POR DÍA (si hay pocos días, mostrar detalle)
        if metricas_rendimiento['total_dias'] <= 10:
            elementos.append(Paragraph("📅 <b>DETALLE DE MEDICIONES POR DÍA:</b>", self.info_style))
            elementos.append(Spacer(1, 5))
            
            detalle_data = [['📅 Fecha', '📊 N° Mediciones']]
            for fecha, cantidad in sorted(metricas_rendimiento['mediciones_por_dia_detalle'].items()):
                detalle_data.append([str(fecha), str(cantidad)])
            
            tabla_detalle = Table(detalle_data, colWidths=[2*inch, 1.5*inch])
            tabla_detalle.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            
            elementos.append(tabla_detalle)
        
        return elementos
    
    def crear_tabla_estadisticas(self, estadisticas, ancho_disponible):
        """Crea una tabla con las estadísticas descriptivas"""
        if not estadisticas:
            return None
        
        # Preparar headers
        headers = ['Variable', 'Media', 'Mediana', 'Moda', 'Desv. Est.', 'Varianza', 'Mín', 'Máx', 'Q1', 'Q3', 'N válidos']
        headers_con_wrap = [self.crear_header_con_wrap(header, max_chars=10) for header in headers]
        
        # Preparar datos
        data = [headers_con_wrap]
        
        for stat in estadisticas:
            fila = [
                self.crear_celda_con_wrap(stat['Variable'], max_chars=15),
                self.crear_celda_con_wrap(stat['Media'], max_chars=10),
                self.crear_celda_con_wrap(stat['Mediana'], max_chars=10),
                self.crear_celda_con_wrap(stat['Moda'], max_chars=10),
                self.crear_celda_con_wrap(stat['Desv. Estándar'], max_chars=10),
                self.crear_celda_con_wrap(stat['Varianza'], max_chars=10),
                self.crear_celda_con_wrap(stat['Mínimo'], max_chars=10),
                self.crear_celda_con_wrap(stat['Máximo'], max_chars=10),
                self.crear_celda_con_wrap(stat['Q1'], max_chars=10),
                self.crear_celda_con_wrap(stat['Q3'], max_chars=10),
                self.crear_celda_con_wrap(stat['Valores válidos'], max_chars=10)
            ]
            data.append(fila)
        
        # Calcular ancho de columnas
        num_cols = len(headers)
        col_width = ancho_disponible / num_cols
        
        # Crear tabla
        table = Table(data, colWidths=[col_width] * num_cols)
        
        # Aplicar estilos
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            
            # Data rows style
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightblue]),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            
            # Altura mínima
            ('MINHEIGHT', (0, 0), (-1, 0), 25),
            ('MINHEIGHT', (0, 1), (-1, -1), 18),
        ]))
        
        return table
    
    def crear_pdf_dispositivo(self, proyecto_id, dispositivo_nombre, df_datos, info_archivos):
        """Crea un PDF completo para un dispositivo"""
        
        filename = f"reporte_{dispositivo_nombre}_proyecto_{proyecto_id}.pdf"
        filepath = os.path.join(self.pdfs_folder, filename)
        
        # Usar landscape para más espacio
        doc = SimpleDocTemplate(filepath, pagesize=landscape(A4),
                              rightMargin=0.5*inch, leftMargin=0.5*inch,
                              topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        # Contenido del PDF
        story = []
        
        # TÍTULO PRINCIPAL
        title = f"📊 REPORTE DE DATOS - {dispositivo_nombre.upper()}"
        story.append(Paragraph(title, self.title_style))
        
        # SUBTÍTULO
        subtitle = f"Proyecto {proyecto_id} | Generado el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        story.append(Paragraph(subtitle, self.subtitle_style))
        
        # DESCRIPCIÓN DETALLADA
        if not df_datos.empty and 'fecha_insercion' in df_datos.columns:
            # Calcular fechas de inserción inicial y final
            df_temp_fechas = df_datos.copy()
            df_temp_fechas['fecha_insercion_dt'] = pd.to_datetime(df_temp_fechas['fecha_insercion'], errors='coerce')
            fecha_inicial = df_temp_fechas['fecha_insercion_dt'].min()
            fecha_final = df_temp_fechas['fecha_insercion_dt'].max()
            
            if pd.notna(fecha_inicial) and pd.notna(fecha_final):
                fecha_inicial_str = fecha_inicial.strftime('%Y-%m-%d %H:%M:%S')
                fecha_final_str = fecha_final.strftime('%Y-%m-%d %H:%M:%S')
                
                descripcion_text = (f"🔍 <b>Descripción del Dataset:</b><br/>"
                                  f"📅 <b>Fecha inserción inicial:</b> {fecha_inicial_str}<br/>"
                                  f"📅 <b>Fecha inserción final:</b> {fecha_final_str}<br/>"
                                  f"🏷️ <b>Código interno:</b> {dispositivo_nombre}")
                story.append(Paragraph(descripcion_text, self.info_style))
                story.append(Spacer(1, 15))
        
        story.append(Spacer(1, 20))
        
        # RESUMEN DE ARCHIVOS
        if info_archivos:
            total_registros = sum(info['registros'] for info in info_archivos)
            total_archivos = len(info_archivos)
            
            resumen_text = (f"📄 <b>{total_archivos}</b> archivos procesados | "
                          f"📊 <b>{total_registros:,}</b> registros totales | "
                          f"📅 Carpetas de fechas: <b>{len(set(info['fecha_carpeta'] for info in info_archivos))}</b>")
            story.append(Paragraph(resumen_text, self.info_style))
            story.append(Spacer(1, 15))
            
            # Tabla de resumen de archivos
            archivo_data = [['📄 Archivo', '📅 Fecha Carpeta', '📊 Registros']]
            for info in info_archivos:
                archivo_data.append([
                    info['archivo'],
                    info['fecha_carpeta'],
                    f"{info['registros']:,}"
                ])
            
            archivo_table = Table(archivo_data, colWidths=[4*inch, 2*inch, 1*inch])
            archivo_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            
            story.append(archivo_table)
            story.append(Spacer(1, 20))
        
        # MÉTRICAS DE CALIDAD DE DATOS
        if not df_datos.empty:
            story.append(Paragraph("🎯 MÉTRICAS DE CALIDAD DE DATOS", self.subtitle_style))
            story.append(Spacer(1, 10))
            
            # Calcular métricas de calidad
            metricas_calidad = self.calcular_metricas_calidad(df_datos)
            
            if metricas_calidad:
                ancho_disponible = landscape(A4)[0] - 1*inch
                tabla_calidad = self.crear_tabla_calidad(metricas_calidad, ancho_disponible)
                
                if tabla_calidad:
                    story.append(tabla_calidad)
                    story.append(Spacer(1, 15))
                    
                    # Agregar explicación de las métricas
                    explicacion_calidad = (
                        "🎯 <b>Métricas de Calidad:</b><br/>"
                        "• <b>Completitud:</b> % datos válidos (no nulos)<br/>"
                        "• <b>Consistencia:</b> % datos sin outliers (método IQR)<br/>"
                        "• <b>Estabilidad:</b> Baja variabilidad (Coef. Variación &lt;30%)<br/>"
                        "• <b>Continuidad:</b> Regularidad temporal en mediciones<br/>"
                        "• <b>Quality Score:</b> Puntuación general ponderada<br/>"
                        "🟢 Excelente (≥90%) | 🟡 Buena (≥80%) | 🟠 Aceptable (≥70%) | 🔴 Deficiente (&lt;70%)"
                    )
                    story.append(Paragraph(explicacion_calidad, self.info_style))
                    story.append(Spacer(1, 20))
            else:
                story.append(Paragraph("⚠️ No se pudieron calcular métricas de calidad", self.info_style))
                story.append(Spacer(1, 15))
        
        # ESTADÍSTICAS DESCRIPTIVAS
        if not df_datos.empty:
            story.append(Paragraph("📊 ESTADÍSTICAS DESCRIPTIVAS", self.subtitle_style))
            story.append(Spacer(1, 10))
            
            # Calcular estadísticas para variables numéricas
            estadisticas = self.calcular_estadisticas_descriptivas(df_datos)
            
            if estadisticas:
                ancho_disponible = landscape(A4)[0] - 1*inch
                tabla_stats = self.crear_tabla_estadisticas(estadisticas, ancho_disponible)
                
                if tabla_stats:
                    story.append(tabla_stats)
                    story.append(Spacer(1, 20))
                    
                    # Agregar explicación de las estadísticas
                    explicacion = ("📈 <b>Interpretación:</b> Media (promedio), Mediana (valor central), "
                                 "Moda (valor más frecuente), Desv. Est. (dispersión), Q1 y Q3 (cuartiles)")
                    story.append(Paragraph(explicacion, self.info_style))
                    story.append(Spacer(1, 15))
            else:
                story.append(Paragraph("⚠️ No se encontraron variables numéricas para análisis estadístico", self.info_style))
                story.append(Spacer(1, 15))
        
        # DATOS PRINCIPALES
        if not df_datos.empty:
            story.append(Paragraph("📋 DATOS COMPLETOS", self.subtitle_style))
            story.append(Spacer(1, 10))
            
            # Formatear datos
            df_formatted = self.formatear_datos_para_tabla(df_datos)
            
            # Dividir en páginas si hay muchos datos
            filas_por_pagina = 35  # Ajustado para landscape
            total_filas = len(df_formatted)
            
            if total_filas <= filas_por_pagina:
                # Todos los datos en una página
                ancho_disponible = landscape(A4)[0] - 1*inch  # Restar márgenes
                table = self.crear_tabla_pdf(df_formatted, ancho_disponible)
                if table:
                    story.append(table)
            else:
                # Dividir en múltiples páginas
                for pagina in range(0, total_filas, filas_por_pagina):
                    fin = min(pagina + filas_por_pagina, total_filas)
                    df_pagina = df_formatted.iloc[pagina:fin]
                    
                    if pagina > 0:
                        story.append(PageBreak())
                    
                    page_title = f"📋 DATOS COMPLETOS - Página {pagina//filas_por_pagina + 1} (Filas {pagina + 1}-{fin})"
                    story.append(Paragraph(page_title, self.subtitle_style))
                    story.append(Spacer(1, 10))
                    
                    ancho_disponible = landscape(A4)[0] - 1*inch
                    table = self.crear_tabla_pdf(df_pagina, ancho_disponible)
                    if table:
                        story.append(table)
                    
                    if pagina + filas_por_pagina < total_filas:
                        story.append(Spacer(1, 20))
            
            # DIAGNÓSTICO DEL RENDIMIENTO DEL SISTEMA
            story.append(Spacer(1, 30))
            
            # Calcular métricas de rendimiento
            metricas_rendimiento = self.calcular_metricas_rendimiento(df_datos)
            
            # Agregar sección de diagnóstico
            elementos_diagnostico = self.crear_seccion_diagnostico_rendimiento(metricas_rendimiento)
            for elemento in elementos_diagnostico:
                story.append(elemento)
        
        else:
            story.append(Paragraph("❌ No hay datos disponibles para este dispositivo", self.info_style))
        
        # Construir PDF
        doc.build(story)
        return filepath
    
    def generar_todos_los_pdfs(self):
        """Genera PDFs para todos los dispositivos"""
        print("🚀 Iniciando generación de PDFs por dispositivo...")
        
        # Escanear estructura
        estructura = self.escanear_estructura()
        
        if not estructura:
            print("❌ No se encontró estructura de datos válida")
            return []
        
        pdfs_generados = []
        
        for proyecto_id, dispositivos in estructura.items():
            for dispositivo_nombre, fechas_datos in dispositivos.items():
                print(f"\n📊 Generando PDF para {dispositivo_nombre} (Proyecto {proyecto_id})...")
                
                # Leer datos del dispositivo
                df_datos, info_archivos = self.leer_datos_dispositivo(
                    proyecto_id, dispositivo_nombre, fechas_datos
                )
                
                # Crear PDF
                pdf_path = self.crear_pdf_dispositivo(
                    proyecto_id, dispositivo_nombre, df_datos, info_archivos
                )
                
                pdfs_generados.append(pdf_path)
                print(f"✅ PDF generado: {os.path.basename(pdf_path)}")
        
        print(f"\n🎉 Generación completada! Se crearon {len(pdfs_generados)} PDFs en '{self.pdfs_folder}'")
        return pdfs_generados


# ===== EJECUCIÓN PRINCIPAL =====
if __name__ == "__main__":
    print("📄 Iniciando generación de reportes PDF...")
    

    generador = GeneradorPDFDispositivos()
    pdfs = generador.generar_todos_los_pdfs()
    
    if pdfs:
        print("\n📋 PDFs GENERADOS:")
        for i, pdf in enumerate(pdfs, 1):
            print(f"{i}. {os.path.basename(pdf)}")
        print(f"\n📁 Ubicación: {os.path.abspath(generador.pdfs_folder)}")
    else:
        print("\n❌ No se pudieron generar PDFs")