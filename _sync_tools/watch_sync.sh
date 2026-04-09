#!/bin/bash
# watch_sync.sh — Vigila cambios en cowork_pedidos y sincroniza al 111
#
# Usa polling nativo de macOS (no necesita fswatch ni brew)
#
# USO:
#   ./watch_sync.sh          <- corre en primer plano
#   ./watch_sync.sh &        <- corre en background
#   ./watch_sync.sh stop     <- detiene el watcher

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib_deploy.sh"

PIDFILE="/tmp/cowork_sync_watcher.pid"
LOGFILE="$SRC/sync_watch.log"
DEBOUNCE=3  # segundos entre checks

# --- Comando: stop ---
if [ "$1" = "stop" ]; then
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        kill "$PID" 2>/dev/null && echo "Watcher detenido (PID $PID)" || echo "El watcher no estaba corriendo"
        rm -f "$PIDFILE"
    else
        echo "No hay watcher corriendo"
    fi
    exit 0
fi

# --- Montar si no esta montado ---
_montar_share "$MOUNT_111" "$SMB_URL_111" "cowork_pedidos (111)" || exit 1

# --- Verificar escritura ---
if [ ! -w "$MOUNT_111" ]; then
    echo -e "${RED}ERROR: No se puede escribir en $MOUNT_111${NC}"
    exit 1
fi

# --- Evitar doble ejecucion ---
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Ya hay un watcher corriendo (PID $OLD_PID). Usa './watch_sync.sh stop' para detenerlo."
        exit 1
    fi
fi

echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"; echo "Watcher detenido."; exit 0' INT TERM EXIT

echo "=========================================="
echo " COWORK SYNC WATCHER"
echo " Vigilando: $SRC"
echo " Destino:   $MOUNT_111"
echo " PID:       $$"
echo " Log:       $LOGFILE"
echo "=========================================="
echo ""

do_sync() {
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$TIMESTAMP] Sincronizando..." | tee -a "$LOGFILE"

    # Solo codigo (NO .xlsx — ver CLAUDE.md regla de no rsync pesados)
    rsync -av --include='*.py' --include='*.md' --include='*.sql' --include='*.json' \
          --include='*.txt' --include='*.sh' --include='*.bat' \
          --include='*/' --exclude='*' \
          "$SRC/" "$MOUNT_111/" 2>&1 | tee -a "$LOGFILE"

    echo "[$TIMESTAMP] Sync completo." | tee -a "$LOGFILE"
    echo "---" >> "$LOGFILE"
}

# Sync inicial
echo "Sync inicial..."
do_sync

# --- Loop de vigilancia ---
LAST_HASH=""

while true; do
    sleep "$DEBOUNCE"

    # Verificar que el share sigue montado
    if ! _verificar_mount "$MOUNT_111"; then
        echo "[$(date '+%H:%M:%S')] AVISO: Share desmontado. Intentando remontar..."
        _montar_share "$MOUNT_111" "$SMB_URL_111" "cowork_pedidos (111)" 2>/dev/null
        if ! _verificar_mount "$MOUNT_111"; then
            echo "[$(date '+%H:%M:%S')] No se pudo remontar. Esperando 30s..."
            sleep 30
            continue
        fi
        echo "[$(date '+%H:%M:%S')] Share reconectado."
    fi

    # Hash de archivos relevantes (nombre + tamano + fecha modif)
    # Solo codigo, NO xlsx
    CURRENT_HASH=$(find "$SRC" \( -name '*.py' -o -name '*.md' -o -name '*.sql' -o -name '*.json' \) \
                   -not -path '*/.claude/*' -not -path '*/__pycache__/*' \
                   -exec stat -f '%N %z %m' {} \; 2>/dev/null | sort | md5)

    if [ "$CURRENT_HASH" != "$LAST_HASH" ]; then
        if [ -n "$LAST_HASH" ]; then
            echo ""
            echo "[$(date '+%H:%M:%S')] Cambio detectado!"
            do_sync
        fi
        LAST_HASH="$CURRENT_HASH"
    fi
done
