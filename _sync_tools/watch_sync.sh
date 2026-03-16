#!/bin/bash
# watch_sync.sh — Vigila cambios en cowork_pedidos y sincroniza al 111 automáticamente
#
# Usa kqueue nativo de macOS (no necesita fswatch ni brew)
#
# USO:
#   chmod +x watch_sync.sh
#   ./watch_sync.sh          ← corre en primer plano (ver logs en consola)
#   ./watch_sync.sh &        ← corre en background
#   ./watch_sync.sh stop     ← detiene el watcher
#
# REQUISITO: El share debe estar montado previamente:
#   sudo mount_smbfs '//administrador:cagr$2011@192.168.2.111/c$/cowork_pedidos' /Volumes/cowork_111

MAC_DIR="$HOME/Desktop/cowork_pedidos"
SVR_DIR="/Volumes/cowork_111"
PIDFILE="/tmp/cowork_sync_watcher.pid"
LOGFILE="$MAC_DIR/sync_watch.log"
DEBOUNCE=3  # segundos de espera para agrupar cambios rápidos

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

# --- Verificar share montado ---
if ! mount | grep -q "cowork_111"; then
    echo "ERROR: El share no está montado en /Volumes/cowork_111"
    echo "Ejecutá primero:"
    echo "  sudo mount_smbfs '//administrador:cagr\$2011@192.168.2.111/c\$/cowork_pedidos' /Volumes/cowork_111"
    exit 1
fi

# --- Verificar escritura ---
if [ ! -w "$SVR_DIR" ]; then
    echo "ERROR: No se puede escribir en $SVR_DIR"
    exit 1
fi

# --- Evitar doble ejecución ---
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Ya hay un watcher corriendo (PID $OLD_PID). Usá './watch_sync.sh stop' para detenerlo."
        exit 1
    fi
fi

# Guardar PID
echo $$ > "$PIDFILE"

# Limpiar al salir
trap 'rm -f "$PIDFILE"; echo "Watcher detenido."; exit 0' INT TERM EXIT

echo "=========================================="
echo " COWORK SYNC WATCHER"
echo " Vigilando: $MAC_DIR"
echo " Destino:   $SVR_DIR"
echo " PID:       $$"
echo " Log:       $LOGFILE"
echo "=========================================="
echo ""

do_sync() {
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$TIMESTAMP] Sincronizando..." | tee -a "$LOGFILE"

    rsync -av --include='*.py' --include='*.md' --include='*.sql' --include='*.xlsx' \
          --include='*/' --exclude='*' \
          "$MAC_DIR/" "$SVR_DIR/" 2>&1 | tee -a "$LOGFILE"

    echo "[$TIMESTAMP] Sync completo." | tee -a "$LOGFILE"
    echo "---" >> "$LOGFILE"
}

# Sync inicial
echo "Sync inicial..."
do_sync

# --- Loop de vigilancia ---
# Usa polling cada N segundos comparando checksums (compatible con cualquier macOS)
LAST_HASH=""

while true; do
    sleep "$DEBOUNCE"

    # Verificar que el share sigue montado
    if ! mount | grep -q "cowork_111"; then
        echo "[$(date '+%H:%M:%S')] AVISO: Share desmontado. Esperando reconexión..."
        while ! mount | grep -q "cowork_111"; do
            sleep 10
        done
        echo "[$(date '+%H:%M:%S')] Share reconectado."
    fi

    # Calcular hash de archivos relevantes (nombre + tamaño + fecha modif)
    CURRENT_HASH=$(find "$MAC_DIR" \( -name '*.py' -o -name '*.md' -o -name '*.sql' -o -name '*.xlsx' \) \
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
