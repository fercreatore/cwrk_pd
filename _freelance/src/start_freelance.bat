@echo off
REM ============================================================================
REM start_freelance.bat — Inicia FastAPI app de Calzalindo Freelance
REM Servidor: 192.168.2.112 (DATASVRW)
REM Python: C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe
REM Port: 8001
REM ============================================================================

title Calzalindo Freelance — FastAPI (uvicorn)
color 0A

REM Set working directory
cd /d "C:\calzalindo_freelance"

REM Check if Python exists
if not exist "C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe" (
    echo.
    echo ERROR: Python 3.14 no encontrado en:
    echo   C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe
    echo.
    echo Por favor instalar Python 3.14 o verificar la ruta.
    pause
    exit /b 1
)

REM Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    echo Activando venv...
    call venv\Scripts\activate.bat
) else (
    echo [INFO] No virtual environment found. Using Python directly.
)

REM Start FastAPI with uvicorn
echo.
echo Iniciando FastAPI en http://0.0.0.0:8001
echo.

"C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

REM If uvicorn fails, keep window open
if errorlevel 1 (
    echo.
    echo ERROR: FastAPI fallo. Presiona una tecla para salir.
    pause
    exit /b 1
)

pause
