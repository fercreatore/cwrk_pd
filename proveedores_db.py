#!/usr/bin/env python3
"""
Módulo de proveedores dinámico — lee todo desde la base de datos.
Reemplaza la configuración estática de config.py PROVEEDORES.

Funciones:
  buscar_proveedor_por_cuit(cuit) → dict con toda la config
  buscar_proveedor_por_nombre(nombre) → dict
  listar_proveedores_activos() → lista de proveedores con artículos recientes
  obtener_pricing_proveedor(numero, marca=None) → descuento, utilidades, etc.
"""

import logging
import pyodbc
from functools import lru_cache

log = logging.getLogger("proveedores_db")


def _get_conn():
    """Obtiene conexión a SQL Server."""
    from config import CONN_COMPRAS
    return pyodbc.connect(CONN_COMPRAS, timeout=10)


@lru_cache(maxsize=1)
def listar_proveedores_activos():
    """
    Lista proveedores que tienen artículos cargados (activos).
    Retorna dict {numero: {nombre, cuit, zona, condicion_iva, marcas, ...}}
    """
    sql = """
        SELECT p.numero, p.denominacion, p.cuit, p.condicion_iva, p.zona,
               COUNT(DISTINCT a.codigo) AS cant_articulos,
               MAX(a.codigo) AS ultimo_articulo
        FROM msgestionC.dbo.proveedores p
        JOIN msgestion01art.dbo.articulo a ON a.proveedor = p.numero
        WHERE a.estado = 'V'
        GROUP BY p.numero, p.denominacion, p.cuit, p.condicion_iva, p.zona
        HAVING COUNT(DISTINCT a.codigo) >= 5
        ORDER BY p.denominacion
    """
    proveedores = {}
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for row in cursor.fetchall():
                proveedores[row.numero] = {
                    "numero": row.numero,
                    "nombre": row.denominacion.strip() if row.denominacion else "",
                    "cuit": (row.cuit or "").strip().replace("-", ""),
                    "condicion_iva": (row.condicion_iva or "I").strip(),
                    "zona": row.zona or 0,
                    "cant_articulos": row.cant_articulos,
                }
    except Exception as e:
        log.error(f"Error listando proveedores: {e}")
    return proveedores


@lru_cache(maxsize=1)
def listar_todos_proveedores():
    """
    Lista TODOS los proveedores activos de la tabla proveedores (motivo_baja='A').
    Incluye cantidad de artículos (puede ser 0 para proveedores nuevos).
    Retorna dict {numero: {nombre, cuit, zona, condicion_iva, cant_articulos}}
    """
    sql = """
        SELECT p.numero, RTRIM(p.denominacion) as nombre,
               RTRIM(ISNULL(p.cuit,'')) as cuit,
               ISNULL(p.condicion_iva,'I') as condicion_iva,
               ISNULL(p.zona,0) as zona,
               ISNULL(ac.cant, 0) as cant_articulos
        FROM msgestionC.dbo.proveedores p
        LEFT JOIN (
            SELECT proveedor, COUNT(*) as cant
            FROM msgestion01art.dbo.articulo
            WHERE estado = 'V'
            GROUP BY proveedor
        ) ac ON ac.proveedor = p.numero
        WHERE p.motivo_baja = 'A'
        ORDER BY p.denominacion
    """
    proveedores = {}
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for row in cursor.fetchall():
                proveedores[row.numero] = {
                    "numero": row.numero,
                    "nombre": row.nombre.strip() if row.nombre else "",
                    "cuit": (row.cuit or "").strip().replace("-", ""),
                    "condicion_iva": (row.condicion_iva or "I").strip(),
                    "zona": row.zona or 0,
                    "cant_articulos": row.cant_articulos or 0,
                }
    except Exception as e:
        log.error(f"Error listando todos los proveedores: {e}")
    return proveedores


def buscar_proveedor_por_cuit(cuit: str) -> dict | None:
    """Busca proveedor por CUIT. Retorna dict con config completa o None."""
    cuit_limpio = cuit.replace("-", "").replace(" ", "").strip()
    if not cuit_limpio:
        return None

    sql = """
        SELECT numero, denominacion, cuit, condicion_iva, zona
        FROM msgestionC.dbo.proveedores
        WHERE REPLACE(REPLACE(cuit, '-', ''), ' ', '') = ?
    """
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, cuit_limpio)
            row = cursor.fetchone()
            if row:
                prov = {
                    "numero": row.numero,
                    "nombre": row.denominacion.strip(),
                    "cuit": cuit_limpio,
                    "condicion_iva": (row.condicion_iva or "I").strip(),
                    "zona": row.zona or 0,
                }
                # Obtener pricing automático
                pricing = obtener_pricing_proveedor(row.numero)
                prov.update(pricing)
                return prov
    except Exception as e:
        log.error(f"Error buscando CUIT {cuit}: {e}")
    return None


