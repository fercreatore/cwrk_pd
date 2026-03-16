#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# DEPLOY: Módulo Productividad e Incentivos → server 192.168.2.111
# Ejecutar desde Mac: bash deploy_productividad.sh
# ═══════════════════════════════════════════════════════════════════

set -e

# ─── CONFIGURACIÓN ───────────────────────────────────────────────
SERVER="192.168.2.111"
USER_SMB="am"         # usuario de red (ajustar si es otro)
PASS_SMB="dl"         # password de red (ajustar si es otro)

# Ruta de web2py en el server (probar las comunes)
# Ajustar si la ruta es diferente
WEB2PY_PATHS=(
    "web2py/applications/calzalindo_objetivos_v2"
    "Web2py/applications/calzalindo_objetivos_v2"
    "WEB2PY/applications/calzalindo_objetivos_v2"
)

# Carpeta local donde están los archivos (donde está este script)
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

# ─── COLORES ─────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  DEPLOY: Módulo Productividad e Incentivos"
echo "  Servidor: $SERVER"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ─── VERIFICAR ARCHIVOS LOCALES ──────────────────────────────────
echo "Verificando archivos locales..."
[ -f "$LOCAL_DIR/controllers/informes_productividad.py" ] || fail "No encuentro controllers/informes_productividad.py"
[ -f "$LOCAL_DIR/views/informes_productividad/dashboard.html" ] || fail "No encuentro views/informes_productividad/dashboard.html"
[ -f "$LOCAL_DIR/views/informes_productividad/vendedor.html" ] || fail "No encuentro views/informes_productividad/vendedor.html"
[ -f "$LOCAL_DIR/views/informes_productividad/estacionalidad.html" ] || fail "No encuentro views/informes_productividad/estacionalidad.html"
[ -f "$LOCAL_DIR/views/informes_productividad/incentivos.html" ] || fail "No encuentro views/informes_productividad/incentivos.html"
ok "Todos los archivos locales encontrados"

# ─── MÉTODO 1: SMB (mount_smbfs en Mac) ─────────────────────────
echo ""
echo "Intentando conectar via SMB..."

MOUNT_POINT="/tmp/deploy_productividad_$$"
mkdir -p "$MOUNT_POINT"
MOUNTED=0
APP_PATH=""

# Probar compartir C$ (admin share)
for SHARE in "C\$" "F\$" "D\$"; do
    SHARE_CLEAN=$(echo "$SHARE" | tr -d '\\')
    echo "  Probando //$SERVER/$SHARE_CLEAN ..."

    if mount_smbfs "//${USER_SMB}:${PASS_SMB}@${SERVER}/${SHARE}" "$MOUNT_POINT" 2>/dev/null; then
        ok "Montado $SHARE"
        MOUNTED=1

        # Buscar web2py
        for WP in "${WEB2PY_PATHS[@]}"; do
            if [ -d "$MOUNT_POINT/$WP" ]; then
                APP_PATH="$MOUNT_POINT/$WP"
                ok "Web2py encontrado en $SHARE/$WP"
                break 2
            fi
        done

        # Si no encontré con las rutas predefinidas, buscar
        FOUND=$(find "$MOUNT_POINT" -maxdepth 4 -name "calzalindo_objetivos_v2" -type d 2>/dev/null | head -1)
        if [ -n "$FOUND" ]; then
            APP_PATH="$FOUND"
            ok "Web2py encontrado en $FOUND"
            break
        fi

        # No encontré, desmontar y probar siguiente
        umount "$MOUNT_POINT" 2>/dev/null
        MOUNTED=0
    fi
done

# ─── MÉTODO 2: smbclient (fallback) ─────────────────────────────
if [ $MOUNTED -eq 0 ]; then
    warn "No pude montar via SMB. Intentando smbclient..."

    if command -v smbclient &>/dev/null; then
        # Listar shares para encontrar la correcta
        echo "  Listando shares en $SERVER..."
        smbclient -L "//$SERVER" -U "${USER_SMB}%${PASS_SMB}" 2>/dev/null || true

        warn "Necesito saber el share y la ruta. Probá manualmente:"
        echo ""
        echo "  smbclient //$SERVER/C\$ -U ${USER_SMB}%${PASS_SMB}"
        echo "  smb> ls web2py\\"
        echo ""
    fi
fi

