@echo off
title Webhook Tokens - Puerto 8506
set PYTHON=C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe
set PYTHONPATH=C:\cowork_pedidos_app

:inicio
echo [%date% %time%] Iniciando webhook tokens...
cd /d C:\cowork_pedidos_app
%PYTHON% -m multicanal.webhook_tokens --port 8506

echo [%date% %time%] Webhook se detuvo. Reiniciando en 5 segundos...
timeout /t 5 /nobreak >nul
goto inicio
