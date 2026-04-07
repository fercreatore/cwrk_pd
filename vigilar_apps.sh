#!/bin/bash
# ============================================================
# vigilar_apps.sh — Watchdog que verifica y reinicia apps caídas
# Uso: bash vigilar_apps.sh
#   Corre en loop infinito, revisa cada 60 segundos.
#   Ctrl+C para detener.
#
# Para correr en background:
#   nohup bash vigilar_apps.sh > /tmp/vigilar_apps.log 2>&1 &
# ============================================================

cd "$(dirname "$0")"
BASE_DIR="$(pwd)"
LOG_DIR="/tmp/streamlit_logs"
mkdir -p "$LOG_DIR"

INTERVAL=60  # segundos entre checks

# Apps: nombre|archivo|puerto
APPS=(
    "Carga Facturas|app_carga.py|8501"
    "H4 Dashboard|app_h4.py|8502"
    "Reposicion|app_reposicion.py|8503"
    "Locales|app_locales.py|8504"
    "Multicanal|app_multicanal.py|8505"
)

check_and_restart() {
    local name="$1" file="$2" port="$3"
    local app_path="$BASE_DIR/$file"

    # Verificar si está corriendo
    pid=$(lsof -ti ":$port" 2>/dev/null | head -1)

    if [ -n "$pid" ]; then
        return 0  # OK, está viva
    fi

    # No está corriendo — reiniciar
    if [ ! -f "$app_path" ]; then
        return 1  # archivo no existe
    fi

    logfile="$LOG_DIR/${file%.py}.log"
    nohup streamlit run "$app_path" \
        --server.port "$port" \
        --server.headless true \
        --server.address 0.0.0.0 \
        > "$logfile" 2>&1 &

    new_pid=$!
    sleep 2

    if kill -0 "$new_pid" 2>/dev/null; then
        echo "[$(date '+%H:%M:%S')] REINICIADA: $name en puerto $port (PID $new_pid)"
    else
        echo "[$(date '+%H:%M:%S')] FALLO REINICIO: $name — ver $logfile"
    fi
}

echo "========================================"
echo "  Vigilante de apps Streamlit"
echo "  Revisando cada ${INTERVAL}s"
echo "  $(date)"
echo "========================================"
echo ""

while true; do
    restarted=0
    for app in "${APPS[@]}"; do
        IFS='|' read -r name file port <<< "$app"
        check_and_restart "$name" "$file" "$port"
        if [ $? -eq 0 ]; then
            : # ok
        fi
    done
    sleep "$INTERVAL"
done
