#!/bin/bash

################################################################################
# deploy_todo.sh — Master deployment para sistema freelance
#
# Sincroniza _freelance/src/ a .112 (FastAPI app) y SQL scripts a .111 (producción)
#
# Uso:
#   ./deploy_todo.sh                    # Deploy con confirmación
#   ./deploy_todo.sh --dryrun           # Ver qué se copiaría
#   ./deploy_todo.sh --force            # Deploy sin confirmación
#   ./deploy_todo.sh --sql-only         # Solo ejecutar SQL en .111 (manual)
#   ./deploy_todo.sh --app-only         # Solo copiar app a .112
#
# Requisitos:
#   - VPN L2TP conectado a ambos servidores
#   - SMB accesible para .111 (//administrador:cagr$2011@192.168.2.111/c$/cowork_pedidos)
#   - SMB accesible para .112 (fe@192.168.2.112/c$)
#   - rsync instalado
#
################################################################################

set -e

# ─────────────────────────────────────────────────────────────────────────────
# Color output
# ─────────────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
CYAN='\033[1;36m'
NC='\033[0m' # No Color

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
SERVER_112="192.168.2.112"
SERVER_111="192.168.2.111"
SMB_USER_111="administrador"
SMB_PASS_111="cagr\$2011"
SMB_USER_112="fer"

LOCAL_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOUNT_POINT_112="/Volumes/cowork_112"
MOUNT_POINT_111="/Volumes/cowork_111"

# Flags
DRYRUN=false
FORCE=false
SQL_ONLY=false
APP_ONLY=false

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

banner() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║ Deploy FREELANCE — Mac → .112 (app) + .111 (SQL)              ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_vpn() {
    local ip=$1
    local name=$2

    if ! ping -c 1 -W 2 "$ip" >/dev/null 2>&1; then
        echo -e "${RED}✗ Error: No se puede alcanzar $ip ($name)${NC}"
        echo "Verificar que VPN L2TP esté conectado."
        return 1
    fi
    echo -e "${GREEN}✓ $name ($ip) alcanzable${NC}"
    return 0
}

mount_smb() {
    local ip=$1
    local user=$2
    local pass=$3
    local mount_point=$4
    local share=$5

    if [ -d "$mount_point" ]; then
        if mount | grep -q "$mount_point"; then
            echo -e "${GREEN}✓ SMB ya montado en $mount_point${NC}"
            return 0
        fi
    fi

    echo -e "${YELLOW}Montando \\\\$ip\\$share...${NC}"
    mkdir -p "$mount_point"

    # Decode password (replace \$ with $)
    decoded_pass="${pass//\\$/\$}"

    if mount_smbfs "//${user}:${decoded_pass}@${ip}/${share}" "$mount_point" 2>/dev/null; then
        echo -e "${GREEN}✓ Montado OK en $mount_point${NC}"
        return 0
    else
        echo -e "${RED}✗ Error montando SMB en $mount_point${NC}"
        return 1
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────────────────────────────────────

for arg in "$@"; do
    case "$arg" in
        --dryrun)
            DRYRUN=true
            ;;
        --force)
            FORCE=true
            ;;
        --sql-only)
            SQL_ONLY=true
            ;;
        --app-only)
            APP_ONLY=true
            ;;
        *)
            echo -e "${RED}Error: argumento desconocido: $arg${NC}"
            echo "Uso: $0 [--dryrun] [--force] [--sql-only] [--app-only]"
            exit 1
            ;;
    esac
done

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

banner

# Check local source
if [ ! -d "$LOCAL_SRC" ]; then
    echo -e "${RED}Error: directorio local no encontrado: $LOCAL_SRC${NC}"
    exit 1
fi

echo -e "${BLUE}Configuración:${NC}"
echo "  Local source:       $LOCAL_SRC"
echo "  FastAPI (.112):     $SERVER_112 → $MOUNT_POINT_112"
echo "  SQL scripts (.111): $SERVER_111 → $MOUNT_POINT_111"
echo "  Flags: dryrun=$DRYRUN force=$FORCE sql_only=$SQL_ONLY app_only=$APP_ONLY"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Check VPN
# ─────────────────────────────────────────────────────────────────────────────

if [ "$SQL_ONLY" = false ]; then
    echo -e "${YELLOW}Verificando VPN a .112...${NC}"
    check_vpn "$SERVER_112" "DATASVRW" || exit 1
    echo ""
fi

if [ "$APP_ONLY" = false ]; then
    echo -e "${YELLOW}Verificando VPN a .111...${NC}"
    check_vpn "$SERVER_111" "DELL-SVR" || exit 1
    echo ""
fi

# ─────────────────────────────────────────────────────────────────────────────
# Deploy FastAPI app to .112 (unless --sql-only)
# ─────────────────────────────────────────────────────────────────────────────

