#!/bin/bash
# sync_to_111.sh — Sincroniza cowork_pedidos del Mac al servidor 111
#
# USO:
#   chmod +x sync_to_111.sh
#   ./sync_to_111.sh              ← sync completo
#   ./sync_to_111.sh archivo.py   ← sync un solo archivo
#
# Si el share no está montado, el script lo monta con sudo.
# Primera vez: sudo mkdir -p /Volumes/cowork_111

MAC_DIR="$HOME/Desktop/cowork_pedidos"
SVR_DIR="/Volumes/cowork_111"

# Verificar si el share ya está montado (chequeando mount activo, no solo directorio)
if mount | grep -q "cowork_111"; then
    echo "Share ya montado en $SVR_DIR"
else
    echo "El share no está montado. Montando (requiere sudo)..."
    sudo mkdir -p "$SVR_DIR" 2>/dev/null
    sudo mount_smbfs '//administrador:cagr$2011@192.168.2.111/c$/cowork_pedidos' "$SVR_DIR"
    if [ $? -ne 0 ]; then
        echo "ERROR: No se pudo montar. Verificar red/credenciales."
        echo "  Manual: sudo mount_smbfs '//administrador:cagr\$2011@192.168.2.111/c\$/cowork_pedidos' $SVR_DIR"
        exit 1
    fi
    echo "Montado OK."
fi

# Verificar que se puede escribir
if [ ! -w "$SVR_DIR" ]; then
    echo "ERROR: No se puede escribir en $SVR_DIR"
    exit 1
fi

if [ -n "$1" ]; then
    # Sync un solo archivo
    echo "Copiando $1..."
    cp "$MAC_DIR/$1" "$SVR_DIR/$1"
    echo "OK: $1 → 111"
else
    # Sync todos los .py y .md
    echo "Sincronizando cowork_pedidos → 111..."
    rsync -av --include='*.py' --include='*.md' --include='*.sql' --include='*.xlsx' \
          --include='*/' --exclude='*' \
          "$MAC_DIR/" "$SVR_DIR/"
    echo ""
    echo "Sync completo."
fi
