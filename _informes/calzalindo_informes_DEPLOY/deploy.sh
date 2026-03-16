#!/bin/bash
# =============================================================================
# DEPLOY calzalindo_informes -> Servidor via SMB
# Uso: bash deploy.sh
# =============================================================================

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Carpeta de origen (donde esta este script)
DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"

# Buscar el mount SMB automaticamente
# El share se monta en /Volumes/web2py_src* y la estructura es:
#   /Volumes/web2py_src-1/applications/calzalindo_informes/
# (sin subcarpeta "web2py" intermedia)
SMB_MOUNT=""
for vol in /Volumes/web2py_src*; do
    if [ -d "$vol/applications" ]; then
        SMB_MOUNT="$vol"
        break
    fi
done

if [ -z "$SMB_MOUNT" ]; then
    echo -e "${YELLOW}SMB no montado. Intentando montar...${NC}"
    open "smb://192.168.2.111/web2py_src"

    for i in $(seq 1 30); do
        sleep 1
        for vol in /Volumes/web2py_src*; do
            if [ -d "$vol/applications" ]; then
                SMB_MOUNT="$vol"
                break 2
            fi
        done
        printf "  Esperando mount... (%ds)\r" "$i"
    done
    echo ""

    if [ -z "$SMB_MOUNT" ]; then
        echo -e "${RED}ERROR: No se pudo montar el SMB despues de 30s${NC}"
        echo "Intenta montarlo manualmente desde Finder (Cmd+K) y despues correr de nuevo."
        exit 1
    fi
    echo -e "${GREEN}SMB montado en: $SMB_MOUNT${NC}"
fi

APP_DIR="$SMB_MOUNT/applications/calzalindo_informes"

if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}ERROR: No existe $APP_DIR${NC}"
    exit 1
fi

echo -e "${YELLOW}=== DEPLOY calzalindo_informes ===${NC}"
echo -e "Origen:  ${GREEN}$DEPLOY_DIR${NC}"
echo -e "Destino: ${GREEN}$APP_DIR${NC}"
echo ""

ERRORES=0
COPIADOS=0

# Funcion para copiar un archivo
copiar() {
    local src="$1"
    local dst="$2"
    local rel="$3"

    if [ ! -f "$src" ]; then
        return
    fi

    # Crear directorio destino si no existe
    mkdir -p "$(dirname "$dst")"

    if cp "$src" "$dst" 2>/dev/null; then
        echo -e "  ${GREEN}OK${NC}  $rel"
        COPIADOS=$((COPIADOS + 1))
    else
        echo -e "  ${RED}FAIL${NC}  $rel"
        ERRORES=$((ERRORES + 1))
    fi
}

# Copiar models
echo -e "${YELLOW}Models:${NC}"
for f in "$DEPLOY_DIR"/models/*.py; do
    [ -f "$f" ] || continue
    nombre=$(basename "$f")
    copiar "$f" "$APP_DIR/models/$nombre" "models/$nombre"
done

# Copiar controllers
echo -e "${YELLOW}Controllers:${NC}"
for f in "$DEPLOY_DIR"/controllers/*.py; do
    [ -f "$f" ] || continue
    nombre=$(basename "$f")
    copiar "$f" "$APP_DIR/controllers/$nombre" "controllers/$nombre"
done

# Copiar views (recursivo)
echo -e "${YELLOW}Views:${NC}"
if [ -d "$DEPLOY_DIR/views" ]; then
    find "$DEPLOY_DIR/views" -type f | while read f; do
        rel="${f#$DEPLOY_DIR/}"
        copiar "$f" "$APP_DIR/$rel" "$rel"
    done
fi

# Copiar static (si existe)
if [ -d "$DEPLOY_DIR/static" ]; then
    echo -e "${YELLOW}Static:${NC}"
    find "$DEPLOY_DIR/static" -type f | while read f; do
        rel="${f#$DEPLOY_DIR/}"
        copiar "$f" "$APP_DIR/$rel" "$rel"
    done
fi

echo ""
if [ "$ERRORES" -gt 0 ]; then
    echo -e "${RED}Deploy con errores: $COPIADOS copiados, $ERRORES fallidos${NC}"
    exit 1
else
    echo -e "${GREEN}Deploy OK: $COPIADOS archivos copiados${NC}"
fi
