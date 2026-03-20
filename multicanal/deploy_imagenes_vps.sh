#!/bin/bash
# Deploy del servidor de imágenes en el VPS (200.58.109.125)
#
# Ejecutar desde la Mac:
#   bash multicanal/deploy_imagenes_vps.sh
#
# Lo que hace:
#   1. Copia nginx_imagenes.conf al VPS
#   2. Habilita el site
#   3. Crea el directorio de imágenes si no existe
#   4. Recarga nginx
#
# PREREQUISITOS:
#   - Acceso SSH al VPS (200.58.109.125)
#   - Las imágenes deben estar en /var/www/imagenes/ en el VPS
#     organizadas como: /var/www/imagenes/{path_relativo}/{archivo_final}
#     Ejemplo: /var/www/imagenes/2/2722200048/2722200048-01.jpeg

VPS="200.58.109.125"
VPS_USER="root"  # ajustar si es otro
CONF_LOCAL="$(dirname "$0")/nginx_imagenes.conf"

echo "=== Deploy servidor de imágenes al VPS $VPS ==="

# 1. Verificar que el archivo de config existe
if [ ! -f "$CONF_LOCAL" ]; then
    echo "ERROR: No se encuentra $CONF_LOCAL"
    exit 1
fi

# 2. Copiar config
echo "[1/4] Copiando nginx config..."
scp "$CONF_LOCAL" "$VPS_USER@$VPS:/etc/nginx/sites-available/imagenes"

# 3. Habilitar site
echo "[2/4] Habilitando site..."
ssh "$VPS_USER@$VPS" "ln -sf /etc/nginx/sites-available/imagenes /etc/nginx/sites-enabled/"

# 4. Crear directorio si no existe
echo "[3/4] Verificando directorio de imágenes..."
ssh "$VPS_USER@$VPS" "mkdir -p /var/www/imagenes && chown -R www-data:www-data /var/www/imagenes"

# 5. Test y reload
echo "[4/4] Recargando nginx..."
ssh "$VPS_USER@$VPS" "nginx -t && systemctl reload nginx"

echo ""
echo "=== Listo. Probar con: ==="
echo "  curl -I http://$VPS:8088/health"
echo "  curl -I http://$VPS:8088/img/2/2722200048/2722200048-01.jpeg"
echo ""
echo "Si las imágenes no están en /var/www/imagenes/, sincronizarlas desde el ERP:"
echo "  # En el VPS, montar el share SMB del servidor 111:"
echo "  mount -t cifs //192.168.2.111/Macroges/Imagenes /var/www/imagenes -o user=administrador,pass=cagr\$2011"
echo "  # O rsync periódico desde el 111"
