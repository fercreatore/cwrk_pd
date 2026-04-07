@echo off
REM =============================================================
REM DEPLOY WEB2PY en servidor 111 (DELL-SVR)
REM Copia staging -> web2py y reinicia web2py
REM
REM IMPORTANTE: Ejecutar como Administrador (clic derecho ->
REM "Ejecutar como administrador") para que taskkill funcione.
REM
REM Uso: deploy_web2py_111.bat [norestart]
REM   norestart = solo copiar, no reiniciar web2py
REM =============================================================

setlocal enabledelayedexpansion

set STAGING=C:\cowork_pedidos\_informes\calzalindo_informes_DEPLOY
set WEB2PY=C:\web2py_src\applications\calzalindo_informes

REM --- Verificar que corre como admin ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] No se esta ejecutando como Administrador.
    echo         taskkill puede fallar. Se recomienda ejecutar
    echo         con clic derecho -^> "Ejecutar como administrador"
    echo.
)

REM --- Verificar que existen las carpetas ---
if not exist "%STAGING%" (
    echo [ERROR] No existe %STAGING%
    echo         Ejecutar primero deploy_web2py.sh desde el Mac
    pause
    exit /b 1
)

if not exist "%WEB2PY%" (
    echo [ERROR] No existe %WEB2PY%
    echo         Verificar que web2py esta instalado
    pause
    exit /b 1
)

echo ================================================
echo  Deploy calzalindo_informes a web2py
echo ================================================
echo  Staging: %STAGING%
echo  Web2py:  %WEB2PY%
echo ================================================
echo.

set COPIED=0

REM === Controllers ===
echo --- Controllers ---
if exist "%STAGING%\controllers\*.py" (
    for %%f in (%STAGING%\controllers\*.py) do (
        copy /Y "%%f" "%WEB2PY%\controllers\" >nul
        echo   [OK] controllers\%%~nxf
        set /a COPIED+=1
    )
) else (
    echo   [SKIP] No hay controllers para copiar
)

REM === Views - layout.html en raiz ===
echo --- Views ---
if exist "%STAGING%\views\layout.html" (
    copy /Y "%STAGING%\views\layout.html" "%WEB2PY%\views\" >nul
    echo   [OK] views\layout.html
    set /a COPIED+=1
)

REM === Views - subdirectorios ===
for /d %%d in (%STAGING%\views\*) do (
    if exist "%%d\*.html" (
        if not exist "%WEB2PY%\views\%%~nxd" mkdir "%WEB2PY%\views\%%~nxd"
        xcopy /Y /Q "%%d\*.html" "%WEB2PY%\views\%%~nxd\" >nul
        for %%f in (%%d\*.html) do (
            echo   [OK] views\%%~nxd\%%~nxf
            set /a COPIED+=1
        )
    )
)

REM === Models ===
echo --- Models ---
if exist "%STAGING%\models\*.py" (
    for %%f in (%STAGING%\models\*.py) do (
        copy /Y "%%f" "%WEB2PY%\models\" >nul
        echo   [OK] models\%%~nxf
        set /a COPIED+=1
    )
) else (
    echo   [SKIP] No hay models para copiar
)

REM === Limpiar __pycache__ ===
echo.
echo --- Limpiando cache ---
if exist "%WEB2PY%\controllers\__pycache__" (
    rd /S /Q "%WEB2PY%\controllers\__pycache__" 2>nul
    echo   [OK] controllers\__pycache__ eliminado
)
if exist "%WEB2PY%\models\__pycache__" (
    rd /S /Q "%WEB2PY%\models\__pycache__" 2>nul
    echo   [OK] models\__pycache__ eliminado
)

echo.
echo ================================================
echo  %COPIED% archivos copiados a web2py
echo ================================================

REM === Reiniciar web2py (salvo si norestart) ===
if /i "%1"=="norestart" (
    echo.
    echo  [SKIP] Reinicio de web2py omitido (norestart)
    echo  Para reiniciar manualmente:
    echo    taskkill /f /im python.exe
    echo    cd C:\web2py_src
    echo    start python web2py.py -a admin -i 0.0.0.0 -p 8080
    goto :fin
)

echo.
echo --- Reiniciando web2py ---
taskkill /f /im python.exe 2>nul
if %errorlevel% equ 0 (
    echo   [OK] python.exe detenido
) else (
    echo   [INFO] python.exe no estaba corriendo
)

timeout /t 2 /nobreak >nul

cd /d C:\web2py_src
start "web2py" python web2py.py -a admin -i 0.0.0.0 -p 8080
echo   [OK] web2py iniciado en http://0.0.0.0:8080

:fin
echo.
echo ================================================
echo  Deploy completado. Recargar el dashboard.
echo ================================================
echo.
pause
