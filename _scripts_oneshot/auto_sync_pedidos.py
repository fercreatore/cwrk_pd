# -*- coding: utf-8 -*-
"""
AUTO SYNC PEDIDOS — Ejecutar con Windows Task Scheduler
========================================================
Llama a sp_sync_pedidos para refrescar la cache de cumplimiento.
Correr en 111 con: py -3 auto_sync_pedidos.py

Para programar cada 30 min:
  schtasks /create /tn "SyncPedidosCache" /tr "py -3 C:\cowork_pedidos\_scripts_oneshot\auto_sync_pedidos.py" /sc minute /mo 30 /ru SYSTEM
"""

import pyodbc
import datetime
import os

LOG_FILE = r"C:\cowork_pedidos\_scripts_oneshot\sync_pedidos.log"

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[{}] {}".format(ts, msg)
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def sync():
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=192.168.2.111;"
        "DATABASE=omicronvt;"
        "UID=am;PWD=dl;"
    )
    try:
        conn = pyodbc.connect(conn_str, timeout=30)
        cursor = conn.cursor()
        cursor.execute("EXEC omicronvt.dbo.sp_sync_pedidos")
        row = cursor.fetchone()
        filas = row[0] if row else "?"
        conn.commit()
        cursor.close()
        conn.close()
        log("OK - {} filas sincronizadas".format(filas))
    except Exception as e:
        log("ERROR - {}".format(str(e)))

if __name__ == "__main__":
    log("--- Inicio sync automatico ---")
    sync()
