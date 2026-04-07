# Diagnóstico Conectividad 112 (DATASVRW) — 21 mar 2026

## Estado de red

| Test | Resultado |
|------|-----------|
| Ping | OK (133-160ms) |
| Puerto 445 (SMB) | ABIERTO |
| Puerto 1433 (SQL Server) | ABIERTO |
| Puerto 3389 (RDP) | CERRADO |
| Puerto 8501 | CERRADO (no hay Streamlit en este puerto) |
| Puerto 8502 | CERRADO (app_h4.py NO corriendo) |
| Puerto 8503 | **ABIERTO** (app_carga.py corriendo) |

## Montaje SMB

| Share | Resultado | Punto de montaje |
|-------|-----------|-----------------|
| `//administrador:cagr$2011@192.168.2.112/compartido` | YA MONTADO | `~/mnt/compartido_112` |
| `//administrador:cagr$2011@192.168.2.112/c$` | OK (montaje nuevo) | `~/mnt/datasvrw_c` |
| `/Volumes/server_112` | MONTADO PERO VACÍO (stale) | Desmontar |
| `/Volumes/server_112c` | MONTADO PERO VACÍO (stale) | Desmontar |

**Credenciales**: `administrador/cagr$2011` — las mismas que el 111.

## Contenido del servidor

### Python
- **Python 3.14** instalado en `C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe`
- Streamlit: instalado (puerto 8503 responde)

### Carpeta `C:\cowork_pedidos_app` (destino del deploy)
Archivos presentes y deployados el 15-20 mar 2026:
```
app_h4.py          (15 mar)
app_carga.py       (15 mar) — CORRIENDO en puerto 8503
app_reposicion.py  (15 mar)
config.py          (15 mar)
ocr_factura.py     (20 mar)
paso3_calcular_periodo.py, paso4_insertar_pedido.py, paso5_parsear_excel.py
paso8_carga_factura.py, proveedores_db.py, resolver_talle.py
requirements.txt
iniciar_streamlit.bat, instalar_streamlit.bat
.streamlit/config.toml
logos/, tests/, facturas_procesadas/, __pycache__/
```

### Otros directorios relevantes en 112
- `C:\calzalindo_freelance` — app freelance
- `C:\scripts_para_cron\001_auditorias_from_109.bat`
- `C:\COMPARTIDO` — archivos compartidos (COMPRAS, FOTOS, etc.)
- `C:\respaldo_sql_desde_111`, `C:\respaldo_sql_tmp` — backups SQL

## Archivos desactualizados en 112

| Archivo | 112 | Local (Mac) | Acción |
|---------|-----|-------------|--------|
| app_carga.py | 15 mar | **17 mar** | REDEPLOY |
| app_reposicion.py | 15 mar | **21 mar** | REDEPLOY |
| config.py | 15 mar | **20 mar** | REDEPLOY |

## Estado actual de Streamlit en 112

- `app_carga.py` **SÍ corre** en puerto 8503 (debería ser 8501 según PUERTOS.md)
- `app_h4.py` **NO corre** (puerto 8502 cerrado)
- `app_reposicion.py` **NO corre** (puerto 8503 usado por app_carga)
- `iniciar_streamlit.bat` levanta app_h4 en 8502 y app_carga en 8503 — NO levanta app_reposicion

**Discrepancia de puertos**: `config.toml` dice `port = 8501`, pero `iniciar_streamlit.bat` usa 8502/8503 (el .bat sobreescribe con `--server.port`).

## Qué falta para deployar app_reposicion.py al 112

### 1. Redeploy archivos actualizados
```bash
cd ~/Desktop/cowork_pedidos/_sync_tools
./deploy_112.sh
```
Esto copia todos los archivos listados en `APP_FILES` al 112 vía SMB.

### 2. Actualizar `iniciar_streamlit.bat` para incluir app_reposicion
El .bat actual solo levanta `app_h4.py` (8502) y `app_carga.py` (8503).
Agregar:
```bat
start "Reposicion" %PYTHON% -m streamlit run app_reposicion.py --server.port 8503 --server.address 0.0.0.0 --server.headless true
```
Y reasignar puertos para que coincidan con PUERTOS.md:
- app_carga.py → 8501
- app_h4.py → 8502
- app_reposicion.py → 8503

### 3. Abrir puertos en firewall de Windows (si no están)
Desde PowerShell admin en el 112:
```powershell
netsh advfirewall firewall add rule name="Streamlit 8501" dir=in action=allow protocol=TCP localport=8501
netsh advfirewall firewall add rule name="Streamlit 8502" dir=in action=allow protocol=TCP localport=8502
netsh advfirewall firewall add rule name="Streamlit 8503" dir=in action=allow protocol=TCP localport=8503
```

### 4. Reiniciar Streamlit en el 112
Conectarse por RDP (puerto 3389 cerrado — probar con TeamViewer o físicamente) y ejecutar:
```
cd C:\cowork_pedidos_app
iniciar_streamlit.bat
```

### 5. Verificar desde Mac
```bash
nc -zv 192.168.2.112 8501 8502 8503
curl http://192.168.2.112:8503
```

## Bloqueantes

1. **RDP cerrado** — no se puede acceder remotamente para reiniciar Streamlit o abrir firewall. Hay que ir físicamente al servidor o habilitar RDP.
2. **Archivos desactualizados** — `app_reposicion.py` en el 112 es del 15 mar, el local tiene cambios del 21 mar.
3. **`iniciar_streamlit.bat` no incluye app_reposicion** — hay que actualizarlo.
4. **Conflicto de puertos** — app_carga ocupa el 8503 (debería ser 8501 según PUERTOS.md), dejando sin puerto a app_reposicion.

## Comando rápido de deploy (desde Mac)

```bash
# 1. Montar C$ del 112 (si no está)
mkdir -p ~/mnt/datasvrw_c
mount_smbfs '//administrador:cagr$2011@192.168.2.112/c$' ~/mnt/datasvrw_c

# 2. Copiar archivos actualizados
cp ~/Desktop/cowork_pedidos/app_reposicion.py ~/mnt/datasvrw_c/cowork_pedidos_app/
cp ~/Desktop/cowork_pedidos/app_carga.py ~/mnt/datasvrw_c/cowork_pedidos_app/
cp ~/Desktop/cowork_pedidos/config.py ~/mnt/datasvrw_c/cowork_pedidos_app/

# 3. Verificar
ls -la ~/mnt/datasvrw_c/cowork_pedidos_app/app_reposicion.py
```
