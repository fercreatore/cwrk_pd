#!/bin/bash
# =============================================================
# RECONECTAR AUTO: Detecta red, conecta VPN si es necesario,
# y monta todos los shares SMB.
#
# Se dispara automáticamente al cambiar de red (LaunchAgent)
# o se puede correr manualmente: ./reconectar_auto.sh (sin sudo)
# =============================================================

LOG="/tmp/reconectar_auto.log"
LOCKFILE="/tmp/reconectar_auto.lock"
CREDS='administrador:cagr$2011'
SUBNET_LOCAL="192.168.2"

# --- Shares a montar (SMB URLs para Finder nativo) ---
declare -a SMB_URLS=(
    "smb://${CREDS}@192.168.2.111/c$/cowork_pedidos"
    "smb://${CREDS}@192.168.2.112/compartido"
)
# Nombres que Finder les asigna en /Volumes/
declare -a VOLUME_NAMES=(
    "cowork_pedidos"
    "compartido"
)

# --- IPs de prueba ---
TEST_IP="192.168.2.111"

# --- Colores (solo para terminal interactiva) ---
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'
    YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; CYAN=''; NC=''
fi

log() {
    echo -e "$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $(echo -e "$1" | sed 's/\x1b\[[0-9;]*m//g')" >> "$LOG"
}

notify() {
    # Notificación de macOS (funciona aunque corra como daemon)
    osascript -e "display notification \"$1\" with title \"Reconexión Red\"" 2>/dev/null
}

# --- Evitar ejecuciones simultáneas ---
if [ -f "$LOCKFILE" ]; then
    pid=$(cat "$LOCKFILE")
    if kill -0 "$pid" 2>/dev/null; then
        echo "Ya hay una instancia corriendo (PID $pid). Saliendo."
        exit 0
    fi
fi
echo $$ > "$LOCKFILE"
trap "rm -f $LOCKFILE" EXIT

# Esperar a que la red se estabilice después del cambio
sleep 3

log "${CYAN}══════════════════════════════════${NC}"
log "${CYAN}  RECONEXIÓN AUTOMÁTICA $(date '+%H:%M:%S')${NC}"
log "${CYAN}══════════════════════════════════${NC}"

# =============================================================
# 1. DETECTAR VPN: buscar servicio VPN configurado en macOS
# =============================================================
detect_vpn_service() {
    # VPN configurada en macOS: L2TP sobre IPSec → evirtual.calzalindo.com.ar
    echo "VPN (L2TP)"
}

# =============================================================
# 2. ¿ESTOY EN LA RED LOCAL?
# =============================================================
check_local_network() {
    # Verificar si tengo una IP en la subred local
    local my_ip
    my_ip=$(ifconfig 2>/dev/null | grep "inet ${SUBNET_LOCAL}" | head -1)

    if [ -n "$my_ip" ]; then
        return 0  # Estoy en la red local
    else
        return 1  # Estoy afuera
    fi
}

# =============================================================
# 3. CONECTAR VPN
# =============================================================
connect_vpn() {
    local vpn_name="$1"

    if [ -z "$vpn_name" ]; then
        log "${RED}✗ No encontré servicio VPN configurado en macOS${NC}"
        log "  Configuralo en Ajustes > Red > VPN"
        notify "❌ No hay VPN configurada"
        return 1
    fi

    # Ver si ya está conectada
    local status
    status=$(scutil --nc status "$vpn_name" 2>/dev/null | head -1)

    if [ "$status" = "Connected" ]; then
        log "${GREEN}✓ VPN '$vpn_name' ya conectada${NC}"
        return 0
    fi

    # Leer secreto IPSec desde Keychain
    local ipsec_secret
    ipsec_secret=$(security find-generic-password -a "VPN (L2TP)" -s "VPN IPSec Secret" -w 2>/dev/null)

    if [ -z "$ipsec_secret" ]; then
        log "${RED}✗ Falta secreto IPSec en Keychain${NC}"
        log "  Guardalo con: security add-generic-password -a 'VPN (L2TP)' -s 'VPN IPSec Secret' -w 'TU_SECRETO'"
        notify "❌ Falta secreto IPSec en Keychain"
        return 1
    fi

    log "${YELLOW}→ Conectando VPN '$vpn_name' (con IPSec secret)...${NC}"
    scutil --nc start "$vpn_name" --secret "$ipsec_secret" 2>/dev/null

    # Esperar conexión (máx 30 seg)
    for i in $(seq 1 30); do
        sleep 1
        status=$(scutil --nc status "$vpn_name" 2>/dev/null | head -1)
        if [ "$status" = "Connected" ]; then
            log "${GREEN}✓ VPN conectada (${i}s)${NC}"
            sleep 2  # Dar tiempo a que se establezcan las rutas
            return 0
        fi
    done

    log "${RED}✗ VPN no conectó después de 30s${NC}"
    notify "❌ VPN no conectó"
    return 1
}

