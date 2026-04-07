#!/bin/bash
# monitor_respuestas.sh — Runs responder_agencias.py --once and logs output
# Designed to be called every 30 seconds via launchd or cron.
#
# Usage (manual):   ./monitor_respuestas.sh
# Usage (cron):     * * * * * /path/to/monitor_respuestas.sh
#                   * * * * * sleep 30 && /path/to/monitor_respuestas.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/log_monitor.txt"
PYTHON="python3"

echo "--------------------------------------------" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ejecutando responder_agencias.py --once" >> "$LOG_FILE"

"$PYTHON" "$SCRIPT_DIR/responder_agencias.py" --once >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Exit code: $EXIT_CODE" >> "$LOG_FILE"
