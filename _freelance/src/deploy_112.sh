#!/bin/bash

################################################################################
# deploy_112.sh — Deploy FastAPI app a DATASVRW (192.168.2.112)
#
# Uso:
#   ./deploy_112.sh                    # Deploy con confirmacion
#   ./deploy_112.sh --dryrun           # Ver qué se copiaría
#   ./deploy_112.sh --force            # Deploy sin confirmacion
#
# Requisitos:
#   - VPN L2TP conectado
#   - Credenciales SMB en Keychain o variables de entorno
#   - rsync instalado
#
################################################################################

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Config
SERVER_IP="192.168.2.112"
SERVER_USER="administrador"
REMOTE_PATH="C:/calzalindo_freelance"
LOCAL_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Mount point on Mac
MOUNT_POINT="/Volumes/cowork_112"

# Flags
DRYRUN=false
FORCE=false

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║ Deploy FastAPI — DATASVRW (192.168.2.112)                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --dryrun)
            DRYRUN=true
            ;;
        --force)
            FORCE=true
            ;;
        *)
            echo -e "${RED}Error: argumento desconocido: $arg${NC}"
            echo "Uso: $0 [--dryrun] [--force]"
            exit 1
            ;;
    esac
done

# Check local source
if [ ! -d "$LOCAL_SRC" ]; then
    echo -e "${RED}Error: directorio local no encontrado: $LOCAL_SRC${NC}"
    exit 1
fi

echo -e "${BLUE}Configuración:${NC}"
echo "  Servidor:     $SERVER_IP"
echo "  Ruta remota:  $REMOTE_PATH"
echo "  Ruta local:   $LOCAL_SRC"
echo "  Mount point:  $MOUNT_POINT"
echo ""

# Check VPN
echo -e "${YELLOW}Verificando VPN...${NC}"
if ! ping -c 1 -W 2 "$SERVER_IP" >/dev/null 2>&1; then
    echo -e "${RED}Error: No se puede alcanzar $SERVER_IP${NC}"
    echo "Verificar que VPN L2TP esté conectado."
    exit 1
fi
echo -e "${GREEN}✓ VPN OK${NC}"
echo ""

# Try to mount SMB if not already mounted
if [ ! -d "$MOUNT_POINT" ]; then
    echo -e "${YELLOW}Montando SMB...${NC}"

    # Read password from Keychain or prompt
    if [ -z "$SMB_PASSWORD" ]; then
        read -sp "Contraseña SMB para $SERVER_USER: " SMB_PASSWORD
        echo ""
    fi

    mkdir -p "$MOUNT_POINT"

    mount_smbfs "//administrador:cagr\$2011@192.168.2.111/c\$/cowork_pedidos" "$MOUNT_POINT" 2>/dev/null || {
        # Try with alternate credentials
        mount_smbfs "//${SERVER_USER}:${SMB_PASSWORD}@${SERVER_IP}/c\$/calzalindo_freelance" "$MOUNT_POINT" || {
            echo -e "${RED}Error: No se puede montar SMB${NC}"
            exit 1
        }
    }
    echo -e "${GREEN}✓ SMB montado${NC}"
else
    echo -e "${GREEN}✓ SMB ya está montado${NC}"
fi
echo ""

# Build rsync command
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
)

if [ "$DRYRUN" = true ]; then
    RSYNC_OPTS+=("--dry-run")
fi

# Show what will be copied
echo -e "${BLUE}Archivos a copiar:${NC}"
rsync "${RSYNC_OPTS[@]}" "$LOCAL_SRC/" "$MOUNT_POINT/" 2>&1 | grep -v "^sending\|^receiving\|^total" | head -20
echo ""

if [ "$DRYRUN" = true ]; then
    echo -e "${YELLOW}[DRYRUN] No se copió nada. Use ./deploy_112.sh para copiar.${NC}"
    exit 0
fi

# Confirm unless --force
if [ "$FORCE" = false ]; then
    read -p "¿Copiar estos archivos? (s/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        echo "Cancelado."
        exit 0
    fi
fi

# Perform rsync
echo -e "${YELLOW}Copiando archivos...${NC}"
rsync "${RSYNC_OPTS[@]}" "$LOCAL_SRC/" "$MOUNT_POINT/"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║ Deploy completado exitosamente                                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Próximos pasos en el servidor ($SERVER_IP):${NC}"
echo ""
echo "1. Opción A — Iniciar manualmente:"
echo -e "   ${YELLOW}cd C:\\calzalindo_freelance${NC}"
echo -e "   ${YELLOW}.\\start_freelance.bat${NC}"
echo ""
echo "2. Opción B — Instalar como servicio Windows:"
echo -e "   ${YELLOW}cd C:\\calzalindo_freelance${NC}"
echo -e "   ${YELLOW}.\\install_service.bat${NC}"
echo "   (ejecutar como Administrator)"
echo ""
echo "3. Verificar:"
echo -e "   ${YELLOW}http://$SERVER_IP:8001${NC}"
echo ""
