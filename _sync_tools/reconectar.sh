#!/bin/bash
# =============================================================
# RECONECTAR: Remonta todos los SMB después de cambio de red
# Uso: ./reconectar.sh
# =============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

CREDS='administrador:cagr$2011'

# --- Definir mounts ---
# Agregar nuevas entradas acá si necesitás más shares
declare -a MOUNTS=(
    "/Volumes/cowork_111|//\${CREDS}@192.168.2.111/c$/cowork_pedidos"
    "/Volumes/compartido|//\${CREDS}@192.168.2.112/compartido"
)

echo -e "${CYAN}==============================${NC}"
echo -e "${CYAN}  RECONEXIÓN DE RED${NC}"
echo -e "${CYAN}==============================${NC}"
echo ""

# --- 1. Verificar conectividad ---
echo -e "${YELLOW}Verificando conectividad...${NC}"
for ip in 192.168.2.111 192.168.2.112; do
    if ping -c 1 -W 2 "$ip" &>/dev/null; then
        echo -e "  ${GREEN}✓ $ip alcanzable${NC}"
    else
        echo -e "  ${RED}✗ $ip NO responde — ¿estás en la red correcta?${NC}"
        echo -e "  ${RED}  Abortando.${NC}"
        exit 1
    fi
done
echo ""

# --- 2. Desmontar los que quedaron colgados ---
echo -e "${YELLOW}Limpiando mounts viejos...${NC}"
for entry in "${MOUNTS[@]}"; do
    MOUNT_POINT="${entry%%|*}"
    if mount | grep -q "$MOUNT_POINT"; then
        sudo umount -f "$MOUNT_POINT" 2>/dev/null
        echo -e "  ${YELLOW}⏏ Desmontado $MOUNT_POINT${NC}"
    fi
done
echo ""

# --- 3. Montar todo ---
echo -e "${YELLOW}Montando shares...${NC}"
OK=0
FAIL=0

for entry in "${MOUNTS[@]}"; do
    MOUNT_POINT="${entry%%|*}"
    SMB_URL="${entry##*|}"

    # Expandir credenciales
    SMB_URL=$(eval echo "$SMB_URL")

    sudo mkdir -p "$MOUNT_POINT" 2>/dev/null

    if sudo mount_smbfs "$SMB_URL" "$MOUNT_POINT" 2>/dev/null; then
        echo -e "  ${GREEN}✓ $MOUNT_POINT → OK${NC}"
        ((OK++))
    else
        echo -e "  ${RED}✗ $MOUNT_POINT → FALLÓ${NC}"
        ((FAIL++))
    fi
done

echo ""
echo -e "${CYAN}==============================${NC}"
if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}  Todo reconectado ($OK shares)${NC}"
else
    echo -e "${YELLOW}  $OK OK / $FAIL fallaron${NC}"
fi
echo -e "${CYAN}==============================${NC}"

# --- 4. Test rápido de lectura ---
echo ""
echo -e "${YELLOW}Test de acceso:${NC}"
for entry in "${MOUNTS[@]}"; do
    MOUNT_POINT="${entry%%|*}"
    if sudo ls "$MOUNT_POINT" &>/dev/null; then
        echo -e "  ${GREEN}✓ $MOUNT_POINT legible${NC}"
    else
        echo -e "  ${RED}✗ $MOUNT_POINT sin acceso${NC}"
    fi
done
