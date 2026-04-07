@echo off
REM ============================================================================
REM install_service.bat — Instala FastAPI como servicio Windows (NSSM)
REM Servidor: 192.168.2.112 (DATASVRW)
REM Servicio: CalzalindoFreelance
REM Python: C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe
REM Port: 8001
REM ============================================================================
REM
REM INSTRUCCIONES:
REM 1. Ejecutar como Administrator
REM 2. NSSM debe estar instalado en C:\nssm\ o en PATH
REM    Descargar: https://nssm.cc/download
REM    Descomprimir nssm-2.24-101-g897c7ee\win64\nssm.exe a C:\nssm\
REM 3. El servicio se iniciará automáticamente en cada boot
REM 4. Para ver logs: nssm get CalzalindoFreelance AppStderr
REM    Para detener: net stop CalzalindoFreelance
REM    Para remover: nssm remove CalzalindoFreelance confirm
REM
REM ============================================================================

setlocal enabledelayedexpansion

color 0A
title Instalar Servicio CalzalindoFreelance

REM Check if running as Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ERROR: Este script requiere permisos de Administrador.
    echo Por favor ejecutar como Administrator.
    pause
    exit /b 1
)

REM Check if NSSM is installed
set NSSM_PATH=C:\nssm\nssm.exe
if not exist "%NSSM_PATH%" (
    REM Try PATH
    where nssm.exe >nul 2>&1
    if %errorLevel% equ 0 (
        for /f "delims=" %%A in ('where nssm.exe') do set NSSM_PATH=%%A
    ) else (
        echo.
        echo ERROR: NSSM no encontrado.
        echo.
        echo NSSM debe estar instalado. Opciones:
        echo 1. Descargar desde: https://nssm.cc/download
        echo 2. Descomprimir nssm-*.exe a C:\nssm\
        echo 3. O agregar NSSM al PATH del sistema
        echo.
        pause
        exit /b 1
    )
)

echo [INFO] Usando NSSM: %NSSM_PATH%
echo.

REM Service name
set SERVICE_NAME=CalzalindoFreelance
set PYTHON_EXE=C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe
set APP_DIR=C:\calzalindo_freelance
set APP_MODULE=main:app
set PORT=8001

REM Check if Python exists
if not exist "%PYTHON_EXE%" (
    echo ERROR: Python 3.14 no encontrado en:
    echo   %PYTHON_EXE%
    pause
    exit /b 1
)

REM Check if app directory exists
if not exist "%APP_DIR%" (
    echo ERROR: Directorio app no encontrado:
    echo   %APP_DIR%
    pause
    exit /b 1
)

REM Remove existing service if it exists
echo [INFO] Verificando servicio existente...
"%NSSM_PATH%" status "%SERVICE_NAME%" >nul 2>&1
if %errorLevel% equ 0 (
    echo [INFO] Servicio ya existe. Removiendo...
    "%NSSM_PATH%" stop "%SERVICE_NAME%" >nul 2>&1
    "%NSSM_PATH%" remove "%SERVICE_NAME%" confirm >nul 2>&1
    if %errorLevel% equ 0 (
        echo [OK] Servicio anterior removido.
    ) else (
        echo [WARN] No se pudo remover servicio anterior.
    )
)

echo.
echo [INFO] Instalando servicio: %SERVICE_NAME%
echo   Python: %PYTHON_EXE%
echo   App Dir: %APP_DIR%
echo   Modulo: %APP_MODULE%
echo   Puerto: %PORT%
echo.

REM Install service
"%NSSM_PATH%" install "%SERVICE_NAME%" "%PYTHON_EXE%" "-m uvicorn %APP_MODULE% --host 0.0.0.0 --port %PORT%"

if %errorLevel% neq 0 (
    echo.
    echo ERROR: Fallo al instalar servicio.
    pause
    exit /b 1
)

REM Set app directory
"%NSSM_PATH%" set "%SERVICE_NAME%" AppDirectory "%APP_DIR%"
if %errorLevel% neq 0 (
    echo [WARN] Error setting AppDirectory
)

REM Set startup type to auto
"%NSSM_PATH%" set "%SERVICE_NAME%" Start SERVICE_AUTO_START
if %errorLevel% neq 0 (
    echo [WARN] Error setting auto-start
)

REM Set restart behavior
"%NSSM_PATH%" set "%SERVICE_NAME%" AppRestartDelay 5000
"%NSSM_PATH%" set "%SERVICE_NAME%" AppThrottle 1500

REM Set output to log files (optional)
set LOG_DIR=%APP_DIR%\logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStdout "%LOG_DIR%\stdout.log"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStderr "%LOG_DIR%\stderr.log"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStdoutCreationDisposition 4
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStderrCreationDisposition 4

REM Start the service
echo.
echo [INFO] Iniciando servicio...
"%NSSM_PATH%" start "%SERVICE_NAME%"

if %errorLevel% equ 0 (
    echo.
    echo ============================================================================
    echo [OK] Servicio instalado y iniciado exitosamente.
    echo ============================================================================
    echo.
    echo Servicio: %SERVICE_NAME%
    echo Estado: Auto-start habilitado
    echo Puerto: %PORT%
    echo URL: http://localhost:%PORT%
    echo.
    echo Comandos utiles:
    echo   net start CalzalindoFreelance     — Iniciar servicio
    echo   net stop CalzalindoFreelance      — Detener servicio
    echo   nssm status CalzalindoFreelance   — Ver estado
    echo   nssm get CalzalindoFreelance AppStderr  — Ver error log
    echo.
) else (
    echo.
    echo ERROR: Fallo al iniciar servicio.
    echo.
)

pause
