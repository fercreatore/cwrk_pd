@echo off
REM =============================================================
REM INSTALAR dependencias para Streamlit app de carga de pedidos
REM Ejecutar UNA sola vez en el .112 (DATASVRW)
REM =============================================================

echo.
echo ========================================
echo  Instalando dependencias Streamlit...
echo ========================================
echo.

REM Usar Python 3.14 que ya esta instalado para el freelance
set PYTHON="C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe"

REM Verificar que existe Python
%PYTHON% --version
if errorlevel 1 (
    echo.
    echo ERROR: No se encontro Python 3.14
    echo Verificar ruta: %PYTHON%
    echo.
    pause
    exit /b 1
)

echo.
echo Instalando paquetes...
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install streamlit pyodbc Pillow pandas pdfplumber PyMuPDF openpyxl numpy python-dateutil plotly

echo.
echo ========================================
echo  Instalacion completada!
echo ========================================
echo  Ahora ejecutar: iniciar_streamlit.bat
echo ========================================
echo.
pause