def buscar_proveedor_por_nombre(nombre: str) -> dict | None:
    """Busca proveedor por nombre parcial. Retorna el más relevante."""
    if not nombre or len(nombre) < 3:
        return None

    sql = """
        SELECT TOP 1 p.numero, p.denominacion, p.cuit, p.condicion_iva, p.zona,
               COUNT(DISTINCT a.codigo) AS cant
        FROM msgestionC.dbo.proveedores p
        JOIN msgestion01art.dbo.articulo a ON a.proveedor = p.numero
        WHERE p.denominacion LIKE ?
        GROUP BY p.numero, p.denominacion, p.cuit, p.condicion_iva, p.zona
        ORDER BY cant DESC
    """
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, f"%{nombre}%")
            row = cursor.fetchone()
            if row:
                prov = {
                    "numero": row.numero,
                    "nombre": row.denominacion.strip(),
                    "cuit": (row.cuit or "").strip().replace("-", ""),
                    "condicion_iva": (row.condicion_iva or "I").strip(),
                    "zona": row.zona or 0,
                }
                pricing = obtener_pricing_proveedor(row.numero)
                prov.update(pricing)
                return prov
    except Exception as e:
        log.error(f"Error buscando nombre '{nombre}': {e}")
    return None


def obtener_pricing_proveedor(numero: int, marca: int = None) -> dict:
    """
    Obtiene pricing del proveedor basándose en sus artículos más recientes.
    Si se especifica marca, filtra por esa marca.

    Retorna: {marca, descuento, utilidad_1..4, formula, rubro, subrubro, descuento_1, descuento_2}
    """
    filtro_marca = "AND a.marca = ?" if marca else ""
    params = [numero, marca] if marca else [numero]

    sql = f"""
        SELECT TOP 1
            a.marca, a.descuento, a.descuento_1, a.descuento_2,
            a.utilidad_1, a.utilidad_2, a.utilidad_3, a.utilidad_4,
            a.formula, a.rubro, a.subrubro
        FROM msgestion01art.dbo.articulo a
        WHERE a.proveedor = ? {filtro_marca}
          AND a.estado = 'V'
          AND a.precio_fabrica > 0
        ORDER BY a.codigo DESC
    """
    defaults = {
        "marca": 0,
        "descuento": 0,
        "descuento_1": 0,
        "descuento_2": 0,
        "utilidad_1": 80,
        "utilidad_2": 100,
        "utilidad_3": 60,
        "utilidad_4": 45,
        "formula": 1,
        "rubro": 4,
        "subrubro": 52,
    }
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, *[params])
            row = cursor.fetchone()
            if row:
                return {
                    "marca": row.marca or 0,
                    "descuento": row.descuento or 0,
                    "descuento_1": row.descuento_1 or 0,
                    "descuento_2": row.descuento_2 or 0,
                    "utilidad_1": row.utilidad_1 or 80,
                    "utilidad_2": row.utilidad_2 or 100,
                    "utilidad_3": row.utilidad_3 or 60,
                    "utilidad_4": row.utilidad_4 or 45,
                    "formula": row.formula or 1,
                    "rubro": row.rubro or 4,
                    "subrubro": row.subrubro or 52,
                }
    except Exception as e:
        log.error(f"Error obteniendo pricing proveedor {numero}: {e}")
    return defaults


def obtener_marcas_proveedor(numero: int) -> list[dict]:
    """
    Lista las marcas que maneja un proveedor con cantidad de artículos.
    Retorna [{marca, cant, desc_ejemplo}]
    """
    sql = """
        SELECT a.marca, COUNT(*) AS cant,
               (SELECT TOP 1 descripcion_1 FROM msgestion01art.dbo.articulo
                WHERE proveedor = ? AND marca = a.marca ORDER BY codigo DESC) AS ejemplo
        FROM msgestion01art.dbo.articulo a
        WHERE a.proveedor = ? AND a.estado = 'V'
        GROUP BY a.marca
        ORDER BY cant DESC
    """
    marcas = []
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, numero, numero)
            for row in cursor.fetchall():
                marcas.append({
                    "marca": row.marca,
                    "cant": row.cant,
                    "ejemplo": (row.ejemplo or "")[:50],
                })
    except Exception as e:
        log.error(f"Error obteniendo marcas proveedor {numero}: {e}")
    return marcas


