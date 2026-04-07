#!/bin/bash
# =============================================================
# DEPLOY WEB2PY: Mac -> SMB staging -> web2py en 111
# Uso: ./deploy_web2py.sh [dryrun|force]
#
# Resuelve el problema de 2 pasos:
#   1. Mac -> SMB (C:\cowork_pedidos\_informes\calzalindo_informes_DEPLOY)
#   2. SMB staging -> web2py (C:\web2py_src\applications\calzalindo_informes)
#
# El paso 2 lo hace el .bat en el servidor (deploy_web2py_111.bat)
# o se puede ejecutar manualmente con los comandos que imprime.
# =============================================================

MOUNT="$HOME/mnt/cowork_111"
SMB_URL='//administrador:cagr$2011@192.168.2.111/c$/cowork_pedidos'
SRC="$(cd "$(dirname "$0")/.." && pwd)/_informes/calzalindo_informes_DEPLOY"
DEST_STAGING="$MOUNT/_informes/calzalindo_informes_DEPLOY"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

MODE="${1:-deploy}"
CHANGED=0
SKIPPED=0
TOTAL=0

# --- Montar SMB ---
montar() {
    if mount | grep -qF "$MOUNT"; then
        echo -e "${GREEN}SMB ya montado${NC}"
    else
        echo -e "${YELLOW}Montando SMB...${NC}"
        mkdir -p "$MOUNT" 2>/dev/null
        mount_smbfs "$SMB_URL" "$MOUNT"
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error montando SMB. Esta encendido el servidor?${NC}"
            exit 1
        fi
        echo -e "${GREEN}SMB montado OK${NC}"
    fi
}

# --- Copiar archivo si cambio (compara tamano + fecha) ---
copy_if_changed() {
    local src_file="$1"
    local dest_file="$2"
    local label="$3"

    TOTAL=$((TOTAL + 1))

    if [ ! -f "$src_file" ]; then
        return
    fi

    # Crear directorio destino si no existe
    local dest_dir=$(dirname "$dest_file")
    mkdir -p "$dest_dir" 2>/dev/null

    if [ "$MODE" = "force" ]; then
        # Forzar copia
        if [ "$MODE" != "dryrun" ]; then
            cp "$src_file" "$dest_file"
        fi
        echo -e "  ${GREEN}[FORCE]${NC} $label"
        CHANGED=$((CHANGED + 1))
        return
    fi

    if [ -f "$dest_file" ]; then
        local src_size=$(stat -f%z "$src_file" 2>/dev/null)
        local dest_size=$(stat -f%z "$dest_file" 2>/dev/null)
        local src_mtime=$(stat -f%m "$src_file" 2>/dev/null)
        local dest_mtime=$(stat -f%m "$dest_file" 2>/dev/null)

        if [ "$src_size" = "$dest_size" ] && [ "$src_mtime" -le "$dest_mtime" ] 2>/dev/null; then
            SKIPPED=$((SKIPPED + 1))
            return
        fi
    fi

    if [ "$MODE" = "dryrun" ]; then
        echo -e "  ${YELLOW}[WOULD COPY]${NC} $label"
    else
        cp "$src_file" "$dest_file"
        echo -e "  ${GREEN}[COPIED]${NC} $label"
    fi
    CHANGED=$((CHANGED + 1))
}

# --- Main ---
echo -e "${BOLD}=== Deploy web2py: calzalindo_informes ===${NC}"
echo -e "Origen:  $SRC"
echo ""

# Validar que existe el source
if [ ! -d "$SRC" ]; then
    echo -e "${RED}No existe $SRC${NC}"
    exit 1
fi

montar

echo -e "Destino: $DEST_STAGING"
echo ""

# === STEP 1: Controllers ===
echo -e "${CYAN}--- Controllers ---${NC}"
for f in "$SRC/controllers/"*.py; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    copy_if_changed "$f" "$DEST_STAGING/controllers/$name" "controllers/$name"
done

# === STEP 2: Views (subdirectorios) ===
echo -e "${CYAN}--- Views ---${NC}"
# Layout en raiz de views
if [ -f "$SRC/views/layout.html" ]; then
    copy_if_changed "$SRC/views/layout.html" "$DEST_STAGING/views/layout.html" "views/layout.html"
