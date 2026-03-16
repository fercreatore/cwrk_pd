#!/bin/bash
# ──────────────────────────────────────────────────────────
# Sincroniza calzalindo_freelance desde Mac → .112
# Uso:
#   ./sync_to_112.sh          → copia una vez
#   ./sync_to_112.sh --watch  → vigila cambios y copia automáticamente
# ──────────────────────────────────────────────────────────

REMOTE_IP="192.168.2.112"
REMOTE_USER="fer"
REMOTE_PATH="/c$/calzalindo_freelance"
MOUNT_POINT="/tmp/win112"

# Detectar ruta local (carpeta donde está este script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_PATH="$SCRIPT_DIR"

echo "═══ Sync calzalindo_freelance → $REMOTE_IP ═══"
echo "Local:  $LOCAL_PATH"
echo "Remoto: \\\\$REMOTE_IP\\c\$\\calzalindo_freelance"
echo ""

# ── Función: montar SMB si no está montado ────────────────
mount_share() {
    if mount | grep -q "$MOUNT_POINT"; then
        echo "✓ SMB ya montado en $MOUNT_POINT"
        return 0
    fi

    echo "Montando \\\\$REMOTE_IP\\c\$ ..."
    mkdir -p "$MOUNT_POINT"
    mount_smbfs "//$REMOTE_USER@$REMOTE_IP/c\$" "$MOUNT_POINT" 2>/dev/null

    if [ $? -ne 0 ]; then
        echo "Intentando con credenciales..."
        echo "Ingresá la contraseña de $REMOTE_USER en $REMOTE_IP:"
        mount_smbfs "//$REMOTE_USER@$REMOTE_IP/c\$" "$MOUNT_POINT"
    fi

    if mount | grep -q "$MOUNT_POINT"; then
        echo "✓ Montado OK"
        return 0
    else
        echo "✗ Error montando SMB. Probá manualmente:"
        echo "  Finder → Ir → Conectar al servidor → smb://$REMOTE_IP/c\$"
        return 1
    fi
}

# ── Función: copiar archivos ──────────────────────────────
sync_files() {
    echo "Copiando archivos..."

    rsync -av --delete \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.DS_Store' \
        --exclude 'sync_to_112.sh' \
        "$LOCAL_PATH/" "$MOUNT_POINT/calzalindo_freelance/"

    if [ $? -eq 0 ]; then
        echo "✓ Sync completo $(date '+%H:%M:%S')"
    else
        echo "✗ Error en sync"
    fi
}

# ── Main ──────────────────────────────────────────────────
mount_share || exit 1

if [ "$1" = "--watch" ]; then
    # Verificar que fswatch esté instalado
    if ! command -v fswatch &> /dev/null; then
        echo "Instalando fswatch (necesario para --watch)..."
        brew install fswatch
    fi

    echo ""
    echo "══ Modo vigilancia activo ══"
    echo "Cada cambio en $LOCAL_PATH se copia al .112 automáticamente."
    echo "Ctrl+C para detener."
    echo ""

    # Primera sync
    sync_files

    # Vigilar cambios
    fswatch -o \
        --exclude '__pycache__' \
        --exclude '\.pyc$' \
        --exclude '\.DS_Store' \
        "$LOCAL_PATH" | while read -r _; do
        echo ""
        echo "── Cambio detectado $(date '+%H:%M:%S') ──"
        sync_files
    done
else
    sync_files
fi
