#!/bin/bash
# Lanzador de app_reposicion.py con fix SSL para SQL Server 2012
# Usar SIEMPRE este script en lugar de "streamlit run" directo

cd "$(dirname "$0")"

# Crear config OpenSSL legacy si no existe
SSL_CONF="/tmp/openssl_legacy.cnf"
if [ ! -f "$SSL_CONF" ]; then
    cat > "$SSL_CONF" << 'EOF'
openssl_conf = openssl_init
[openssl_init]
ssl_conf = ssl_sect
[ssl_sect]
system_default = system_default_sect
[system_default_sect]
MinProtocol = TLSv1
CipherString = DEFAULT@SECLEVEL=0
EOF
fi

export OPENSSL_CONF="$SSL_CONF"

# Matar instancia anterior en 8503 si existe
lsof -ti:8503 | xargs kill -9 2>/dev/null

exec streamlit run app_reposicion.py --server.port 8503
