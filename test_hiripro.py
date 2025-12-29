import requests
import pandas as pd
from io import StringIO

# Parámetros para HIRIPRO-06
proyecto = 18
codigo_interno = "HIRIPRO-06"
api_url = "https://api-sensores.cmasccp.cl/listarDatosEstructuradosV2"
fecha_inicio = "2025-11-20"

def test_hiripro_paquetes():
    """Probar múltiples paquetes para HIRIPRO-06"""
    
    headers = {'Accept': 'text/csv'}
    limite = 100
    
    for paquete_num in range(1, 6):  # Probar 5 paquetes
        offset = (paquete_num - 1) * limite
        
        url_completa = f"{api_url}?tabla=datos&order_by=fecha_insercion&disp.id_proyecto={proyecto}&limite={limite}&offset={offset}&disp.codigo_interno={codigo_interno}&fecha_inicio={fecha_inicio}&formato=csv"
        
        print(f"\n📦 Paquete {paquete_num}: offset={offset}")
        print(f"🔗 URL: {url_completa}")
        
        try:
            response = requests.get(url_completa, headers=headers, timeout=60)
            print(f"📡 Status: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text.strip()
                print(f"📄 Contenido: {len(content)} caracteres")
                
                if content:
                    try:
                        df = pd.read_csv(StringIO(content))
                        print(f"📊 Registros: {len(df)}")
                        
                        if len(df) == 0:
                            print("📭 Paquete vacío - Fin de datos")
                            break
                        elif len(df) < limite:
                            print(f"📭 Último paquete ({len(df)} < {limite})")
                            break
                        else:
                            print(f"🔄 Paquete completo, continuando...")
                    
                    except Exception as e:
                        print(f"❌ Error CSV: {e}")
                        break
                else:
                    print("📭 Respuesta vacía - Fin de datos")
                    break
            else:
                print(f"❌ Error HTTP: {response.status_code}")
                print(f"📄 Mensaje: {response.text[:200]}")
                break
                
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            break

if __name__ == "__main__":
    test_hiripro_paquetes()