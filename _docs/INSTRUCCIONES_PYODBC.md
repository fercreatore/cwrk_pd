# Instalación de pyodbc en Windows

## Prerequisitos

### 1. Python instalado
Verificar que tenés Python 3.8+ instalado:
```
python --version
```
Si no lo tenés, descargarlo de https://www.python.org/downloads/

### 2. ODBC Driver 17 for SQL Server
Este driver probablemente ya está instalado en tu máquina si usás MS Gestión.
Para verificar, abrir CMD y ejecutar:
```
odbcad32
```
En la pestaña "Drivers" debería aparecer "ODBC Driver 17 for SQL Server".

Si NO está, descargarlo de:
https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

## Instalación

### Opción A: pip directo (lo más simple)
Abrir CMD o PowerShell como administrador y ejecutar:
```
pip install pyodbc
```

### Opción B: si tenés un entorno virtual
```
cd C:\Proyectos\calzalindo\notas_pedido\cowork_pedidos
python -m venv venv
venv\Scripts\activate
pip install pyodbc
pip install openpyxl pandas    # para parsear Excel
```

### Opción C: si pip falla por compilación
En algunos Windows, pyodbc necesita compilar extensiones C. Si falla:
```
pip install --only-binary :all: pyodbc
```
O instalar desde un wheel precompilado:
```
pip install pipwin
pipwin install pyodbc
```

## Verificar la instalación

Abrir Python y ejecutar:
```python
import pyodbc

# Listar drivers disponibles
print(pyodbc.drivers())

# Debería aparecer algo como:
# ['ODBC Driver 17 for SQL Server', 'SQL Server', ...]
```

## Probar la conexión

```python
import pyodbc

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.112;"
    "DATABASE=msgestionC;"
    "UID=administrador;"
    "PWD=Cagr$2011;"
    "TrustServerCertificate=yes;"
)

try:
    conn = pyodbc.connect(conn_str, timeout=10)
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 numero, denominacion FROM pedico2 ORDER BY numero DESC")
    row = cursor.fetchone()
    print(f"Último pedido: {row[0]} - {row[1]}")
    conn.close()
    print("Conexión OK!")
except Exception as e:
    print(f"Error: {e}")
```

## Ejecutar los scripts

Una vez instalado pyodbc, podés ejecutar desde la carpeta del proyecto:

```
cd C:\Proyectos\calzalindo\notas_pedido\cowork_pedidos

# Paso 1: verificar BD
python paso1_verificar_bd.py

# Paso 7: analizar colores (Topper)
python paso7_reconstruir_colores.py --marca 314 --dry-run

# Paso 6b: flujo Topper dry-run
python paso6b_flujo_topper.py "TOPPER CALZADO COMPLETO.xlsx" --dry-run

# Cuando estés conforme con el dry-run:
python paso6b_flujo_topper.py "TOPPER CALZADO COMPLETO.xlsx" --ejecutar
```

## Dependencias adicionales

Si no las tenés instaladas:
```
pip install openpyxl    # para leer Excel
pip install pandas      # para paso5_parsear_excel.py
```

## Troubleshooting

### Error: "Data source name not found"
- Verificar que ODBC Driver 17 está instalado (ver paso 2)
- Si tenés "ODBC Driver 18", cambiar en config.py:
  `DRIVER={ODBC Driver 18 for SQL Server}`

### Error: "Login failed"
- Verificar usuario/contraseña en config.py
- Verificar que el servidor 192.168.2.112 es accesible desde tu red

### Error: "Could not connect to server"
- Verificar que estás en la red de la empresa (o VPN)
- Probar: `ping 192.168.2.112`
- Verificar que SQL Server está escuchando en el puerto 1433
