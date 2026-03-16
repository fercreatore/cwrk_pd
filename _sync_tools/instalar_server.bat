@echo off
REM ═══════════════════════════════════════════════════════════════
REM  INSTALADOR - Sistema de Carga H4/Calzalindo
REM  Ejecutar como Administrador en DELL-SVR (192.168.2.111)
REM ═══════════════════════════════════════════════════════════════

echo.
echo ========================================
echo   Instalador Sistema de Carga H4
echo ========================================
echo.

REM ── Verificar Python ──
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instalar Python 3.10+ desde python.org
    echo         Asegurar que "Add to PATH" este activado al instalar.
    pause
    exit /b 1
)

echo [OK] Python encontrado:
python --version
echo.

REM ── Instalar dependencias ──
echo Instalando dependencias...
pip install streamlit pyodbc Pillow pillow-heif requests --upgrade
if errorlevel 1 (
    echo [WARN] Hubo errores al instalar. Intentando con python -m pip...
    python -m pip install streamlit pyodbc Pillow pillow-heif requests --upgrade
)
echo.

REM ── Verificar ODBC Driver ──
echo Verificando ODBC Driver...
python -c "import pyodbc; drivers=[d for d in pyodbc.drivers() if 'SQL Server' in d]; print('Drivers SQL:', drivers)"
echo.

REM ── Crear carpeta de trabajo ──
if not exist "C:\CargaH4" mkdir "C:\CargaH4"
echo [OK] Carpeta C:\CargaH4 lista
echo.

REM ── Copiar archivos (si se ejecuta desde la carpeta cowork_pedidos) ──
if exist "app_carga.py" (
    echo Copiando archivos a C:\CargaH4...
    copy /Y config.py C:\CargaH4\
    copy /Y app_carga.py C:\CargaH4\
    copy /Y paso8_carga_factura.py C:\CargaH4\
    copy /Y paso4_insertar_pedido.py C:\CargaH4\
    copy /Y paso7_buscar_imagenes.py C:\CargaH4\
    echo [OK] Archivos copiados
) else (
    echo [INFO] Ejecutar desde la carpeta cowork_pedidos para copiar archivos
    echo        o copiar manualmente a C:\CargaH4
)
echo.

REM ── Crear script de inicio ──
echo Creando C:\CargaH4\iniciar.bat...
(
echo @echo off
echo cd /d C:\CargaH4
echo echo Iniciando Sistema de Carga H4...
echo echo Acceder desde cualquier PC: http://192.168.2.111:8501
echo echo Presionar Ctrl+C para detener
echo echo.
echo streamlit run app_carga.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false
) > C:\CargaH4\iniciar.bat
echo [OK] Script de inicio creado
echo.

echo ========================================
echo   Instalacion completada!
echo ========================================
echo.
echo Para iniciar el sistema:
echo   1. Abrir CMD como Administrador
echo   2. Ejecutar: C:\CargaH4\iniciar.bat
echo.
echo Acceso desde la intranet:
echo   http://192.168.2.111:8501
echo.
echo Para que inicie automaticamente con Windows:
echo   Copiar acceso directo de iniciar.bat a:
echo   shell:startup
echo.
pause
