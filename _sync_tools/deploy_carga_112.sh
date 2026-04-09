#!/bin/bash
# DEPRECADO: Usar ./deploy.sh carga
echo -e "\033[1;33mAVISO: Este script esta deprecado. Usar: ./deploy.sh carga\033[0m"
exec "$(dirname "$0")/deploy.sh" carga
