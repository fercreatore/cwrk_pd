@echo off
REM =============================================================
REM INICIAR Streamlit apps - H4 / Calzalindo
REM Accesible desde toda la red:
REM   Carga de Pedidos:        http://192.168.2.112:8502
REM   Reposicion Inteligente:  http://192.168.2.112:8503
REM =============================================================

set PYTHON="C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe"

echo.
echo ========================================
echo  Apps Streamlit - H4 / Calzalindo
echo ========================================
echo  Carga de Pedidos:        http://192.168.2.112:8502
echo  Reposicion Inteligente:  http://192.168.2.112:8503
echo  Ctrl+C para detener
echo ========================================
echo.

cd /d C:\cowork_pedidos_app

REM Iniciar app principal (Sistema Integrado) en 8502
start "H4 Sistema" %PYTHON% -m streamlit run app_h4.py --server.port 8502 --server.address 0.0.0.0 --server.headless true

REM Iniciar app carga facturas en 8503 (backup standalone)
%PYTHON% -m streamlit run app_carga.py --server.port 8503 --server.address 0.0.0.0 --server.headless true
