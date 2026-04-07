#!/usr/bin/env python3
"""
gestionar_optout.py - Gestionar lista de opt-out WhatsApp Calzalindo

Uso:
    python3 gestionar_optout.py list                              # Listar todos
    python3 gestionar_optout.py add +5493462XXXXXX "Nombre"       # Agregar
    python3 gestionar_optout.py add +5493462XXXXXX "Nombre" "motivo"  # Con motivo
    python3 gestionar_optout.py remove +5493462XXXXXX             # Quitar
"""
import json
import os
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPTOUT_FILE = os.path.join(SCRIPT_DIR, "optout_list.json")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_optouts() -> list:
    if os.path.exists(OPTOUT_FILE):
        try:
            with open(OPTOUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_optouts(data: list):
    with open(OPTOUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalizar_telefono(tel: str) -> str:
    """Normaliza a formato sin + para comparacion consistente."""
    return tel.lstrip("+").strip()


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_list():
    optouts = load_optouts()
    if not optouts:
        print("No hay opt-outs registrados.")
        return
    print(f"\n{'='*70}")
    print(f" LISTA DE OPT-OUTS ({len(optouts)} registros)")
    print(f"{'='*70}")
    for i, entry in enumerate(optouts, 1):
        tel = entry.get("telefono", "?")
        nombre = entry.get("nombre", "")
        motivo = entry.get("motivo", "")
        origen = entry.get("origen", "")
        fecha = entry.get("fecha_baja", "")
        print(f"  {i}. {tel}  {nombre}")
        if motivo:
            print(f"     Motivo: {motivo}")
        print(f"     Origen: {origen} | Fecha: {fecha}")
    print(f"{'='*70}\n")


def cmd_add(telefono: str, nombre: str = "", motivo: str = ""):
    tel_norm = normalizar_telefono(telefono)
    optouts = load_optouts()

    # Verificar si ya existe
    for entry in optouts:
        if normalizar_telefono(entry.get("telefono", "")) == tel_norm:
            print(f"El telefono {telefono} ya esta en la lista de opt-out.")
            return

    entry = {
        "telefono": tel_norm,
        "nombre": nombre,
        "motivo": motivo,
        "origen": "manual",
        "fecha_baja": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    optouts.append(entry)
    save_optouts(optouts)
    print(f"Agregado: {tel_norm} ({nombre}) a la lista de opt-out.")


def cmd_remove(telefono: str):
    tel_norm = normalizar_telefono(telefono)
    optouts = load_optouts()
    new_list = [e for e in optouts if normalizar_telefono(e.get("telefono", "")) != tel_norm]

    if len(new_list) == len(optouts):
        print(f"El telefono {telefono} no estaba en la lista de opt-out.")
        return

    save_optouts(new_list)
    print(f"Removido: {tel_norm} de la lista de opt-out.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "list":
        cmd_list()
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Uso: python3 gestionar_optout.py add +5493462XXXXXX \"Nombre\" [\"motivo\"]")
            return
        telefono = sys.argv[2]
        nombre = sys.argv[3] if len(sys.argv) > 3 else ""
        motivo = sys.argv[4] if len(sys.argv) > 4 else ""
        cmd_add(telefono, nombre, motivo)
    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("Uso: python3 gestionar_optout.py remove +5493462XXXXXX")
            return
        telefono = sys.argv[2]
        cmd_remove(telefono)
    else:
        print(f"Comando desconocido: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
