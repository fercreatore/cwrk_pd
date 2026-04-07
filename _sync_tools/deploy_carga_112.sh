#!/bin/bash
# deploy_carga_112.sh — Sube app_carga.py + dependencias al .112
# Ejecutar desde Mac: bash _sync_tools/deploy_carga_112.sh
#
# Destino: //192.168.2.112/c$/cowork_pedidos/

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MOUNT_POINT="/Volumes/cowork_112"
SMB_SHARE="//administrador:cagr\$2011@192.168.2.112/c\$/cowork_pedidos"

# ── Archivos a copiar ──
ARCHIVOS=(
    # CORE
    "app_carga.py"
    "config.py"
    # EXCEL/PEDIDO
    "paso5_parsear_excel.py"
    "proveedores_db.py"
    # OCR FACTURAS
    "ocr_factura.py"
    # INSERT PEDIDO/REMITO
    "paso4_insertar_pedido.py"
    "paso8_carga_factura.py"
    "paso9_insertar_remito.py"
    "resolver_talle.py"
    # REQUIREMENTS
    "requirements.txt"
)

echo "╔══════════════════════════════════════════════════╗"
echo "║  DEPLOY app_carga → .112 (DATASVRW)             ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── Montar SMB si no está ──
if [ ! -d "$MOUNT_POINT" ]; then
    echo "📂 Montando SMB .112..."
    sudo mkdir -p "$MOUNT_POINT"
    sudo mount_smbfs "$SMB_SHARE" "$MOUNT_POINT"
    echo "   ✅ Montado en $MOUNT_POINT"
else
    echo "📂 SMB .112 ya montado en $MOUNT_POINT"
fi

# ── Crear carpeta destino si no existe ──
DEST="$MOUNT_POINT"
if [ ! -d "$DEST" ]; then
    mkdir -p "$DEST"
    echo "   📁 Creada carpeta $DEST"
fi

# ── Copiar archivos ──
echo ""
echo "📋 Copiando ${#ARCHIVOS[@]} archivos..."
for f in "${ARCHIVOS[@]}"; do
    if [ -f "$PROJECT_DIR/$f" ]; then
        cp "$PROJECT_DIR/$f" "$DEST/$f"
        echo "   ✅ $f"
    else
        echo "   ⚠️  $f NO ENCONTRADO (skip)"
    fi
done

echo ""
echo "═══════════════════════════════════════════════════"
echo "✅ Deploy completo. ${#ARCHIVOS[@]} archivos copiados al .112"
echo ""
echo "PRÓXIMOS PASOS en el .112:"
echo ""
echo "  1. Instalar dependencias (una sola vez):"
echo '     "C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe" -m pip install -r C:\cowork_pedidos\requirements.txt'
echo ""
echo "  2. Levantar la app:"
echo '     "C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe" -m streamlit run C:\cowork_pedidos\app_carga.py --server.port 8501 --server.address 0.0.0.0'
echo ""
echo "  3. Abrir desde cualquier PC de la red:"
echo "     http://192.168.2.112:8501"
echo "═══════════════════════════════════════════════════"
