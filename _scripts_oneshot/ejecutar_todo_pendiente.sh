#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# EJECUTAR TODO PENDIENTE — Diadora fix + Atomik RUNFLEX
# ═══════════════════════════════════════════════════════════════
# Este script:
#   1. Deploy al 111 (via deploy.sh)
#   2. Conecta al 111 y ejecuta los 2 scripts pendientes
#
# DESDE LA MAC:
#   cd ~/Desktop/cowork_pedidos/_scripts_oneshot
#   chmod +x ejecutar_todo_pendiente.sh
#   ./ejecutar_todo_pendiente.sh
# ═══════════════════════════════════════════════════════════════

set -e
ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
NC='\033[0m'

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  EJECUCIÓN COMPLETA: Fix Diadora + Alta Atomik RUNFLEX"
echo "═══════════════════════════════════════════════════════════"

# ── Paso 1: Deploy ──
echo ""
echo -e "${AMARILLO}[1/3] Desplegando scripts al 111...${NC}"
cd ~/Desktop/cowork_pedidos/_sync_tools
./deploy.sh scripts
echo -e "${VERDE}✓ Deploy completado${NC}"

# ── Paso 2: Fix Diadora (marca + grupo) ──
echo ""
echo -e "${AMARILLO}[2/3] Corrigiendo marca/grupo Diadora (614→675, PU→MACRAME)...${NC}"

# Ejecutar en el 111 vía SMB + py -3
# Primero verificar que el mount está
MOUNT="/Volumes/cowork_111"
if ! mount | grep -q "cowork_111"; then
    echo -e "${ROJO}✗ SMB no montado. Montando...${NC}"
    sudo mkdir -p "$MOUNT" 2>/dev/null
    sudo mount_smbfs '//administrador:cagr$2011@192.168.2.111/c$/cowork_pedidos' "$MOUNT"
fi

# No puedo ejecutar py -3 remotamente via SMB, necesito otro método
# Usando PowerShell remoto o el acceso directo
echo ""
echo -e "${AMARILLO}Abriendo sesión en el 111 para ejecutar scripts...${NC}"
echo ""
echo "════════════════════════════════════════════════════════"
echo "  COPIAR Y PEGAR EN LA TERMINAL DEL 111 (Escritorio Remoto):"
echo "════════════════════════════════════════════════════════"
echo ""
echo '  cd C:\cowork_pedidos\_scripts_oneshot'
echo '  py -3 fix_marca_diadora.py --ejecutar'
echo '  py -3 insertar_atomik_runflex.py --ejecutar'
echo ""
echo "════════════════════════════════════════════════════════"
echo ""
echo -e "${VERDE}Los scripts ya están en el servidor (paso 1 hizo deploy).${NC}"
echo -e "${VERDE}Solo falta ejecutar los 2 comandos de arriba en el 111.${NC}"
