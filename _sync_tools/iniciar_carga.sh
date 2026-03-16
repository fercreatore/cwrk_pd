#!/bin/bash
# Iniciar sistema de carga de facturas para operadores
#   chmod +x iniciar_carga.sh
#   ./iniciar_carga.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Fix SSL para Mac + SQL Server viejo ──────────────────
cat > /tmp/openssl_legacy.cnf << 'SSLEOF'
openssl_conf = openssl_init
[openssl_init]
ssl_conf = ssl_sect
[ssl_sect]
system_default = system_default_sect
[system_default_sect]
MinProtocol = TLSv1
CipherString = DEFAULT:@SECLEVEL=0
SSLEOF
export OPENSSL_CONF=/tmp/openssl_legacy.cnf

echo "=================================="
echo " Sistema de Carga H4/Calzalindo"
echo "=================================="

# Verificar dependencias
python3 -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Instalando dependencias..."
    pip3 install -r requirements.txt
fi

# Mostrar IP
echo "Acceso local:  http://localhost:8501"
IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
[ -n "$IP" ] && echo "Acceso red:    http://$IP:8501"
echo ""

# Levantar Streamlit
streamlit run app_carga.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.maxUploadSize 50 \
    --browser.gatherUsageStats false
