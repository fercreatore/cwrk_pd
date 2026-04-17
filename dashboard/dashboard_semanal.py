#!/usr/bin/env python3
"""
dashboard_semanal.py — Dashboard semanal de decisiones H4 / CALZALINDO
Genera un informe markdown con métricas clave y lo envía por Telegram.

Uso:
    python3 dashboard/dashboard_semanal.py            # completo
    python3 dashboard/dashboard_semanal.py --solo-pdf  # solo guarda archivo, no envía
    python3 dashboard/dashboard_semanal.py --solo-macro # solo datos macro (sin SQL)
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import json

# ── Agregar raíz del proyecto al path ─────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

# ── Telegram ───────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = "8650255274:AAHqQ6pacJ8yjvLXYUht2d7Ot181w3_HISo"
TELEGRAM_CHAT_ID   = "5624243292"


def enviar_telegram(texto: str) -> bool:
    try:
        url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({
            "chat_id":    TELEGRAM_CHAT_ID,
            "text":       texto,
            "parse_mode": "HTML",
        }).encode()
        req  = urllib.request.Request(url, data=data,
                                      headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Telegram] Error al enviar: {e}")
        return False


# ── SQL helpers ────────────────────────────────────────────────────────────

def get_conn():
    import pyodbc
    from config import CONN_COMPRAS
    return pyodbc.connect(CONN_COMPRAS)


def query(conn, sql: str):
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return [dict(zip(cols, r)) for r in rows]


# ── Métricas SQL ───────────────────────────────────────────────────────────

def ventas_semana(conn):
    hoy    = datetime.today()
    lunes  = hoy - timedelta(days=hoy.weekday())
    semana_ant = lunes - timedelta(days=7)

    sql = f"""
        SELECT
            SUM(CASE WHEN CONVERT(date, fecha) >= '{lunes.strftime('%Y-%m-%d')}'
                     THEN precio_venta * cantidad ELSE 0 END) AS venta_esta_semana,
            SUM(CASE WHEN CONVERT(date, fecha) >= '{semana_ant.strftime('%Y-%m-%d')}'
                      AND CONVERT(date, fecha) <  '{lunes.strftime('%Y-%m-%d')}'
                     THEN precio_venta * cantidad ELSE 0 END) AS venta_semana_ant,
            SUM(CASE WHEN CONVERT(date, fecha) >= '{lunes.strftime('%Y-%m-%d')}'
                     THEN cantidad ELSE 0 END) AS pares_esta_semana,
            SUM(CASE WHEN CONVERT(date, fecha) >= '{semana_ant.strftime('%Y-%m-%d')}'
                      AND CONVERT(date, fecha) <  '{lunes.strftime('%Y-%m-%d')}'
                     THEN cantidad ELSE 0 END) AS pares_semana_ant
        FROM msgestionC.dbo.ventas1
        WHERE codigo NOT IN (7, 36)
          AND operacion = '-'
          AND CONVERT(date, fecha) >= '{semana_ant.strftime('%Y-%m-%d')}'
    """
    rows = query(conn, sql)
    return rows[0] if rows else {}


def ventas_mes(conn):
    hoy      = datetime.today()
    ini_mes  = hoy.replace(day=1)
    ini_mes_ant = (ini_mes - timedelta(days=1)).replace(day=1)

    sql = f"""
        SELECT
            SUM(CASE WHEN CONVERT(date, fecha) >= '{ini_mes.strftime('%Y-%m-%d')}'
                     THEN precio_venta * cantidad ELSE 0 END) AS venta_mes,
            SUM(CASE WHEN CONVERT(date, fecha) >= '{ini_mes_ant.strftime('%Y-%m-%d')}'
                      AND CONVERT(date, fecha) <  '{ini_mes.strftime('%Y-%m-%d')}'
                     THEN precio_venta * cantidad ELSE 0 END) AS venta_mes_ant,
            SUM(CASE WHEN CONVERT(date, fecha) >= '{ini_mes.strftime('%Y-%m-%d')}'
                     THEN cantidad ELSE 0 END) AS pares_mes,
            SUM(CASE WHEN CONVERT(date, fecha) >= '{ini_mes_ant.strftime('%Y-%m-%d')}'
                      AND CONVERT(date, fecha) <  '{ini_mes.strftime('%Y-%m-%d')}'
                     THEN cantidad ELSE 0 END) AS pares_mes_ant
        FROM msgestionC.dbo.ventas1
        WHERE codigo NOT IN (7, 36)
          AND operacion = '-'
          AND CONVERT(date, fecha) >= '{ini_mes_ant.strftime('%Y-%m-%d')}'
    """
    rows = query(conn, sql)
    return rows[0] if rows else {}


def alertas_stock(conn):
    """Top artículos con stock ≤ 0 y ventas recientes (quiebre activo)."""
    sql = """
        SELECT TOP 15
            s.articulo,
            a.descripcion,
            SUM(s.stock_actual) AS stock_total,
            ISNULL(v.pares_30d, 0) AS pares_30d
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        LEFT JOIN (
            SELECT articulo, SUM(cantidad) AS pares_30d
            FROM msgestionC.dbo.ventas1
            WHERE codigo NOT IN (7, 36)
              AND operacion = '-'
              AND CONVERT(date, fecha) >= CONVERT(date, DATEADD(day,-30,GETDATE()))
            GROUP BY articulo
        ) v ON v.articulo = s.articulo
        WHERE a.marca NOT IN (1316, 1317, 1158, 436)
        GROUP BY s.articulo, a.descripcion, v.pares_30d
        HAVING SUM(s.stock_actual) <= 0 AND ISNULL(v.pares_30d, 0) >= 3
        ORDER BY ISNULL(v.pares_30d, 0) DESC
    """
    return query(conn, sql)


def pedidos_pendientes(conn):
    """Pedidos de compra en estado V (vigente) sin recibir."""
    sql = """
        SELECT TOP 10
            p2.numero,
            p2.razon_social,
            p2.fecha,
            SUM(p1.cantidad) AS pares,
            SUM(p1.precio * p1.cantidad) AS monto
        FROM msgestionC.dbo.pedico2 p2
        JOIN msgestionC.dbo.pedico1 p1 ON p1.numero = p2.numero
        WHERE p2.estado = 'V'
          AND p2.codigo = 8
        GROUP BY p2.numero, p2.razon_social, p2.fecha
        ORDER BY p2.fecha DESC
    """
    return query(conn, sql)


def top_marcas_semana(conn):
    """Top 5 marcas por venta esta semana."""
    hoy   = datetime.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    sql = f"""
        SELECT TOP 5
            a.marca,
            m.descripcion AS marca_desc,
            SUM(v.precio_venta * v.cantidad) AS venta,
            SUM(v.cantidad) AS pares
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        JOIN msgestion01art.dbo.marcas m ON m.codigo = a.marca
        WHERE v.codigo NOT IN (7, 36)
          AND v.operacion = '-'
          AND a.marca NOT IN (1316, 1317, 1158, 436)
          AND CONVERT(date, v.fecha) >= '{lunes.strftime('%Y-%m-%d')}'
        GROUP BY a.marca, m.descripcion
        ORDER BY venta DESC
    """
    return query(conn, sql)


# ── Formato ────────────────────────────────────────────────────────────────

def fmt_m(valor) -> str:
    """Formatea número grande como $1.2M o $345K."""
    if valor is None:
        return "$—"
    v = float(valor)
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


def flecha(actual, anterior) -> str:
    if not actual or not anterior or float(anterior) == 0:
        return ""
    pct = (float(actual) - float(anterior)) / float(anterior) * 100
    sym = "▲" if pct >= 0 else "▼"
    return f"{sym}{abs(pct):.1f}%"


# ── Sección macro (hardcodeada / fácil de actualizar) ─────────────────────

def seccion_macro() -> str:
    hoy = datetime.today()
    return f"""
