@echo off
REM sync_from_mac.bat — Tira desde el 111, copia archivos del Mac
REM
REM PREREQUISITO: El Mac debe tener compartida la carpeta cowork_pedidos
REM   Mac > Preferencias del Sistema > Compartir > Compartir archivos > agregar carpeta
REM
REM AJUSTAR esta ruta al nombre de red del Mac:
SET MAC_SHARE=\\FERNANDOS-MAC\cowork_pedidos
SET LOCAL_DIR=C:\cowork_pedidos

echo Sincronizando desde Mac...
robocopy "%MAC_SHARE%" "%LOCAL_DIR%" *.py *.md *.sql /S /XO /NJH /NJS
echo.
echo Sync completo.
pause
