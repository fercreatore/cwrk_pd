#!/bin/bash
# =============================================================
# DEPLOY UNIFICADO: Mac → Servidores 111 y 112
#
# Uso: ./deploy.sh [componente]
#
# Componentes:
#   scripts    Scripts pipeline + oneshot al 111
#   web2py     calzalindo_informes al 111 (directo, sin paso manual)
#   112        Streamlit apps al 112 (compartido)
#   carga      app_carga al 112 (C:\cowork_pedidos)
#   todo       scripts + web2py + 112
#   archivo    Copiar UN archivo puntual al 111
#   dryrun     Ver que se copiaria sin copiar nada
#
# REGLA: Solo codigo (.py, .sql, .json, .md, .txt, .sh, .bat).
# Para archivos pesados: ./deploy.sh archivo ruta/al/archivo
# =============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib_deploy.sh"

# --- Manifest de archivos para 112 ---
MANIFEST_112="$SCRIPT_DIR/manifest_112.txt"

# --- Deploy scripts (pipeline + oneshot) al 111 ---
deploy_scripts() {
    _montar_share "$MOUNT_111" "$SMB_URL_111" "cowork_pedidos (111)" || return 1
    echo -e "${YELLOW}--- Deploy scripts a C:\\cowork_pedidos ---${NC}"
    local INCLUDES=$(build_include_flags)

    # 1) _scripts_oneshot/
    echo -e "${CYAN}  _scripts_oneshot/${NC}"
    eval rsync -av $INCLUDES --include='*/' --exclude='*' \
        "\"$SRC/_scripts_oneshot/\"" "\"$MOUNT_111/_scripts_oneshot/\""

    # 1b) autorepo/ (motor autocompensación inter-depósito)
    if [ -d "$SRC/autorepo" ]; then
        echo -e "${CYAN}  autorepo/${NC}"
        eval rsync -av $INCLUDES --include='*/' --exclude='*' \
            "\"$SRC/autorepo/\"" "\"$MOUNT_111/autorepo/\""
    fi

    # 2) Raiz (pipeline core) — solo archivos de raiz, sin subcarpetas grandes
    echo -e "${CYAN}  raiz (pipeline core)${NC}"
    eval rsync -av $INCLUDES \
        --exclude='_*' --exclude='.*' \
        --exclude='clz_wpu/' \
        --exclude='compras/' \
        --exclude='valijas/' \
        --exclude='tests/' \
        --include='*/' --exclude='*' \
        "\"$SRC/\"" "\"$MOUNT_111/\""

    echo -e "${GREEN}+ Scripts desplegados en C:\\cowork_pedidos${NC}"
    _verificar_deploy "$SRC" "$MOUNT_111" "scripts-111"
}

# --- Deploy web2py (calzalindo_informes) al 111 ---
deploy_web2py() {
    _montar_share "$MOUNT_111_WEB2PY" "$SMB_URL_111_WEB2PY" "web2py (111)" || return 1
    echo -e "${YELLOW}--- Deploy calzalindo_informes ---${NC}"

    rsync -av \
        "$SRC/_informes/calzalindo_informes_DEPLOY/" \
        "$MOUNT_111_WEB2PY/"

    # Limpieza de __pycache__ (antes requeria paso manual con .bat)
    rm -rf "$MOUNT_111_WEB2PY/controllers/__pycache__" 2>/dev/null
    rm -rf "$MOUNT_111_WEB2PY/models/__pycache__" 2>/dev/null
    echo -e "${CYAN}  Cache limpiado (controllers + models)${NC}"

    # Copiar el .bat como fallback para restart manual
    if [ -f "$SCRIPT_DIR/deploy_web2py_111.bat" ]; then
        _montar_share "$MOUNT_111" "$SMB_URL_111" "cowork_pedidos (111)" 2>/dev/null
        cp "$SCRIPT_DIR/deploy_web2py_111.bat" "$MOUNT_111/_sync_tools/" 2>/dev/null
    fi

    echo -e "${GREEN}+ Web2py desplegado en C:\\web2py_src\\applications\\calzalindo_informes${NC}"
    echo -e "${CYAN}  web2py en dev mode auto-recarga. Si no, reiniciar:${NC}"
    echo -e "${CYAN}    taskkill /f /im python.exe && cd C:\\web2py_src && start python web2py.py -a admin -i 0.0.0.0 -p 8080${NC}"
    _verificar_deploy "$SRC/_informes/calzalindo_informes_DEPLOY" "$MOUNT_111_WEB2PY" "web2py-111"
}