📊 <b>MACRO ARGENTINA — {hoy.strftime('%d/%m/%Y')}</b>

🟡 Inflación: ~3% mensual (INDEC pub. ~14 de cada mes)
🟢 Tipo de cambio: dólar oficial ~$1.420 | bandas flotantes
🔴 Consumo minorista pymes: -5.6% interanual (feb-2026)
🔴 Aranceles calzado: 20% (bajaron de 35%) → importaciones +71%

<i>Actualizar con dato INDEC cuando se publique (día 14).</i>
""".strip()


# ── Construcción del informe ───────────────────────────────────────────────

def construir_informe(solo_macro: bool = False) -> str:
    hoy = datetime.today()
    lines = []

    lines.append(f"🗓 <b>DASHBOARD SEMANAL — H4 / CALZALINDO</b>")
    lines.append(f"<i>{hoy.strftime('%A %d de %B de %Y').capitalize()}</i>")
    lines.append("")

    # ── Macro ──────────────────────────────────────────────────────────────
    lines.append(seccion_macro())
    lines.append("")

    if solo_macro:
        lines.append("<i>⚠️ Modo --solo-macro: datos SQL no disponibles.</i>")
        return "\n".join(lines)

    # ── SQL ────────────────────────────────────────────────────────────────
    try:
        conn = get_conn()
    except Exception as e:
        lines.append(f"<i>⚠️ Sin conexión SQL: {e}</i>")
        return "\n".join(lines)

    # Ventas semana
    try:
        vsem = ventas_semana(conn)
        vmes = ventas_mes(conn)

        lines.append("💰 <b>VENTAS</b>")
        vv  = vsem.get("venta_esta_semana") or 0
        vva = vsem.get("venta_semana_ant") or 0
        pv  = vsem.get("pares_esta_semana") or 0
        pva = vsem.get("pares_semana_ant") or 0
        lines.append(f"  Esta semana:  {fmt_m(vv)} ({int(pv or 0)} pares) {flecha(vv, vva)}")
        lines.append(f"  Semana ant.:  {fmt_m(vva)} ({int(pva or 0)} pares)")

        vm  = vmes.get("venta_mes") or 0
        vma = vmes.get("venta_mes_ant") or 0
        pm  = vmes.get("pares_mes") or 0
        pma = vmes.get("pares_mes_ant") or 0
        lines.append(f"  Mes actual:   {fmt_m(vm)} ({int(pm or 0)} pares) {flecha(vm, vma)}")
        lines.append(f"  Mes anterior: {fmt_m(vma)} ({int(pma or 0)} pares)")
        lines.append("")
    except Exception as e:
        lines.append(f"  <i>Error ventas: {e}</i>\n")

    # Top marcas
    try:
        marcas = top_marcas_semana(conn)
        if marcas:
            lines.append("🏆 <b>TOP MARCAS (semana)</b>")
            for i, m in enumerate(marcas, 1):
                desc  = (m.get("marca_desc") or "")[:20]
                venta = fmt_m(m.get("venta"))
                pares = int(m.get("pares") or 0)
                lines.append(f"  {i}. {desc:<20} {venta}  ({pares} pares)")
            lines.append("")
    except Exception as e:
        lines.append(f"  <i>Error marcas: {e}</i>\n")

    # Quiebre activo
    try:
        quiebres = alertas_stock(conn)
        if quiebres:
            lines.append("🚨 <b>QUIEBRE ACTIVO (stock≤0 + ventas últimos 30d)</b>")
            for q in quiebres[:8]:
                desc  = (q.get("descripcion") or "")[:25]
                pares = int(q.get("pares_30d") or 0)
                lines.append(f"  ⛔ {desc:<25}  {pares}p/30d")
            if len(quiebres) > 8:
                lines.append(f"  ... y {len(quiebres)-8} más")
            lines.append("")
        else:
            lines.append("✅ <b>Sin quiebres activos detectados</b>\n")
    except Exception as e:
        lines.append(f"  <i>Error stock: {e}</i>\n")

    # Pedidos pendientes
    try:
        pedidos = pedidos_pendientes(conn)
        if pedidos:
            lines.append("📦 <b>PEDIDOS VIGENTES (estado V)</b>")
            for p in pedidos[:5]:
                razon  = (p.get("razon_social") or "")[:22]
                pares  = int(p.get("pares") or 0)
                monto  = fmt_m(p.get("monto"))
                fecha  = str(p.get("fecha") or "")[:10]
                lines.append(f"  • {razon:<22} {pares}p  {monto}  ({fecha})")
            if len(pedidos) > 5:
                lines.append(f"  ... y {len(pedidos)-5} más")
            lines.append("")
    except Exception as e:
        lines.append(f"  <i>Error pedidos: {e}</i>\n")

    conn.close()

    lines.append(f"<i>Generado: {hoy.strftime('%d/%m/%Y %H:%M')}</i>")
    return "\n".join(lines)


# ── Guardar markdown ───────────────────────────────────────────────────────

def guardar_informe(texto: str) -> str:
    fecha = datetime.today().strftime("%Y-%m-%d")
    carpeta = os.path.join(_ROOT, "_informes")
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"dashboard_semanal_{fecha}.md")

    # Guardar versión sin HTML tags (más legible en markdown)
    import re
    md = re.sub(r"<[^>]+>", "", texto)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(md)
    return ruta


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Dashboard semanal H4/CALZALINDO")
    parser.add_argument("--solo-pdf",   action="store_true",
                        help="Solo genera el archivo, no envía por Telegram")
    parser.add_argument("--solo-macro", action="store_true",
                        help="Solo datos macro (sin conexión SQL)")
    args = parser.parse_args()

    print("Generando dashboard semanal...")

    informe = construir_informe(solo_macro=args.solo_macro)

    # Guardar siempre
    ruta = guardar_informe(informe)
    print(f"✅ Informe guardado en: {ruta}")

    # Enviar por Telegram (salvo --solo-pdf)
    if args.solo_pdf:
        print("Modo --solo-pdf: no se envía por Telegram.")
        return

    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "TU_TOKEN_AQUI":
        print("⚠️  TOKEN de Telegram no configurado. Correr con --solo-pdf.")
        print(f"   Informe guardado en: {ruta}")
        return

    # Telegram limita mensajes a 4096 chars
    MAX = 4000
    if len(informe) > MAX:
        partes = [informe[i:i+MAX] for i in range(0, len(informe), MAX)]
        ok = all(enviar_telegram(p) for p in partes)
    else:
        ok = enviar_telegram(informe)

    if ok:
        print("✅ Dashboard enviado por Telegram.")
    else:
        print("❌ Error al enviar por Telegram. Ver informe guardado.")
        print(f"   Ruta: {ruta}")


if __name__ == "__main__":
    main()
