@echo off
setlocal

REM ============================================================================
REM  schedule_autorepo_111.bat
REM  ---------------------------------------------------------------------------
REM  Proposito:
REM    Configura el Task Scheduler de Windows Server 2012 (192.168.2.111) con
REM    las tres tareas del motor de autocompensacion/reposicion:
REM
REM      1. CWK_Autorepo_Urgente     -> diaria a las 07:00
REM      2. CWK_Autorepo_Rebalanceo  -> semanal jueves a las 18:00
REM      3. CWK_Autorepo_Auditoria   -> mensual el dia 1 a las 09:00
REM
REM    Todas ejecutan el mismo script C:\cowork_pedidos\autorepo_engine.py con
REM    un --modo distinto. Corren como SYSTEM, con privilegios elevados, y
REM    redirigen stdout/stderr a C:\cowork_pedidos\autorepo\logs\.
REM
REM    Ventana de mantenimiento SQL Server 02:00-05:00 AM: los horarios
REM    elegidos la evitan a proposito. No mover sin coordinar con IT.
REM
REM  Fecha creacion: 11-abr-2026
REM
REM  Instalacion (desde el servidor 192.168.2.111):
REM    1. Abrir CMD como Administrador (Run as administrator)
REM    2. cd C:\cowork_pedidos\_sync_tools
REM    3. schedule_autorepo_111.bat
REM
REM  Requisitos previos:
REM    - Python 3.13 disponible via "py -3"  (NO usar "python", apunta a 2.7)
REM    - C:\cowork_pedidos\autorepo_engine.py existente al momento de
REM      dispararse la tarea (el .bat NO verifica existencia del script,
REM      solo programa las tareas)
REM
REM  Idempotente: borra cualquier tarea previa con el mismo nombre antes de
REM  crearla, asi puede correrse varias veces sin duplicar.
REM ============================================================================

echo.
echo === Configuracion Task Scheduler: CWK Autorepo (3 tareas) ===
echo.

REM ---------------------------------------------------------------------------
REM  1) Asegurar directorio de logs
REM ---------------------------------------------------------------------------
if not exist C:\cowork_pedidos\autorepo\logs (
    echo [*] Creando directorio de logs C:\cowork_pedidos\autorepo\logs
    mkdir C:\cowork_pedidos\autorepo\logs
) else (
    echo [=] Directorio de logs ya existe
)

echo.

REM ---------------------------------------------------------------------------
REM  2) Borrar tareas previas (idempotencia). || echo ok absorbe el error si
REM     la tarea no existe todavia.
REM ---------------------------------------------------------------------------
echo [*] Limpiando tareas previas (si existen)...
schtasks /Delete /TN "CWK_Autorepo_Urgente"    /F >nul 2>&1 || echo   - CWK_Autorepo_Urgente no existia (ok)
schtasks /Delete /TN "CWK_Autorepo_Rebalanceo" /F >nul 2>&1 || echo   - CWK_Autorepo_Rebalanceo no existia (ok)
schtasks /Delete /TN "CWK_Autorepo_Auditoria"  /F >nul 2>&1 || echo   - CWK_Autorepo_Auditoria no existia (ok)

echo.

REM ---------------------------------------------------------------------------
REM  3) Crear tarea URGENTE - diaria 07:00
REM ---------------------------------------------------------------------------
echo [*] Creando CWK_Autorepo_Urgente (DAILY 07:00)...
schtasks /Create ^
    /TN "CWK_Autorepo_Urgente" ^
    /TR "cmd /c py -3 C:\cowork_pedidos\autorepo_engine.py --modo urgente >> C:\cowork_pedidos\autorepo\logs\autorepo_urgente.log 2>&1" ^
    /SC DAILY ^
    /ST 07:00 ^
    /RU SYSTEM ^
    /RL HIGHEST ^
    /F

if errorlevel 1 (
    echo [!] ERROR creando CWK_Autorepo_Urgente
) else (
    echo [OK] CWK_Autorepo_Urgente creada
)

echo.

REM ---------------------------------------------------------------------------
REM  4) Crear tarea REBALANCEO - semanal jueves 18:00
REM ---------------------------------------------------------------------------
echo [*] Creando CWK_Autorepo_Rebalanceo (WEEKLY THU 18:00)...
schtasks /Create ^
    /TN "CWK_Autorepo_Rebalanceo" ^
    /TR "cmd /c py -3 C:\cowork_pedidos\autorepo_engine.py --modo rebalanceo >> C:\cowork_pedidos\autorepo\logs\autorepo_rebalanceo.log 2>&1" ^
    /SC WEEKLY ^
    /D THU ^
    /ST 18:00 ^
    /RU SYSTEM ^
    /RL HIGHEST ^
    /F

if errorlevel 1 (
    echo [!] ERROR creando CWK_Autorepo_Rebalanceo
) else (
    echo [OK] CWK_Autorepo_Rebalanceo creada
)

echo.

REM ---------------------------------------------------------------------------
REM  5) Crear tarea AUDITORIA - mensual dia 1, 09:00
REM ---------------------------------------------------------------------------
echo [*] Creando CWK_Autorepo_Auditoria (MONTHLY day 1 09:00)...
schtasks /Create ^
    /TN "CWK_Autorepo_Auditoria" ^
    /TR "cmd /c py -3 C:\cowork_pedidos\autorepo_engine.py --modo auditoria >> C:\cowork_pedidos\autorepo\logs\autorepo_auditoria.log 2>&1" ^
    /SC MONTHLY ^
    /D 1 ^
    /ST 09:00 ^
    /RU SYSTEM ^
    /RL HIGHEST ^
    /F

if errorlevel 1 (
    echo [!] ERROR creando CWK_Autorepo_Auditoria
) else (
    echo [OK] CWK_Autorepo_Auditoria creada
)

echo.
echo ============================================================================
echo  Verificacion: Query de las 3 tareas recien creadas
echo ============================================================================
echo.

echo --- CWK_Autorepo_Urgente ---
schtasks /Query /TN "CWK_Autorepo_Urgente"
echo.

echo --- CWK_Autorepo_Rebalanceo ---
schtasks /Query /TN "CWK_Autorepo_Rebalanceo"
echo.

echo --- CWK_Autorepo_Auditoria ---
schtasks /Query /TN "CWK_Autorepo_Auditoria"
echo.

echo ============================================================================
echo  Listo. Las 3 tareas quedaron programadas.
echo  Logs en: C:\cowork_pedidos\autorepo\logs\
echo ============================================================================

endlocal
exit /b 0

REM ============================================================================
REM  DESINSTALACION (copiar y pegar en CMD admin para remover las 3 tareas):
REM
REM    schtasks /Delete /TN "CWK_Autorepo_Urgente"    /F
REM    schtasks /Delete /TN "CWK_Autorepo_Rebalanceo" /F
REM    schtasks /Delete /TN "CWK_Autorepo_Auditoria"  /F
REM
REM  Para consultar manualmente el estado de una tarea:
REM    schtasks /Query /TN "CWK_Autorepo_Urgente" /V /FO LIST
REM
REM  Para disparar una corrida manual (util para debug, no espera al cron):
REM    schtasks /Run /TN "CWK_Autorepo_Urgente"
REM ============================================================================