def auto_detectar_proveedor_factura(cuit: str = None, nombre: str = None) -> dict | None:
    """
    Detecta automáticamente el proveedor a partir del CUIT o nombre
    extraído de la factura. Retorna config completa o None.
    """
    if cuit:
        prov = buscar_proveedor_por_cuit(cuit)
        if prov:
            log.info(f"Proveedor detectado por CUIT {cuit}: {prov['nombre']} (#{prov['numero']})")
            return prov

    if nombre:
        prov = buscar_proveedor_por_nombre(nombre)
        if prov:
            log.info(f"Proveedor detectado por nombre '{nombre}': {prov['nombre']} (#{prov['numero']})")
            return prov

    return None


# ── Auto-detección por texto libre (nombre archivo, contenido PDF/Excel) ──

@lru_cache(maxsize=1)
def _construir_indice_busqueda():
    """
    Construye un índice keyword → proveedor_numero desde:
    1. nombre_fantasia de proveedores (separado por - y /)
    2. denominacion de proveedores (razón social)
    3. descripcion de marcas → proveedor principal (de tabla articulo)

    Retorna dict {keyword_upper: proveedor_numero}
    Prioridad: keywords más específicos ganan.
    """
    import re
    indice = {}  # keyword → (proveedor_numero, score)

    try:
        with _get_conn() as conn:
            cursor = conn.cursor()

            # 1) nombre_fantasia y denominacion de proveedores activos con artículos
            cursor.execute("""
                SELECT p.numero, RTRIM(p.denominacion) as denominacion,
                       RTRIM(ISNULL(p.nombre_fantasia,'')) as fantasia,
                       ISNULL(ac.cant, 0) as cant
                FROM msgestionC.dbo.proveedores p
                LEFT JOIN (
                    SELECT proveedor, COUNT(*) as cant
                    FROM msgestion01art.dbo.articulo WHERE estado = 'V'
                    GROUP BY proveedor
                ) ac ON ac.proveedor = p.numero
                WHERE p.motivo_baja = 'A' AND ISNULL(ac.cant, 0) > 0
            """)
            for row in cursor.fetchall():
                num = row.numero
                cant = row.cant or 0

                def _set_indice(key, num, cant):
                    """Solo guarda si no existe o si tiene más artículos (proveedor más relevante)."""
                    existing = indice.get(key)
                    if not existing or cant > existing[1]:
                        indice[key] = (num, cant)

                # Razón social como keyword
                denom = (row.denominacion or "").strip().upper()
                if len(denom) >= 3:
                    _set_indice(denom, num, cant)
                    # También primera palabra si es larga (ej: "GRIMOLDI" de "GRIMOLDI S.A.")
                    primera = denom.split()[0] if denom.split() else ""
                    if len(primera) >= 4 and primera not in ("S.A.", "SRL", "S.R.L", "S.A.I.C."):
                        _set_indice(primera, num, cant)

                # nombre_fantasia: separar por " - " y "/" para marcas múltiples
                fantasia = (row.fantasia or "").strip()
                if fantasia and len(fantasia) >= 3:
                    # Filtrar los que son contactos, no marcas
                    if not any(x in fantasia.lower() for x in ["contacto", "celu", "ctas ctes",
                                                                 "mesa de entrada", "andrea",
                                                                 "maria", "marta", "julian",
                                                                 "adriana"]):
                        for parte in re.split(r'\s*[-/]\s*', fantasia):
                            parte = parte.strip().upper()
                            if len(parte) >= 3:
                                _set_indice(parte, num, cant)

            # 2) Nombres de marcas → proveedor principal
            cursor.execute("""
                SELECT a.marca, RTRIM(m.descripcion) as marca_nombre, a.proveedor,
                       COUNT(*) as cant
                FROM msgestion01art.dbo.articulo a
                JOIN msgestion01art.dbo.marcas m ON a.marca = m.codigo
                WHERE a.estado = 'V'
                GROUP BY a.marca, m.descripcion, a.proveedor
                HAVING COUNT(*) >= 10
                ORDER BY cant DESC
            """)
            for row in cursor.fetchall():
                marca_nombre = (row.marca_nombre or "").strip().upper()
                if len(marca_nombre) >= 3:
                    key = marca_nombre
                    existing = indice.get(key)
                    # Solo guardar si no existe o tiene más artículos
                    if not existing or row.cant > existing[1]:
                        indice[key] = (row.proveedor, row.cant)

    except Exception as e:
        log.error(f"Error construyendo índice de búsqueda: {e}")

    return indice


