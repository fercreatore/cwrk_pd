#!/bin/bash
# =============================================================
# DEPLOY RÁPIDO: Mac → Servidor 111
# Uso: ./deploy.sh [componente]
# Componentes: scripts, web2py, todo
#
# REGLA GENERAL: Solo se sincronizan archivos de código y datos
# livianos (.py, .sql, .json, .md, .txt). NUNCA archivos pesados
# (.xlsx, .zip, .pdf, imágenes, etc.).
#
# Para agregar un archivo pesado puntual:
#   ./deploy.sh archivo _scripts_oneshot/mi_archivo.xlsx
# =============================================================

MOUNT="/Volumes/cowork_111"
SMB_URL='//administrador:cagr$2011@192.168.2.111/c$/cowork_pedidos'
SRC="$HOME/Desktop/cowork_pedidos"
WEB2PY="$MOUNT/../web2py_src/applications/calzalindo_informes"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Extensiones que se sincronizan (código + datos livianos)
SYNC_EXTS=(*.py *.sql *.json *.md *.txt *.sh *.bat *.cfg *.toml *.plist)

# --- Verificar/montar SMB ---
montar() {
    if mount | grep -q "cowork_111"; then
        echo -e "${GREEN}✓ SMB ya montado${NC}"
    else
        echo -e "${YELLOW}Montando SMB...${NC}"
        sudo mkdir -p "$MOUNT" 2>/dev/null
        sudo mount_smbfs "$SMB_URL" "$MOUNT"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Montado OK${NC}"
        else
            echo -e "${RED}✗ Error montando. ¿Está encendido el servidor?${NC}"
            exit 1
        fi
    fi
}

build_include_flags() {
    local flags=""
    for ext in "${SYNC_EXTS[@]}"; do
        flags="$flags --include=$ext"
    done
    echo "$flags"
}

# --- Deploy web2py (calzalindo_informes) ---
deploy_web2py() {
    echo -e "${YELLOW}--- Deploy calzalindo_informes ---${NC}"
    sudo rsync -av \
        "$SRC/_informes/calzalindo_informes_DEPLOY/" \
        "$WEB2PY/"
    echo -e "${GREEN}✓ Web2py desplegado. RECORDÁ reiniciar web2py en el servidor.${NC}"
}

# --- Deploy scripts (pipeline + oneshot) ---
deploy_scripts() {
    echo -e "${YELLOW}--- Deploy scripts a C:\\cowork_pedidos ---${NC}"
    local INCLUDES=$(build_include_flags)

    # 1) _scripts_oneshot/
    echo -e "${CYAN}  _scripts_oneshot/${NC}"
    eval sudo rsync -av $INCLUDES --include='*/' --exclude='*' \
        "\"$SRC/_scripts_oneshot/\"" "\"$MOUNT/_scripts_oneshot/\""

    # 2) Raíz (pipeline core) — SOLO archivos de raíz, sin descender a subcarpetas
    #    Excluye explícitamente carpetas grandes que NO son pipeline
    echo -e "${CYAN}  raíz (pipeline core)${NC}"
    eval sudo rsync -av $INCLUDES \
        --exclude='_*' --exclude='.*' \
        --exclude='clz_wpu/' \
        --exclude='compras/' \
        --exclude='valijas/' \
        --exclude='tests/' \
        --include='*/' --exclude='*' \
        "\"$SRC/\"" "\"$MOUNT/\""

    # Resumen de lo transferido
    echo ""
    echo -e "${GREEN}✓ Scripts desplegados en C:\\cowork_pedidos${NC}"
    echo -e "${CYAN}  Extensiones sync: ${SYNC_EXTS[*]}${NC}"
}

# --- Deploy archivo individual ---
deploy_archivo() {
    local ARCHIVO="$1"
    if [ -z "$ARCHIVO" ]; then
        echo -e "${RED}✗ Falta nombre de archivo. Uso: ./deploy.sh archivo ruta/al/archivo${NC}"
        exit 1
    fi
    if [ ! -f "$SRC/$ARCHIVO" ]; then
        echo -e "${RED}✗ No existe: $SRC/$ARCHIVO${NC}"
        exit 1
    fi
    local DIR=$(dirname "$ARCHIVO")
    sudo mkdir -p "$MOUNT/$DIR" 2>/dev/null
    sudo cp "$SRC/$ARCHIVO" "$MOUNT/$ARCHIVO"
    local SIZE=$(du -sh "$SRC/$ARCHIVO" | cut -f1)
    echo -e "${GREEN}✓ $ARCHIVO ($SIZE) → 111${NC}"
}

# --- Dry-run: mostrar qué se copiaría ---
deploy_dryrun() {
    echo -e "${YELLOW}--- DRY-RUN: archivos que se copiarían ---${NC}"
    local INCLUDES=$(build_include_flags)

    echo -e "${CYAN}  _scripts_oneshot/${NC}"
    eval rsync -avn $INCLUDES --include='*/' --exclude='*' \
        "\"$SRC/_scripts_oneshot/\"" "\"$MOUNT/_scripts_oneshot/\"" 2>/dev/null | grep -v '/$'

    echo -e "${CYAN}  raíz${NC}"
    eval rsync -avn $INCLUDES \
        --exclude='_*' --exclude='.*' \
        --exclude='clz_wpu/' \
        --exclude='compras/' \
        --exclude='valijas/' \
        --exclude='tests/' \
        --include='*/' --exclude='*' \
        "\"$SRC/\"" "\"$MOUNT/\"" 2>/dev/null | grep -v '/$'

    echo ""
    echo -e "${YELLOW}Nada fue copiado (dry-run). Usá './deploy.sh scripts' para ejecutar.${NC}"
}

# --- Main ---
case "${1:-todo}" in
    scripts|sql)
        montar
        deploy_scripts
        ;;
    web2py)
        montar
        deploy_web2py
        ;;
    todo)
        montar
        deploy_scripts
        deploy_web2py
        ;;
    archivo)
        montar
        deploy_archivo "$2"
        ;;
    dryrun|dry-run|--dry-run)
        montar
        deploy_dryrun
        ;;
    *)
        echo "Uso: $0 [scripts|web2py|todo|archivo <ruta>|dryrun]"
        echo ""
        echo "  scripts   Solo .py/.sql/.json/.md/.txt/.sh al 111 (default rápido)"
        echo "  web2py    Deploy calzalindo_informes a web2py"
        echo "  todo      scripts + web2py"
        echo "  archivo   Copiar UN archivo puntual (ej: ./deploy.sh archivo _excel_pedidos/Pedido.xlsx)"
        echo "  dryrun    Ver qué se copiaría sin copiar nada"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deploy completado.${NC}"
echo -e "${GREEN}========================================${NC}"
