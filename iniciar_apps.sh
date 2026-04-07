#!/bin/bash
# ============================================================
# iniciar_apps.sh — Levanta todas las apps Streamlit
# Uso: bash iniciar_apps.sh
# Para detener todo: bash iniciar_apps.sh stop
# ============================================================

cd "$(dirname "$0")"
BASE_DIR="$(pwd)"
LOG_DIR="/tmp/streamlit_logs"
PID_DIR="/tmp/streamlit_pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

# Apps registradas: nombre|archivo|puerto|directorio
APPS=(
    "Carga Facturas|app_carga.py|8501|."
    "H4 Dashboard|app_h4.py|8502|."
    "Reposicion|app_reposicion.py|8503|."
    "Locales|app_locales.py|8504|."
    "Multicanal|app_multicanal.py|8505|."
)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

stop_all() {
    echo -e "${YELLOW}Deteniendo todas las apps...${NC}"
    for app in "${APPS[@]}"; do
        IFS='|' read -r name file port dir <<< "$app"
        pidfile="$PID_DIR/streamlit_${port}.pid"
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null
                echo -e "  ${RED}Detenida${NC} $name (puerto $port, PID $pid)"
            fi
            rm -f "$pidfile"
        fi
        # Matar cualquier proceso en ese puerto
        lsof -ti ":$port" 2>/dev/null | xargs kill -9 2>/dev/null
    done
    echo -e "${GREEN}Todo detenido.${NC}"
}

status() {
    echo -e "${YELLOW}Estado de las apps:${NC}"
    echo ""
    for app in "${APPS[@]}"; do
        IFS='|' read -r name file port dir <<< "$app"
        pid=$(lsof -ti ":$port" 2>/dev/null | head -1)
        if [ -n "$pid" ]; then
            echo -e "  ${GREEN}[RUNNING]${NC} $name — puerto $port (PID $pid)"
        else
            echo -e "  ${RED}[STOPPED]${NC} $name — puerto $port"
        fi
    done
    echo ""
}

start_all() {
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}  Iniciando apps Streamlit${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo ""

    for app in "${APPS[@]}"; do
        IFS='|' read -r name file port dir <<< "$app"

        # Verificar si ya está corriendo
        existing_pid=$(lsof -ti ":$port" 2>/dev/null | head -1)
        if [ -n "$existing_pid" ]; then
            echo -e "  ${GREEN}[OK]${NC} $name ya corre en puerto $port (PID $existing_pid)"
            continue
        fi

        # Verificar que el archivo existe
        app_path="$BASE_DIR/$dir/$file"
        if [ ! -f "$app_path" ]; then
            echo -e "  ${RED}[SKIP]${NC} $name — $app_path no existe"
            continue
        fi

        # Lanzar
        logfile="$LOG_DIR/${file%.py}.log"
        nohup streamlit run "$app_path" \
            --server.port "$port" \
            --server.headless true \
            --server.address 0.0.0.0 \
            > "$logfile" 2>&1 &

        pid=$!
        echo "$pid" > "$PID_DIR/streamlit_${port}.pid"
        sleep 1

        # Verificar que arrancó
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "  ${GREEN}[START]${NC} $name — puerto $port (PID $pid)"
        else
            echo -e "  ${RED}[FAIL]${NC} $name — ver $logfile"
        fi
    done

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Logs en: $LOG_DIR/${NC}"
    echo -e "${GREEN}========================================${NC}"
}

case "${1:-start}" in
    stop)   stop_all ;;
    status) status ;;
    restart) stop_all; sleep 2; start_all ;;
    *)      start_all ;;
esac