# ─── COPIAR ARCHIVOS ────────────────────────────────────────────
if [ -n "$APP_PATH" ]; then
    echo ""
    echo "Copiando archivos..."

    # 1. Controller
    cp "$LOCAL_DIR/controllers/informes_productividad.py" "$APP_PATH/controllers/"
    ok "Controller copiado"

    # 2. Views (crear carpeta si no existe)
    mkdir -p "$APP_PATH/views/informes_productividad"
    cp "$LOCAL_DIR/views/informes_productividad/dashboard.html" "$APP_PATH/views/informes_productividad/"
    cp "$LOCAL_DIR/views/informes_productividad/vendedor.html" "$APP_PATH/views/informes_productividad/"
    cp "$LOCAL_DIR/views/informes_productividad/estacionalidad.html" "$APP_PATH/views/informes_productividad/"
    cp "$LOCAL_DIR/views/informes_productividad/incentivos.html" "$APP_PATH/views/informes_productividad/"
    ok "Vistas copiadas (4 archivos)"

    # 3. Parchear menu.py (agregar entrada Productividad)
    MENU_FILE="$APP_PATH/models/menu.py"
    if [ -f "$MENU_FILE" ]; then
        # Verificar si ya existe la entrada
        if grep -q "informes_productividad" "$MENU_FILE"; then
            warn "Entrada de menú ya existe, no se modifica"
        else
            # Hacer backup
            cp "$MENU_FILE" "${MENU_FILE}.bak_$(date +%Y%m%d_%H%M%S)"
            ok "Backup de menu.py creado"

            # Insertar antes de 'CLZ VENTAS'
            MENU_ENTRY="response.menu+=[\n    ('Productividad', False, URL(),[\n        ('Dashboard RRHH', False, URL('informes_productividad','dashboard')),\n        ('Estacionalidad', False, URL('informes_productividad','estacionalidad')),\n        ('Simulador Incentivos', False, URL('informes_productividad','incentivos')),\n    ])\n]"

            if grep -q "CLZ VENTAS" "$MENU_FILE"; then
                # Insertar antes de CLZ VENTAS
                sed -i.tmp "/CLZ VENTAS/i\\
$MENU_ENTRY" "$MENU_FILE" 2>/dev/null || \
                # Mac sed syntax
                sed -i '' "/CLZ VENTAS/i\\
$MENU_ENTRY" "$MENU_FILE" 2>/dev/null
                rm -f "${MENU_FILE}.tmp"
                ok "Entrada de menú agregada antes de 'CLZ VENTAS'"
            else
                # Agregar al final del archivo
                echo "" >> "$MENU_FILE"
                echo "$MENU_ENTRY" >> "$MENU_FILE"
                ok "Entrada de menú agregada al final"
            fi
        fi
    else
        warn "No encontré menu.py en $MENU_FILE"
    fi

    # Desmontar
    echo ""
    umount "$MOUNT_POINT" 2>/dev/null && ok "Share desmontado" || true
    rmdir "$MOUNT_POINT" 2>/dev/null || true

    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo -e "  ${GREEN}DEPLOY COMPLETO${NC}"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "  URLs disponibles:"
    echo "  → http://$SERVER:8000/calzalindo_objetivos_v2/informes_productividad/dashboard"
    echo "  → http://$SERVER:8000/calzalindo_objetivos_v2/informes_productividad/estacionalidad"
    echo "  → http://$SERVER:8000/calzalindo_objetivos_v2/informes_productividad/incentivos"
    echo ""
    echo "  web2py levanta los cambios automáticamente (no hace falta reiniciar)"
    echo ""

else
    # ─── FALLBACK: Instrucciones manuales con rutas ──────────────
    echo ""
    warn "No pude acceder automáticamente al server."
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  OPCIÓN A: Montar manualmente y volver a correr"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "  # Desde Finder: Cmd+K → smb://${USER_SMB}:${PASS_SMB}@${SERVER}/C\$"
    echo "  # Luego volvé a correr este script"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  OPCIÓN B: Copiar con smbclient"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "  smbclient //$SERVER/C\$ -U ${USER_SMB}%${PASS_SMB} << 'EOF'"
    echo "  cd web2py\\applications\\calzalindo_objetivos_v2\\controllers"
    echo "  put ${LOCAL_DIR}/controllers/informes_productividad.py"
    echo "  cd ..\\views"
    echo "  mkdir informes_productividad"
    echo "  cd informes_productividad"
    echo "  put ${LOCAL_DIR}/views/informes_productividad/dashboard.html"
    echo "  put ${LOCAL_DIR}/views/informes_productividad/vendedor.html"
    echo "  put ${LOCAL_DIR}/views/informes_productividad/estacionalidad.html"
    echo "  put ${LOCAL_DIR}/views/informes_productividad/incentivos.html"
    echo "  quit"
    echo "  EOF"
    echo ""
    echo "  Después editá menu.py manualmente (ver DEPLOY_PRODUCTIVIDAD.md)"
    echo ""

    rmdir "$MOUNT_POINT" 2>/dev/null || true
fi
