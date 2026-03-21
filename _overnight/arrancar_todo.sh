#!/usr/bin/env bash
# =============================================================================
# arrancar_todo.sh — Un solo comando para lanzar todo el sistema overnight
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         CLAUDE OVERNIGHT — ARRANQUE COMPLETO                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# --- 1. Verificar/instalar tmux ---
echo -e "${YELLOW}[1/5] Verificando tmux...${NC}"
if ! command -v tmux &>/dev/null; then
    echo "  tmux no encontrado. Instalando..."
    if command -v brew &>/dev/null; then
        brew install tmux
    else
        echo -e "${RED}ERROR: tmux no instalado y brew no disponible.${NC}"
        echo "  Instalá tmux manualmente: brew install tmux"
        exit 1
    fi
fi
echo -e "  ${GREEN}tmux $(tmux -V) ✓${NC}"

# --- 2. Verificar claude ---
echo -e "${YELLOW}[2/5] Verificando claude CLI...${NC}"
if ! command -v claude &>/dev/null; then
    echo -e "${RED}ERROR: claude CLI no encontrado en PATH${NC}"
    echo "  Instalá Claude Code: npm install -g @anthropic-ai/claude-code"
    exit 1
fi
echo -e "  ${GREEN}claude CLI encontrado ✓${NC}"

# --- 3. Verificar projects.conf ---
echo -e "${YELLOW}[3/5] Verificando configuración...${NC}"
if [[ ! -f "$SCRIPT_DIR/projects.conf" ]]; then
    echo -e "${RED}ERROR: No existe $SCRIPT_DIR/projects.conf${NC}"
    exit 1
fi

# Mostrar proyectos configurados
echo "  Proyectos configurados:"
while IFS='|' read -r name dir bitacora; do
    [[ "$name" =~ ^#.*$ ]] && continue
    [[ -z "$name" ]] && continue
    name=$(echo "$name" | xargs)
    dir=$(echo "$dir" | xargs)
    dir="${dir/#\~/$HOME}"
    if [[ -d "$dir" ]]; then
        echo -e "    ${GREEN}✓${NC} $name → $dir"
    else
        echo -e "    ${RED}✗${NC} $name → $dir (NO EXISTE)"
    fi
done < "$SCRIPT_DIR/projects.conf"

# --- 4. Matar orquestador anterior si existe ---
echo -e "${YELLOW}[4/5] Limpiando sesiones anteriores...${NC}"
if tmux has-session -t orquestador 2>/dev/null; then
    echo "  Matando orquestador anterior..."
    tmux kill-session -t orquestador 2>/dev/null || true
fi
# Matar sesiones de proyectos anteriores
while IFS='|' read -r name dir bitacora; do
    [[ "$name" =~ ^#.*$ ]] && continue
    [[ -z "$name" ]] && continue
    name=$(echo "$name" | xargs)
    tmux kill-session -t "$name" 2>/dev/null || true
done < "$SCRIPT_DIR/projects.conf"
echo -e "  ${GREEN}Limpio ✓${NC}"

# --- 5. Lanzar todo ---
echo -e "${YELLOW}[5/5] Lanzando orquestador + caffeinate...${NC}"

# caffeinate en background para mantener Mac despierta
caffeinate -i -w $$ &
CAFFEINATE_PID=$!
echo "  caffeinate PID: $CAFFEINATE_PID (Mac no dormirá)"

# Crear directorio de logs
mkdir -p "$SCRIPT_DIR/logs"

# Lanzar orquestador en sesión tmux propia
tmux new-session -d -s orquestador -c "$SCRIPT_DIR" \
    "bash '$SCRIPT_DIR/orquestador.sh' 2>&1 | tee -a '$SCRIPT_DIR/orquestador.log'"

echo -e "  ${GREEN}Orquestador lanzado en tmux sesión 'orquestador' ✓${NC}"

# --- Dashboard ---
sleep 8  # esperar a que se lancen los agentes

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗"
echo "║                    DASHBOARD                                ║"
echo "╠══════════════════════════════════════════════════════════════╣${NC}"
echo ""
echo "  Sesiones tmux activas:"
tmux list-sessions 2>/dev/null | while read -r line; do
    echo "    $line"
done

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}Comandos útiles:${NC}"
echo ""
echo "    Ver orquestador:    tmux attach -t orquestador"
echo "    Ver proyecto:       tmux attach -t cowork_pedidos"
echo "    Status rápido:      bash $SCRIPT_DIR/orquestador.sh --status"
echo "    Ver log:            tail -f $SCRIPT_DIR/orquestador.log"
echo "    Ver log proyecto:   tail -f $SCRIPT_DIR/logs/cowork_pedidos.log"
echo "    Parar todo:         tmux kill-server"
echo ""
echo -e "${GREEN}Todo lanzado. Podés cerrar esta terminal.${NC}"
echo -e "${GREEN}Los agentes seguirán corriendo en tmux + caffeinate.${NC}"
