#!/bin/bash
# =============================================================
# Instala y activa el daemon de reconexión automática VPN L2TP
# Uso: bash _sync_tools/instalar_vpn_daemon.sh
# =============================================================

PLIST_SRC="$HOME/Library/LaunchAgents/com.cowork.vpn-reconectar.plist"
LABEL="com.cowork.vpn-reconectar"

echo "=== Instalación daemon VPN reconexión ==="

# Verificar que el secreto IPSec está en Keychain
if ! security find-generic-password -a "VPN (L2TP)" -s "com.cowork.vpn.ipsec" -w &>/dev/null; then
    echo "⚠ Falta el secreto IPSec en Keychain."
    echo "  Guardalo primero:"
    echo "  security add-generic-password -a 'VPN (L2TP)' -s 'com.cowork.vpn.ipsec' -w 'TU_SECRETO_IPSEC'"
    echo ""
    read -p "¿Querés ingresarlo ahora? (s/n) " resp
    if [ "$resp" = "s" ] || [ "$resp" = "S" ]; then
        read -sp "Secreto IPSec: " secret_val
        echo ""
        security add-generic-password -a "VPN (L2TP)" -s "com.cowork.vpn.ipsec" -w "$secret_val"
        if [ $? -eq 0 ]; then
            echo "✓ Secreto guardado en Keychain"
        else
            echo "✗ Error guardando secreto"
            exit 1
        fi
    else
        echo "AVISO: El daemon no podrá reconectar sin el secreto."
    fi
fi

# Verificar que el plist existe
if [ ! -f "$PLIST_SRC" ]; then
    echo "ERROR: No existe $PLIST_SRC"
    echo "Copialo primero a ~/Library/LaunchAgents/"
    exit 1
fi

# Descargar si ya estaba cargado (ignorar error si no existía)
launchctl unload "$PLIST_SRC" 2>/dev/null
echo "✓ Descargado anterior (si existía)"

# Cargar el nuevo
launchctl load "$PLIST_SRC"
if [ $? -eq 0 ]; then
    echo "✓ Daemon cargado OK"
else
    echo "✗ Error al cargar daemon"
    exit 1
fi

# Verificar que está corriendo
if launchctl list | grep -q "$LABEL"; then
    echo "✓ Daemon activo: $LABEL"
else
    echo "⚠ Daemon cargado pero no aparece en launchctl list"
fi

echo ""
echo "El daemon verifica la VPN cada 30 segundos."
echo "Log: /tmp/vpn-reconectar.log"
echo ""
echo "Para desactivar:  launchctl unload $PLIST_SRC"
echo "Para ver estado:   scutil --nc status 'VPN (L2TP)'"
echo "Para ver log:      tail -f /tmp/vpn-reconectar.log"