# --- Deploy Streamlit app al 112 (compartido) ---
deploy_112() {
    _montar_share "$MOUNT_112" "$SMB_URL_112" "compartido (112)" || return 1
    local DEST="$MOUNT_112/cowork_pedidos_app"
    mkdir -p "$DEST" 2>/dev/null

    echo -e "${YELLOW}--- Deploy Streamlit app a .112 ---${NC}"

    # Leer manifest si existe, sino usar lista default
    local FILES=()
    if [ -f "$MANIFEST_112" ]; then
        while IFS= read -r line; do
            # Ignorar comentarios y lineas vacias
            [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
            FILES+=("$line")
        done < "$MANIFEST_112"
        echo -e "${CYAN}  Leyendo de manifest_112.txt (${#FILES[@]} archivos)${NC}"
    else
        FILES=(
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
        echo -e "${CYAN}  Usando lista default (${#FILES[@]} archivos)${NC}"
    fi

    for f in "${FILES[@]}"; do
        if [ -f "$SRC/$f" ]; then
            cp "$SRC/$f" "$DEST/$f"
            echo -e "${GREEN}  + $f${NC}"
        else
            echo -e "${RED}  x No existe: $f${NC}"
        fi
    done

    # .streamlit config
    if [ -d "$SRC/.streamlit" ]; then
        mkdir -p "$DEST/.streamlit" 2>/dev/null
        cp "$SRC/.streamlit/"* "$DEST/.streamlit/" 2>/dev/null
        echo -e "${GREEN}  + .streamlit/${NC}"
    fi

    # logos
    if [ -d "$SRC/logos" ]; then
        mkdir -p "$DEST/logos" 2>/dev/null
        cp "$SRC/logos/"* "$DEST/logos/" 2>/dev/null
        echo -e "${GREEN}  + logos/${NC}"
    fi

    # tests
    if [ -d "$SRC/tests" ]; then
        mkdir -p "$DEST/tests" 2>/dev/null
        cp "$SRC/tests/"*.py "$DEST/tests/" 2>/dev/null
        echo -e "${GREEN}  + tests/${NC}"
    fi

    # .bat de arranque
    cp "$SCRIPT_DIR/iniciar_streamlit.bat" "$DEST/" 2>/dev/null
    cp "$SCRIPT_DIR/instalar_streamlit.bat" "$DEST/" 2>/dev/null

    echo -e "${GREEN}+ Deploy a .112 completado${NC}"
    echo -e "${CYAN}  En el 112: cd C:\\compartido\\cowork_pedidos_app && iniciar_streamlit.bat${NC}"
}

# --- Deploy app_carga al 112 (C:\cowork_pedidos via c$ share) ---
deploy_carga() {
    local MOUNT_112_CARGA="$HOME/mnt/cowork_112_carga"
    local SMB_URL_112_CARGA="//${SMB_USER}:${SMB_PASS}@192.168.2.112/c\$/cowork_pedidos"

    _montar_share "$MOUNT_112_CARGA" "$SMB_URL_112_CARGA" "cowork_pedidos (112 c$)" || return 1

    echo -e "${YELLOW}--- Deploy app_carga a .112 (C:\\cowork_pedidos) ---${NC}"

    local ARCHIVOS=(
        app_carga.py config.py
        paso5_parsear_excel.py proveedores_db.py
        ocr_factura.py
        paso4_insertar_pedido.py paso8_carga_factura.py paso9_insertar_remito.py
        resolver_talle.py
        requirements.txt
    )

    for f in "${ARCHIVOS[@]}"; do
        if [ -f "$SRC/$f" ]; then
            cp "$SRC/$f" "$MOUNT_112_CARGA/$f"
            echo -e "${GREEN}  + $f${NC}"
        else
            echo -e "${RED}  x $f NO ENCONTRADO${NC}"
        fi
    done

    echo -e "${GREEN}+ Deploy carga a .112 completado${NC}"
}

# --- Deploy archivo individual al 111 ---
deploy_archivo() {
    local ARCHIVO="$1"
    if [ -z "$ARCHIVO" ]; then
        echo -e "${RED}x Falta nombre de archivo. Uso: ./deploy.sh archivo ruta/al/archivo${NC}"
        return 1
    fi
    if [ ! -f "$SRC/$ARCHIVO" ]; then
        echo -e "${RED}x No existe: $SRC/$ARCHIVO${NC}"
        return 1
    fi
    _montar_share "$MOUNT_111" "$SMB_URL_111" "cowork_pedidos (111)" || return 1
    local DIR=$(dirname "$ARCHIVO")
    mkdir -p "$MOUNT_111/$DIR" 2>/dev/null
    cp "$SRC/$ARCHIVO" "$MOUNT_111/$ARCHIVO"
    local SIZE=$(du -sh "$SRC/$ARCHIVO" | cut -f1)
    echo -e "${GREEN}+ $ARCHIVO ($SIZE) → 111${NC}"
}

# --- Dry-run: mostrar que se copiaria ---
deploy_dryrun() {
    echo -e "${YELLOW}--- DRY-RUN: archivos que se copiarian ---${NC}"

    # 111 scripts
    if _montar_share "$MOUNT_111" "$SMB_URL_111" "cowork_pedidos (111)" 2>/dev/null; then
        local INCLUDES=$(build_include_flags)
        echo -e "${CYAN}  _scripts_oneshot/ → 111${NC}"
        eval rsync -avn $INCLUDES --include='*/' --exclude='*' \
            "\"$SRC/_scripts_oneshot/\"" "\"$MOUNT_111/_scripts_oneshot/\"" 2>/dev/null \
            | grep -v '/$' | grep -v '^sending' | grep -v '^sent ' | grep -v '^total ' | grep -v '^Transfer' | grep -v '^$' \
            | sed 's/^/    /'

        echo -e "${CYAN}  raiz → 111${NC}"
        eval rsync -avn $INCLUDES \
            --exclude='_*' --exclude='.*' \
            --exclude='clz_wpu/' --exclude='compras/' --exclude='valijas/' --exclude='tests/' \
            --include='*/' --exclude='*' \
            "\"$SRC/\"" "\"$MOUNT_111/\"" 2>/dev/null \
            | grep -v '/$' | grep -v '^sending' | grep -v '^sent ' | grep -v '^total ' | grep -v '^Transfer' | grep -v '^$' \
            | sed 's/^/    /'
    fi

    # 111 web2py
    if _montar_share "$MOUNT_111_WEB2PY" "$SMB_URL_111_WEB2PY" "web2py (111)" 2>/dev/null; then
        echo -e "${CYAN}  web2py → 111${NC}"
        rsync -avn "$SRC/_informes/calzalindo_informes_DEPLOY/" "$MOUNT_111_WEB2PY/" 2>/dev/null \
            | grep -v '/$' | grep -v '^sending' | grep -v '^sent ' | grep -v '^total ' | grep -v '^Transfer' | grep -v '^$' \
            | sed 's/^/    /'
    fi

    # 112
    echo -e "${CYAN}  112 streamlit:${NC}"
    if [ -f "$MANIFEST_112" ]; then
        while IFS= read -r line; do
            [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
            if [ -f "$SRC/$line" ]; then
                echo "    $line"
            fi
        done < "$MANIFEST_112"
    else
        echo "    (manifest_112.txt no existe, usaria lista default)"
    fi

    echo ""
    echo -e "${YELLOW}Nada fue copiado (dry-run).${NC}"
}

# --- Main ---
echo -e "${BOLD}=== DEPLOY COWORK PEDIDOS ===${NC}"
echo ""

case "${1:-todo}" in
    scripts|sql)
        deploy_scripts
        ;;
    web2py)
        deploy_web2py
        ;;
    112)
        deploy_112
        ;;
    carga)
        deploy_carga
        ;;
    todo)
        deploy_scripts
        echo ""
        deploy_web2py
        echo ""
        deploy_112
        ;;
    archivo)
        deploy_archivo "$2"
        ;;
    dryrun|dry-run|--dry-run)
        deploy_dryrun
        ;;
    *)
        echo "Uso: $0 [scripts|web2py|112|carga|todo|archivo <ruta>|dryrun]"
        echo ""
        echo "  scripts   .py/.sql/.json al 111 (pipeline + oneshot)"
        echo "  web2py    calzalindo_informes al 111 (directo, sin paso manual)"
        echo "  112       Streamlit apps al 112 (compartido)"
        echo "  carga     app_carga al 112 (C:\\cowork_pedidos)"
        echo "  todo      scripts + web2py + 112"
        echo "  archivo   Copiar UN archivo: ./deploy.sh archivo _excel_pedidos/Pedido.xlsx"
        echo "  dryrun    Ver que se copiaria sin copiar nada"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deploy completado.${NC}"
echo -e "${GREEN}========================================${NC}"
