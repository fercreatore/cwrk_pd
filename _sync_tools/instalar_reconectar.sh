#!/bin/bash
# =============================================================
# INSTALADOR: Configura la reconexión automática de red
# Uso: sudo ./instalar_reconectar.sh
# =============================================================

RED='\033[0;31m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.calzalindo.reconectar"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME.plist"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
SCRIPT_SRC="$SCRIPT_DIR/reconectar_auto.sh"

# LaunchAgent corre como tu usuario (NO necesita sudo)
mkdir -p "$HOME/Library/LaunchAgents" 2>/dev/null

echo -e "${CYAN}══════════════════════════════════${NC}"
echo -e "${CYAN}  Instalando reconexión automática${NC}"
echo -e "${CYAN}══════════════════════════════════${NC}"
echo ""

# 1. Permisos del script
echo -e "${YELLOW}1. Permisos del script...${NC}"
chmod +x "$SCRIPT_SRC"
echo -e "   ${GREEN}✓ $SCRIPT_SRC${NC}"

# 2. Descargar daemon anterior si existe
if launchctl list | grep -q "$PLIST_NAME" 2>/dev/null; then
    echo -e "${YELLOW}2. Descargando daemon anterior...${NC}"
    launchctl unload "$PLIST_DST" 2>/dev/null
    launchctl bootout system "$PLIST_DST" 2>/dev/null
    echo -e "   ${GREEN}✓ Descargado${NC}"
else
    echo -e "${YELLOW}2. No hay daemon previo${NC}"
fi

# 3. Copiar plist
echo -e "${YELLOW}3. Instalando plist...${NC}"
cp "$PLIST_SRC" "$PLIST_DST"
chmod 644 "$PLIST_DST"
echo -e "   ${GREEN}✓ $PLIST_DST${NC}"

# 4. Cargar daemon
echo -e "${YELLOW}4. Cargando daemon...${NC}"
launchctl load "$PLIST_DST"
echo -e "   ${GREEN}✓ Cargado${NC}"

echo ""
echo -e "${GREEN}══════════════════════════════════${NC}"
echo -e "${GREEN}  Instalación completa${NC}"
echo -e "${GREEN}══════════════════════════════════${NC}"
echo ""
echo -e "El daemon se activa cuando:"
echo -e "  • Cambiás de red WiFi"
echo -e "  • Conectás/desconectás cable ethernet"
echo -e "  • Cada 5 minutos (fallback)"
echo -e "  • Al iniciar la Mac"
echo ""
echo -e "Logs en: /tmp/reconectar_auto.log"
echo ""
echo -e "${YELLOW}Para desinstalar:${NC}"
echo -e "  sudo launchctl unload $PLIST_DST"
echo -e "  sudo rm $PLIST_DST"