def detectar_proveedor_por_texto(texto: str) -> dict | None:
    """
    Detecta proveedor a partir de texto libre (nombre de archivo, contenido PDF/Excel).
    Busca keywords del índice dentro del texto.

    Retorna dict con config completa del proveedor o None.
    """
    if not texto or len(texto) < 3:
        return None

    texto_upper = texto.upper()
    indice = _construir_indice_busqueda()

    # Buscar el keyword más largo que matchea (más específico = mejor)
    mejor_match = None
    mejor_score = 0

    for keyword, (prov_num, cant) in indice.items():
        if keyword in texto_upper:
            # Score = largo del keyword × cantidad de artículos (prefiere matches largos y proveedores grandes)
            score = len(keyword) * (1 + cant / 1000)
            if score > mejor_score:
                mejor_score = score
                mejor_match = prov_num

    if mejor_match:
        # Obtener config completa
        provs = listar_proveedores_activos()
        prov_base = provs.get(mejor_match)
        if prov_base:
            prov = dict(prov_base)
            pricing = obtener_pricing_proveedor(mejor_match)
            prov.update(pricing)
            log.info(f"Proveedor detectado por texto: {prov['nombre']} (#{mejor_match})")
            return prov

    return None


def listar_proveedores_con_fantasia():
    """
    Lista todos los proveedores activos con artículos, incluyendo nombre_fantasia y marcas.
    Para mostrar en selectbox con nombre amigable.
    Retorna dict {numero: {nombre, fantasia, marcas_texto, cant_articulos, ...}}
    """
    sql = """
        SELECT p.numero, RTRIM(p.denominacion) as nombre,
               RTRIM(ISNULL(p.nombre_fantasia,'')) as fantasia,
               RTRIM(ISNULL(p.cuit,'')) as cuit,
               ISNULL(p.condicion_iva,'I') as condicion_iva,
               ISNULL(p.zona,0) as zona,
               ISNULL(ac.cant, 0) as cant_articulos
        FROM msgestionC.dbo.proveedores p
        LEFT JOIN (
            SELECT proveedor, COUNT(*) as cant
            FROM msgestion01art.dbo.articulo
            WHERE estado = 'V'
            GROUP BY proveedor
        ) ac ON ac.proveedor = p.numero
        WHERE p.motivo_baja = 'A' AND ISNULL(ac.cant, 0) >= 5
        ORDER BY p.denominacion
    """
    proveedores = {}
    try:
        with _get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for row in cursor.fetchall():
                fantasia = (row.fantasia or "").strip()
                nombre = (row.nombre or "").strip()
                # Armar label amigable: "MARCA (Razón Social)" o solo "Razón Social"
                if fantasia and len(fantasia) >= 3 and not any(
                    x in fantasia.lower() for x in ["contacto", "celu", "ctas ctes",
                                                     "mesa de entrada"]
                ):
                    label = f"{fantasia} ({nombre})"
                else:
                    label = nombre

                proveedores[row.numero] = {
                    "numero": row.numero,
                    "nombre": nombre,
                    "fantasia": fantasia,
                    "label": label,
                    "cuit": (row.cuit or "").strip().replace("-", ""),
                    "condicion_iva": (row.condicion_iva or "I").strip(),
                    "zona": row.zona or 0,
                    "cant_articulos": row.cant_articulos or 0,
                }
    except Exception as e:
        log.error(f"Error listando proveedores con fantasia: {e}")
    return proveedores


# ── CLI para testing ──
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        busqueda = sys.argv[1]
        if busqueda.isdigit() and len(busqueda) >= 10:
            prov = buscar_proveedor_por_cuit(busqueda)
        else:
            prov = buscar_proveedor_por_nombre(busqueda)

        if prov:
            print(f"\nProveedor encontrado:")
            for k, v in prov.items():
                print(f"  {k}: {v}")
            marcas = obtener_marcas_proveedor(prov["numero"])
            if marcas:
                print(f"\nMarcas ({len(marcas)}):")
                for m in marcas:
                    print(f"  Marca {m['marca']}: {m['cant']} arts — ej: {m['ejemplo']}")
        else:
            print(f"No encontrado: {busqueda}")
    else:
        provs = listar_proveedores_activos()
        print(f"\nProveedores activos: {len(provs)}")
        for num, p in list(provs.items())[:20]:
            print(f"  {num:>5} | {p['nombre']:<40} | CUIT: {p['cuit']:<15} | Arts: {p['cant_articulos']}")
