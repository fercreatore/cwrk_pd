#!/bin/bash
# DEPRECADO: Usar ./deploy.sh web2py
echo -e "\033[1;33mAVISO: Este script esta deprecado. Usar: ./deploy.sh web2py\033[0m"
exec "$(dirname "$0")/deploy.sh" web2py