if [ "$SQL_ONLY" = false ]; then
    echo -e "${BLUE}═══ PARTE 1: Deploy app a .112 (FastAPI) ═══${NC}"
    echo ""

    mount_smb "$SERVER_112" "$SMB_USER_112" "" "$MOUNT_POINT_112" "c\$" || exit 1
    echo ""

    RSYNC_OPTS=(
        -av
        --delete
        --exclude='__pycache__'
        --exclude='*.pyc'
        --exclude='*.pyo'
        --exclude='.DS_Store'
        --exclude='.git'
        --exclude='*.egg-info'
        --exclude='.pytest_cache'
        --exclude='deploy_112.sh'
        --exclude='sync_to_112.sh'
        --exclude='deploy_todo.sh'
        --exclude='sql'
    )

    if [ "$DRYRUN" = true ]; then
        RSYNC_OPTS+=("--dry-run")
    fi

    echo -e "${BLUE}Archivos a copiar a .112:${NC}"
    rsync "${RSYNC_OPTS[@]}" "$LOCAL_SRC/" "$MOUNT_POINT_112/calzalindo_freelance/" 2>&1 | head -30
    echo ""

    if [ "$DRYRUN" = true ]; then
        echo -e "${YELLOW}[DRYRUN] No se copió nada a .112. Use ./deploy_todo.sh para copiar.${NC}"
    else
        if [ "$FORCE" = false ]; then
            read -p "¿Copiar app a .112? (s/n) " -n 1 -r
            echo ""
            if [[ ! $REPLY =~ ^[Ss]$ ]]; then
                echo "Cancelado."
                exit 0
            fi
        fi

        echo -e "${YELLOW}Copiando app a .112...${NC}"
        rsync "${RSYNC_OPTS[@]}" "$LOCAL_SRC/" "$MOUNT_POINT_112/calzalindo_freelance/"
        echo -e "${GREEN}✓ App copiada a .112${NC}"
    fi

    echo ""
fi

# ─────────────────────────────────────────────────────────────────────────────
# Copy SQL scripts to .111 (unless --app-only)
# ─────────────────────────────────────────────────────────────────────────────

if [ "$APP_ONLY" = false ]; then
    echo -e "${BLUE}═══ PARTE 2: Copiar SQL scripts a .111 ═══${NC}"
    echo ""

    mount_smb "$SERVER_111" "$SMB_USER_111" "$SMB_PASS_111" "$MOUNT_POINT_111" "c\$/cowork_pedidos" || exit 1
    echo ""

    SQL_SRC="$LOCAL_SRC/sql"
    SQL_DEST="$MOUNT_POINT_111/_freelance/src/sql"

    if [ ! -d "$SQL_SRC" ]; then
        echo -e "${RED}Error: directorio SQL no encontrado: $SQL_SRC${NC}"
        exit 1
    fi

    echo -e "${BLUE}SQL scripts a copiar:${NC}"
    ls -lah "$SQL_SRC"/*.sql 2>/dev/null || echo "  (no SQL files found)"
    echo ""

    RSYNC_OPTS_SQL=(
        -av
        --include='*.sql'
        --exclude='*'
    )

    if [ "$DRYRUN" = true ]; then
        RSYNC_OPTS_SQL+=("--dry-run")
    fi

    mkdir -p "$SQL_DEST"
    rsync "${RSYNC_OPTS_SQL[@]}" "$SQL_SRC/" "$SQL_DEST/" || true

    if [ "$DRYRUN" = true ]; then
        echo -e "${YELLOW}[DRYRUN] No se copió nada a .111. Use ./deploy_todo.sh para copiar.${NC}"
    else
        if [ "$FORCE" = false ]; then
            read -p "¿Copiar SQL scripts a .111? (s/n) " -n 1 -r
            echo ""
            if [[ ! $REPLY =~ ^[Ss]$ ]]; then
                echo "Cancelado."
                exit 0
            fi
        fi

        echo -e "${YELLOW}Copiando SQL scripts a .111...${NC}"
        rsync "${RSYNC_OPTS_SQL[@]}" "$SQL_SRC/" "$SQL_DEST/"
        echo -e "${GREEN}✓ SQL scripts copiados a .111${NC}"
    fi

    echo ""
fi

# ─────────────────────────────────────────────────────────────────────────────
# Summary and next steps
# ─────────────────────────────────────────────────────────────────────────────

echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║ Deploy completado exitosamente                                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$SQL_ONLY" = false ]; then
    echo -e "${BLUE}Próximos pasos en .112 ($SERVER_112):${NC}"
    echo ""
    echo "1. SSH a .112 (si no está montado automáticamente):"
    echo -e "   ${YELLOW}ssh fer@$SERVER_112${NC}"
    echo ""
    echo "2. Reiniciar FastAPI uvicorn:"
    echo -e "   ${YELLOW}cd C:\\calzalindo_freelance${NC}"
    echo -e "   ${YELLOW}python -m pip install -r requirements.txt  # si es necesario${NC}"
    echo -e "   ${YELLOW}python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001${NC}"
    echo ""
    echo "3. Verificar:"
    echo -e "   ${YELLOW}curl http://$SERVER_112:8001/docs${NC}"
    echo ""
fi

if [ "$APP_ONLY" = false ]; then
    echo -e "${BLUE}SQL scripts a ejecutar en .111 ($SERVER_111):${NC}"
    echo ""
    echo "Ejecutar en SQL Server Management Studio o sqlcmd:"
    echo -e "   ${YELLOW}C:\\cowork_pedidos\\_freelance\\src\\sql\\RUN_ALL.sql${NC}"
    echo ""
    echo "Opcionalmente, en orden manual:"
    echo -e "   ${YELLOW}sqlcmd -S 192.168.2.111 -U am -P dl -d omicronvt -i C:\\cowork_pedidos\\_freelance\\src\\sql\\001_crear_tablas_freelance.sql${NC}"
    echo -e "   ${YELLOW}sqlcmd -S 192.168.2.111 -U am -P dl -d omicronvt -i C:\\cowork_pedidos\\_freelance\\src\\sql\\002_seed_data.sql${NC}"
    echo -e "   ${YELLOW}sqlcmd -S 192.168.2.111 -U am -P dl -d omicronvt -i C:\\cowork_pedidos\\_freelance\\src\\sql\\003_alta_mati.sql${NC}"
    echo ""
fi

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
