#!/usr/bin/env bash
# =============================================================================
# orquestador.sh — Mantiene agentes Claude corriendo toda la noche
# Cada proyecto corre en su propia sesión tmux.
# Loop cada 5 minutos verificando estado y relanzando si es necesario.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONF="$SCRIPT_DIR/projects.conf"
LOG="$SCRIPT_DIR/orquestador.log"
PIDS_DIR="$SCRIPT_DIR/.pids"
MAX_RESTARTS=50          # máximo relanzamientos por proyecto por ejecución
CHECK_INTERVAL=300       # 5 minutos entre checks
STUCK_TIMEOUT=1800       # 30 min sin output = colgado

mkdir -p "$PIDS_DIR"

# --- Logging ---
log() {
    local ts
    ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$ts] $*" | tee -a "$LOG"
}

# --- Leer último estado de bitácora ---
get_last_context() {
    local dir="$1" bitacora="$2"
    local file="$dir/$bitacora"

    if [[ -f "$file" ]]; then
        # Extraer últimas 30 líneas como contexto
        local context
        context=$(tail -30 "$file" 2>/dev/null || echo "")
        if [[ -n "$context" ]]; then
            echo "Leé $bitacora y continuá desde donde quedaste en la última sesión. Contexto reciente del archivo: $(echo "$context" | head -10)"
            return
        fi
    fi

    # Fallback: buscar SESSION_LOG.md o BITACORA_DESARROLLO.md
    for fallback in SESSION_LOG.md BITACORA_DESARROLLO.md CLAUDE.md; do
        if [[ -f "$dir/$fallback" ]]; then
            echo "Leé $fallback y continuá desde donde quedaste en la última sesión."
            return
        fi
    done

    echo "Revisá el estado del proyecto y continuá con las tareas pendientes."
}

# --- Verificar si sesión tmux está viva y activa ---
session_alive() {
    local name="$1"
    tmux has-session -t "$name" 2>/dev/null
}

# --- Verificar si el proceso claude dentro de tmux sigue corriendo ---
claude_running_in_session() {
    local name="$1"
    # Capturar PID del pane y verificar si claude está en el árbol de procesos
    local pane_pid
    pane_pid=$(tmux list-panes -t "$name" -F '#{pane_pid}' 2>/dev/null | head -1)
    if [[ -z "$pane_pid" ]]; then
        return 1
    fi
    # Verificar si hay un proceso claude hijo
    pgrep -P "$pane_pid" -f "claude" >/dev/null 2>&1
}

# --- Verificar si está colgado (sin output reciente) ---
is_stuck() {
    local name="$1"
    local marker="$PIDS_DIR/${name}.last_activity"

    # Capturar contenido actual del pane
    local current_content
    current_content=$(tmux capture-pane -t "$name" -p 2>/dev/null | tail -5 | md5 2>/dev/null || echo "")

    if [[ -f "$marker" ]]; then
        local last_content
        last_content=$(cat "$marker")
        if [[ "$current_content" == "$last_content" ]]; then
            local last_mod
            last_mod=$(stat -f %m "$marker" 2>/dev/null || echo 0)
            local now
            now=$(date +%s)
            local diff=$((now - last_mod))
            if [[ $diff -gt $STUCK_TIMEOUT ]]; then
                return 0  # está colgado
            fi
        else
            echo "$current_content" > "$marker"
        fi
    else
        echo "$current_content" > "$marker"
    fi
    return 1  # no está colgado
}

# --- Matar sesión tmux ---
kill_session() {
    local name="$1"
    log "KILL: Matando sesión $name"
    tmux kill-session -t "$name" 2>/dev/null || true
    rm -f "$PIDS_DIR/${name}.last_activity"
}

