#!/bin/bash
# =============================================================
# setup_mcp.sh — Genera .mcp.json desde .mcp.json.template
#
# Lee credenciales de ~/.cowork_creds y reemplaza los placeholders.
# Correr una sola vez, o cada vez que cambien credenciales.
#
# Uso: ./_sync_tools/setup_mcp.sh
# =============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$PROJECT_DIR/.mcp.json.template"
OUTPUT="$PROJECT_DIR/.mcp.json"
CREDS="$HOME/.cowork_creds"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# --- Verificar template ---
if [ ! -f "$TEMPLATE" ]; then
    echo -e "${RED}x No existe $TEMPLATE${NC}"
    exit 1
fi

# --- Verificar credenciales ---
if [ ! -f "$CREDS" ]; then
    echo -e "${YELLOW}No existe ~/.cowork_creds. Creandolo...${NC}"
    cat > "$CREDS" << 'CREDS_EOF'
# Credenciales para MCP y deploy (NO commitear este archivo)
# Generado por setup_mcp.sh

# SMB (deploy a servidores)
SMB_USER="administrador"
SMB_PASS='cagr$2011'

# SQL Server (ERP)
SQL_USER="am"
SQL_PASS="dl"

# CLZ Ventas SQL
CLZ_VENTAS_USER="meta106"
CLZ_VENTAS_PASS="Meta106%23"

# MySQL
MYSQL_USER="root"
MYSQL_PASS="cagr%242011"

# PostgreSQL (VPS Guille)
PG_USER="guille"
PG_PASS="Martes13%23"

# n8n JWT
N8N_JWT_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmNTQwMWRmYy05YjI1LTRhZmUtOGIzNC1kOTMxYTM2ZTg5ODYiLCJpc3MiOiJuOG4iLCJhdWQiOiJtY3Atc2VydmVyLWFwaSIsImp0aSI6IjQ0MDk4ODk4LTg2MDMtNDc4NC1hMDgyLWRlZDVlZTE5YzE3ZiIsImlhdCI6MTc3MzcxNDgyN30.9ERddhdk3SbUz6_ps8lCSyLunXjxi-goKJYBlsJZVVE"
CREDS_EOF
    chmod 600 "$CREDS"
    echo -e "${GREEN}+ ~/.cowork_creds creado. Edita las credenciales si cambiaron.${NC}"
fi

# --- Leer credenciales ---
source "$CREDS"

# --- Generar .mcp.json ---
cp "$TEMPLATE" "$OUTPUT"

# Reemplazar placeholders
sed -i '' "s|{{SQL_USER}}|${SQL_USER}|g" "$OUTPUT"
sed -i '' "s|{{SQL_PASS}}|${SQL_PASS}|g" "$OUTPUT"
sed -i '' "s|{{CLZ_VENTAS_USER}}|${CLZ_VENTAS_USER}|g" "$OUTPUT"
sed -i '' "s|{{CLZ_VENTAS_PASS}}|${CLZ_VENTAS_PASS}|g" "$OUTPUT"
sed -i '' "s|{{MYSQL_USER}}|${MYSQL_USER}|g" "$OUTPUT"
sed -i '' "s|{{MYSQL_PASS}}|${MYSQL_PASS}|g" "$OUTPUT"
sed -i '' "s|{{PG_USER}}|${PG_USER}|g" "$OUTPUT"
sed -i '' "s|{{PG_PASS}}|${PG_PASS}|g" "$OUTPUT"
sed -i '' "s|{{N8N_JWT_TOKEN}}|${N8N_JWT_TOKEN}|g" "$OUTPUT"

echo -e "${GREEN}+ .mcp.json generado desde template${NC}"
echo -e "${YELLOW}  Credenciales leidas de ~/.cowork_creds${NC}"