# =============================================================
# 4. LÓGICA PRINCIPAL
# =============================================================

VPN_SERVICE=$(detect_vpn_service)
log "VPN detectada: ${VPN_SERVICE:-ninguna}"

if check_local_network; then
    log "${GREEN}✓ Estoy en la red local ($SUBNET_LOCAL.x)${NC}"
else
    log "${YELLOW}→ No estoy en la red local, necesito VPN${NC}"

    if ! connect_vpn "$VPN_SERVICE"; then
        log "${RED}✗ No pude conectar VPN. Abortando.${NC}"
        notify "❌ Sin VPN, no puedo montar shares"
        exit 1
    fi
fi

# Verificar que llego al servidor
log ""
log "${YELLOW}Verificando servidores...${NC}"
for ip in 192.168.2.111 192.168.2.112; do
    if ping -c 1 -W 3 "$ip" &>/dev/null; then
        log "  ${GREEN}✓ $ip OK${NC}"
    else
        log "  ${RED}✗ $ip no responde${NC}"
        notify "❌ Servidor $ip no responde"
        exit 1
    fi
done

# =============================================================
# 5. DESMONTAR SHARES COLGADOS + REMONTAR VIA FINDER NATIVO
# =============================================================
log ""
log "${YELLOW}Desmontando shares colgados...${NC}"

# Primero limpiar todo lo que quedó roto
for vol in "${VOLUME_NAMES[@]}"; do
    if mount | grep -q "/Volumes/$vol"; then
        umount -f "/Volumes/$vol" 2>/dev/null
        log "  ${YELLOW}⏏ Desmontado /Volumes/$vol${NC}"
        sleep 1
    fi
done

log "${YELLOW}Montando via Finder (aparecen en barra lateral)...${NC}"
OK=0; FAIL=0

for i in "${!SMB_URLS[@]}"; do
    url="${SMB_URLS[$i]}"
    vol="${VOLUME_NAMES[$i]}"

    # open smb:// es equivalente a Cmd+K en Finder → monta nativo
    open "$url" 2>/dev/null

    # Esperar a que aparezca el volumen (máx 15 seg)
    mounted=false
    for attempt in $(seq 1 15); do
        sleep 1
        if mount | grep -q "/Volumes/$vol"; then
            mounted=true
            break
        fi
    done

    if $mounted; then
        log "  ${GREEN}✓ /Volumes/$vol (${attempt}s)${NC}"
        ((OK++))
    else
        log "  ${RED}✗ /Volumes/$vol — no montó${NC}"
        ((FAIL++))
    fi
done

# Cerrar ventanas de Finder que se abrieron (solo queremos el sidebar)
sleep 1
osascript -e '
    tell application "Finder"
        close every window
    end tell
' 2>/dev/null

# =============================================================
# 7. RESULTADO
# =============================================================
log ""
if [ $FAIL -eq 0 ]; then
    log "${GREEN}══ Todo reconectado ($OK shares) ══${NC}"
    notify "✅ Reconectado: $OK shares montados"
else
    log "${YELLOW}══ $OK OK / $FAIL fallaron ══${NC}"
    notify "⚠️ Reconexión parcial: $FAIL shares fallaron"
fi
