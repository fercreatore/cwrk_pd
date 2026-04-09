#!/bin/bash
# =============================================================
# lib_deploy.sh — Libreria compartida para todos los scripts de deploy
#
# Uso: source "$(dirname "$0")/lib_deploy.sh"
#
# Provee:
#   - Mount points estandarizados (~/mnt/)
#   - Credenciales desde ~/.cowork_creds (o fallback inline)
#   - _montar_share()     — monta un share SMB sin sudo
#   - _verificar_mount()  — test acceso real (no solo mount | grep)
#   - _verificar_deploy() — post-deploy: cuenta archivos y test lectura
#   - Colores para output
#   - SRC (directorio fuente)
# =============================================================

# --- Colores ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --- Directorio fuente ---
SRC="$HOME/Desktop/cowork_pedidos"

# --- Credenciales ---
# Leer de ~/.cowork_creds si existe, sino fallback a valores inline
if [ -f "$HOME/.cowork_creds" ]; then
    source "$HOME/.cowork_creds"
else
    SMB_USER="administrador"
    SMB_PASS='cagr$2011'
fi

# --- Mount points estandarizados ---
MOUNT_111="$HOME/mnt/cowork_111"
MOUNT_111_WEB2PY="$HOME/mnt/web2py_111"
MOUNT_112="$HOME/mnt/compartido_112"

# --- SMB URLs ---
SMB_URL_111="//${SMB_USER}:${SMB_PASS}@192.168.2.111/c\$/cowork_pedidos"
SMB_URL_111_WEB2PY="//${SMB_USER}:${SMB_PASS}@192.168.2.111/c\$/web2py_src/applications/calzalindo_informes"
SMB_URL_112="//${SMB_USER}:${SMB_PASS}@192.168.2.112/compartido"

# --- Extensiones a sincronizar ---
SYNC_EXTS=(*.py *.sql *.json *.md *.txt *.sh *.bat *.cfg *.toml *.plist)

# --- Montar un share SMB (sin sudo) ---
# Uso: _montar_share <mount_point> <smb_url> <label>
# Retorna 0 si OK, 1 si fallo
_montar_share() {
    local mount_point="$1"
    local smb_url="$2"
    local label="$3"

    # Si es un symlink (puesto por reconectar_auto), verificar que el target exista
    if [ -L "$mount_point" ]; then
        local target=$(readlink "$mount_point")
        if [ -d "$target" ] && [ "$(ls -A "$target" 2>/dev/null)" ]; then
            echo -e "${GREEN}+ $label OK (via symlink → $target)${NC}"
            return 0
        else
            # Symlink roto, remover e intentar mount directo
            rm -f "$mount_point"
        fi
    fi

    # Crear directorio si no existe
    mkdir -p "$mount_point" 2>/dev/null

    # Intentar montar
    mount_smbfs "$smb_url" "$mount_point" 2>/dev/null
    local rc=$?

    if [ $rc -eq 0 ]; then
        echo -e "${GREEN}+ $label montado OK${NC}"
        return 0
    fi

    # Ya montado? Verificar acceso real
    if _verificar_mount "$mount_point"; then
        echo -e "${GREEN}+ $label ya montado${NC}"
        return 0
    fi

    echo -e "${RED}x Error montando $label. Esta encendido el servidor?${NC}"
    return 1
}

# --- Verificar que un mount point es accesible (no stale) ---
# Uso: _verificar_mount <mount_point>
# Retorna 0 si accesible, 1 si no
_verificar_mount() {
    local mount_point="$1"

    # macOS no tiene 'timeout', usar perl one-liner como fallback
    local content
    content=$(perl -e 'alarm 3; exec @ARGV' ls -A "$mount_point" 2>/dev/null)
    if [ -n "$content" ]; then
        return 0
    fi
    return 1
}

# --- Verificacion post-deploy ---
# Uso: _verificar_deploy <src_dir> <dest_dir> <label>
_verificar_deploy() {
    local src_dir="$1"
    local dest_dir="$2"
    local label="$3"

    if ! _verificar_mount "$dest_dir"; then
        echo -e "${RED}x Verificacion $label: mount no accesible${NC}"
        return 1
    fi

    # Contar .py en origen y destino
    local src_count=$(find "$src_dir" -name "*.py" -type f 2>/dev/null | wc -l | tr -d ' ')
    local dest_count=$(find "$dest_dir" -name "*.py" -type f 2>/dev/null | wc -l | tr -d ' ')

    if [ "$src_count" -gt 0 ] && [ "$dest_count" -gt 0 ]; then
        echo -e "${GREEN}+ Verificacion $label: $dest_count .py en destino (origen: $src_count)${NC}"
    elif [ "$dest_count" -eq 0 ]; then
        echo -e "${YELLOW}! Verificacion $label: 0 archivos .py en destino${NC}"
    fi

    # Test de lectura rapido
    local test_file=$(find "$dest_dir" -name "*.py" -type f 2>/dev/null | head -1)
    if [ -n "$test_file" ]; then
        if perl -e 'alarm 3; exec @ARGV' head -1 "$test_file" &>/dev/null; then
            echo -e "${GREEN}+ Test lectura OK${NC}"
        else
            echo -e "${RED}x Test lectura fallo (mount stale?)${NC}"
            return 1
        fi
    fi

    return 0
}

# --- Build rsync include flags desde SYNC_EXTS ---
build_include_flags() {
    local flags=""
    for ext in "${SYNC_EXTS[@]}"; do
        flags="$flags --include=$ext"
    done
    echo "$flags"
}