fi
# Subdirectorios de views
for d in "$SRC/views/"*/; do
    [ -d "$d" ] || continue
    dirname=$(basename "$d")
    for f in "$d"*.html; do
        [ -f "$f" ] || continue
        name=$(basename "$f")
        copy_if_changed "$f" "$DEST_STAGING/views/$dirname/$name" "views/$dirname/$name"
    done
done

# === STEP 3: Models ===
echo -e "${CYAN}--- Models ---${NC}"
for f in "$SRC/models/"*.py; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    copy_if_changed "$f" "$DEST_STAGING/models/$name" "models/$name"
done

# === STEP 4: SQL (staging only, no va a web2py) ===
echo -e "${CYAN}--- SQL (staging only) ---${NC}"
for f in "$SRC/sql/"*.sql; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    copy_if_changed "$f" "$DEST_STAGING/sql/$name" "sql/$name"
done

# === STEP 5: Deploy the .bat to the server ===
BAT_FILE="$(cd "$(dirname "$0")" && pwd)/deploy_web2py_111.bat"
if [ -f "$BAT_FILE" ]; then
    copy_if_changed "$BAT_FILE" "$MOUNT/_sync_tools/deploy_web2py_111.bat" "_sync_tools/deploy_web2py_111.bat"
fi

# === Resumen ===
echo ""
echo -e "${BOLD}=== Resumen ===${NC}"
if [ "$MODE" = "dryrun" ]; then
    echo -e "${YELLOW}DRY-RUN: $CHANGED archivos se copiarian, $SKIPPED sin cambios${NC}"
else
    echo -e "${GREEN}$CHANGED archivos copiados al staging SMB, $SKIPPED sin cambios (de $TOTAL)${NC}"
fi

# === STEP 6: Instrucciones para el servidor ===
echo ""
echo -e "${BOLD}=== PASO 2: Copiar staging -> web2py en el 111 ===${NC}"
echo -e "${CYAN}Opcion A: Ejecutar el .bat en el servidor (como Administrador):${NC}"
echo -e "  ${YELLOW}C:\\cowork_pedidos\\_sync_tools\\deploy_web2py_111.bat${NC}"
echo ""
echo -e "${CYAN}Opcion B: Copy-paste en CMD del 111:${NC}"
echo -e "${YELLOW}---${NC}"

# Generar comandos copy para controllers
for f in "$SRC/controllers/"*.py; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    echo "copy /Y \"C:\\cowork_pedidos\\_informes\\calzalindo_informes_DEPLOY\\controllers\\$name\" \"C:\\web2py_src\\applications\\calzalindo_informes\\controllers\\\""
done

# Generar comandos para views
if [ -f "$SRC/views/layout.html" ]; then
    echo "copy /Y \"C:\\cowork_pedidos\\_informes\\calzalindo_informes_DEPLOY\\views\\layout.html\" \"C:\\web2py_src\\applications\\calzalindo_informes\\views\\\""
fi
for d in "$SRC/views/"*/; do
    [ -d "$d" ] || continue
    dirname=$(basename "$d")
    echo "xcopy /Y /I \"C:\\cowork_pedidos\\_informes\\calzalindo_informes_DEPLOY\\views\\$dirname\\*\" \"C:\\web2py_src\\applications\\calzalindo_informes\\views\\$dirname\\\""
done

# Generar comandos para models
for f in "$SRC/models/"*.py; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    echo "copy /Y \"C:\\cowork_pedidos\\_informes\\calzalindo_informes_DEPLOY\\models\\$name\" \"C:\\web2py_src\\applications\\calzalindo_informes\\models\\\""
done

# Cache cleanup
echo "rd /S /Q \"C:\\web2py_src\\applications\\calzalindo_informes\\controllers\\__pycache__\" 2>nul"
echo "rd /S /Q \"C:\\web2py_src\\applications\\calzalindo_informes\\models\\__pycache__\" 2>nul"

echo -e "${YELLOW}---${NC}"
echo ""
echo -e "${CYAN}Opcion C: Reiniciar web2py (CMD como Administrador):${NC}"
echo -e "  taskkill /f /im python.exe"
echo -e "  cd C:\\web2py_src"
echo -e "  start python web2py.py -a admin -i 0.0.0.0 -p 8080"
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Staging completado. Ejecutar paso 2 en el 111.${NC}"
echo -e "${GREEN}========================================${NC}"