# --- Lanzar agente Claude en sesión tmux ---
launch_agent() {
    local name="$1" dir="$2" bitacora="$3"
    local restart_file="$PIDS_DIR/${name}.restarts"

    # Verificar límite de restarts
    local restarts=0
    if [[ -f "$restart_file" ]]; then
        restarts=$(cat "$restart_file")
    fi
    if [[ $restarts -ge $MAX_RESTARTS ]]; then
        log "SKIP: $name alcanzó máximo de $MAX_RESTARTS relanzamientos"
        return 1
    fi

    # Verificar que el directorio existe
    if [[ ! -d "$dir" ]]; then
        log "ERROR: Directorio no existe: $dir"
        return 1
    fi

    # Obtener contexto
    local prompt
    prompt=$(get_last_context "$dir" "$bitacora")

    # Matar sesión anterior si existe
    tmux kill-session -t "$name" 2>/dev/null || true

    log "LAUNCH: $name en $dir (restart #$((restarts + 1)))"
    log "  PROMPT: ${prompt:0:100}..."

    # Crear sesión tmux y lanzar claude
    tmux new-session -d -s "$name" -c "$dir" \
        "claude --dangerously-skip-permissions -p '$prompt' 2>&1 | tee -a '$SCRIPT_DIR/logs/${name}.log'; echo '=== CLAUDE TERMINÓ ===' ; sleep 30"

    # Incrementar contador
    echo $((restarts + 1)) > "$restart_file"

    # Inicializar marker de actividad
    sleep 3
    tmux capture-pane -t "$name" -p 2>/dev/null | tail -5 | md5 > "$PIDS_DIR/${name}.last_activity" 2>/dev/null || true
}

# --- Parsear projects.conf ---
parse_projects() {
    local projects=()
    while IFS='|' read -r name dir bitacora; do
        # Saltar comentarios y líneas vacías
        [[ "$name" =~ ^#.*$ ]] && continue
        [[ -z "$name" ]] && continue
        name=$(echo "$name" | xargs)  # trim
        dir=$(echo "$dir" | xargs)
        bitacora=$(echo "$bitacora" | xargs)
        # Expandir ~
        dir="${dir/#\~/$HOME}"
        projects+=("$name|$dir|$bitacora")
    done < "$CONF"
    echo "${projects[@]}"
}

# --- Dashboard status ---
print_status() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              ORQUESTADOR OVERNIGHT — STATUS                 ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    printf "║ %-20s │ %-10s │ %-8s │ %-12s ║\n" "PROYECTO" "ESTADO" "RESTARTS" "ÚLTIMO CHECK"
    echo "╠══════════════════════════════════════════════════════════════╣"

    for project in $(parse_projects); do
        IFS='|' read -r name dir bitacora <<< "$project"
        local status="?"
        local restarts=0
        local last_check
        last_check=$(date '+%H:%M:%S')

        if session_alive "$name"; then
            if claude_running_in_session "$name"; then
                status="RUNNING"
            else
                status="FINISHED"
            fi
        else
            status="DOWN"
        fi

        if [[ -f "$PIDS_DIR/${name}.restarts" ]]; then
            restarts=$(cat "$PIDS_DIR/${name}.restarts")
        fi

        printf "║ %-20s │ %-10s │ %-8s │ %-12s ║\n" "$name" "$status" "$restarts" "$last_check"
    done

    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

# --- Main loop ---
main() {
    log "=========================================="
    log "ORQUESTADOR INICIADO"
    log "Config: $CONF"
    log "Check interval: ${CHECK_INTERVAL}s"
    log "=========================================="

    # Crear directorio de logs
    mkdir -p "$SCRIPT_DIR/logs"

    # Reset contadores de restart
    rm -f "$PIDS_DIR"/*.restarts

    # Lanzamiento inicial de todos los proyectos
    for project in $(parse_projects); do
        IFS='|' read -r name dir bitacora <<< "$project"
        launch_agent "$name" "$dir" "$bitacora"
        sleep 5  # espacio entre lanzamientos para no saturar
    done

    log "Todos los agentes lanzados. Entrando en loop de monitoreo..."

    # Loop de monitoreo
    while true; do
        sleep "$CHECK_INTERVAL"

        log "--- CHECK $(date '+%H:%M:%S') ---"

        for project in $(parse_projects); do
            IFS='|' read -r name dir bitacora <<< "$project"

            if session_alive "$name"; then
                if claude_running_in_session "$name"; then
                    # Verificar si está colgado
                    if is_stuck "$name"; then
                        log "STUCK: $name parece colgado (sin cambios en ${STUCK_TIMEOUT}s)"
                        kill_session "$name"
                        launch_agent "$name" "$dir" "$bitacora"
                    else
                        log "OK: $name corriendo normalmente"
                    fi
                else
                    log "FINISHED: $name terminó — relanzando"
                    kill_session "$name"
                    launch_agent "$name" "$dir" "$bitacora"
                fi
            else
                log "DOWN: sesión $name no existe — relanzando"
                launch_agent "$name" "$dir" "$bitacora"
            fi
        done

        print_status >> "$LOG"
    done
}

# --- Ejecución ---
if [[ "${1:-}" == "--status" ]]; then
    print_status
    exit 0
fi

main "$@"
