#!/bin/bash
# =============================================================
# DEPLOY: Mac → Servidor 112 (Streamlit app carga pedidos)
# Uso: ./deploy_112.sh
#
# Copia solo los archivos necesarios para correr la app Streamlit
# de carga de pedidos en el servidor réplica .112
# =============================================================

MOUNT_112="$HOME/mnt/compartido_112"
SMB_URL_112='//administrador:cagr$2011@192.168.2.112/compartido'
SRC="$HOME/Desktop/cowork_pedidos"
DEST="$MOUNT_112/cowork_pedidos_app"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Archivos que necesita la app Streamlit
APP_FILES=(
    app_h4.py
    app_carga.py
    app_reposicion.py
    config.py
    proveedores_db.py
    ocr_factura.py
    paso3_calcular_periodo.py
    paso4_insertar_pedido.py
    paso5_parsear_excel.py
    paso8_carga_factura.py
    resolver_talle.py
    requirements.txt
)

# --- Verificar/montar SMB ---
montar_112() {
    if mount | grep -qF "$MOUNT_112"; then
        echo -e "${GREEN}✓ SMB .112 ya montado${NC}"
    else
        echo -e "${YELLOW}Montando SMB al .112 (compartido)...${NC}"
        mkdir -p "$MOUNT_112" 2>/dev/null
        mount_smbfs "$SMB_URL_112" "$MOUNT_112"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Montado OK en $MOUNT_112${NC}"
        else
            echo -e "${RED}✗ Error montando .112${NC}"
            exit 1
        fi
    fi
    # Crear carpeta destino si no existe
    if [ ! -d "$DEST" ]; then
        echo -e "${YELLOW}Creando carpeta cowork_pedidos_app en compartido...${NC}"
        mkdir -p "$DEST"
        echo -e "${GREEN}✓ Carpeta creada${NC}"
    fi
}

deploy_app() {
    echo -e "${YELLOW}--- Deploy Streamlit app a .112 ---${NC}"

    # Copiar archivos principales
    for f in "${APP_FILES[@]}"; do
        if [ -f "$SRC/$f" ]; then
            cp "$SRC/$f" "$DEST/$f"
            echo -e "${GREEN}  ✓ $f${NC}"
        else
            echo -e "${RED}  ✗ No existe: $f${NC}"
        fi
    done

    # Copiar carpeta .streamlit si existe
    if [ -d "$SRC/.streamlit" ]; then
        mkdir -p "$DEST/.streamlit" 2>/dev/null
        cp "$SRC/.streamlit/"* "$DEST/.streamlit/" 2>/dev/null
        echo -e "${GREEN}  ✓ .streamlit/${NC}"
    fi

    # Copiar carpeta logos si existe
    if [ -d "$SRC/logos" ]; then
        mkdir -p "$DEST/logos" 2>/dev/null
        cp "$SRC/logos/"* "$DEST/logos/" 2>/dev/null
        echo -e "${GREEN}  ✓ logos/${NC}"
    fi

    # Copiar tests
    if [ -d "$SRC/tests" ]; then
        mkdir -p "$DEST/tests" 2>/dev/null
        cp "$SRC/tests/"*.py "$DEST/tests/" 2>/dev/null
        echo -e "${GREEN}  ✓ tests/${NC}"
    fi

    # Copiar scripts de arranque
    cp "$SRC/_sync_tools/iniciar_streamlit.bat" "$DEST/" 2>/dev/null
    cp "$SRC/_sync_tools/instalar_streamlit.bat" "$DEST/" 2>/dev/null
    echo -e "${GREEN}  ✓ .bat de arranque${NC}"

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deploy a .112 completado.${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${CYAN}En el .112, ejecutar:${NC}"
    echo -e "${CYAN}  1) cd C:\\cowork_pedidos_app${NC}"
    echo -e "${CYAN}  2) instalar_streamlit.bat  (solo la primera vez)${NC}"
    echo -e "${CYAN}  3) iniciar_streamlit.bat${NC}"
    echo -e "${CYAN}  4) Abrir http://192.168.2.112:8502 desde cualquier PC${NC}"
}

# --- Main ---
montar_112
deploy_app
