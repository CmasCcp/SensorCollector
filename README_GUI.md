# 🌡️ Interfaz Gráfica para Colector de Datos de Sensores

## 📖 Descripción

Esta interfaz gráfica proporciona una manera moderna, fácil e intuitiva de configurar y ejecutar la colección de datos de sensores ambientales. Está construida con **CustomTkinter** para una apariencia profesional y soporte de modo oscuro.

## 🚀 Instalación y Uso

### Requisitos
- Python 3.7 o superior
- Librerías listadas en `requeriments.txt` (incluyendo `customtkinter`)

### Instalación de dependencias
```bash
pip install -r requeriments.txt
```

### Ejecución
```bash
python gui_app.py
```

## 🎯 Características Principales

### 📊 Dashboard
- Vista inicial con accesos rápidos.
- Información general de la aplicación.

### 📡 Colector (Collector)
- **Descargar Datos**: Ejecuta el proceso de descarga desde la API (mismo motor que `app.py`).
- **Subir a OneDrive**: Sube los archivos CSV procesados a la nube.
- **Log en Tiempo Real**: Visualiza el progreso detallado de las operaciones directamente en la ventana.

### 🛠️ Herramientas (Tools)
- **Conversor CSV a Excel**: Convierte masivamente los archivos recolectados a formato Excel.
- **Unificador de Proyectos**: Combina múltiples archivos CSV dispersos en un único archivo consolidado por proyecto.

### ⚙️ Configuración Visual
- **Temas**: Soporte para Modo Claro, Modo Oscuro y Sistema.
- **Interfaz Responsiva**: Diseño limpio y organizado por pestañas.

## 📁 Estructura de Carpetas

- `datos/`: Carpeta donde se descargan los CSV crudos.
- `datos_unificados/`: Carpeta de salida para datos consolidados.
- `datos_excel/`: Carpeta para los reportes en Excel.

## 📞 Soporte

Cualquier duda o mejora, contactar al equipo de desarrollo.
