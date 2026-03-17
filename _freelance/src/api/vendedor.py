# -*- coding: utf-8 -*-
"""
API del Panel del Vendedor Freelance.
Cada vendedor ve SU dashboard, SU catalogo, SUS ventas.

Endpoints:
  GET  /api/v1/vendedor/{cod}/dashboard   → KPIs personales
  GET  /api/v1/vendedor/{cod}/ventas      → Mis ventas del periodo
  GET  /api/v1/vendedor/{cod}/ranking     → Mi posicion en el ranking
  GET  /api/v1/vendedor/{cod}/catalogo    → Productos para compartir
  GET  /api/v1/vendedor/{cod}/clientes    → Mis clientes (CRM)
  GET  /api/v1/vendedor/{cod}/proyeccion  → Proyeccion vs tope monotributo
  POST /api/v1/vendedor/{cod}/compartir   → Marcar contenido como compartido
"""
import calendar
from fastapi import APIRouter, HTTPException
from datetime import datetime, date
from db import query, execute
from .topes_mono import TOPES_MONO

router = APIRouter()


def _get_vendedor(cod: str) -> dict:
    """Obtiene datos del vendedor freelance por codigo de atribucion (V569)."""
    rows = query(
        "SELECT vf.*, v.descripcion AS nombre "
        "FROM vendedor_freelance vf "
        "JOIN msgestionC.dbo.viajantes v ON v.codigo = vf.viajante_cod "
        "WHERE vf.codigo_atrib = ? AND vf.activo = 1",
        'omicronvt',
        (cod,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    return rows[0]


@router.get("/{cod}/dashboard")
async def dashboard(cod: str, meses: int = 1):
    """
    Dashboard personal del vendedor.
    Retorna KPIs: ventas hoy, semana, mes, ranking, fee acumulado.
    """
    vend = _get_vendedor(cod)
    hoy = date.today()
    primer_dia_mes = date(hoy.year, hoy.month, 1)

    sql_ventas = """
        SELECT
            SUM(total_item) AS venta_total,
            SUM(precio_costo * cantidad) AS costo_total,
            SUM(cantidad) AS pares,
            COUNT(DISTINCT CASE WHEN codigo=1 THEN
                CAST(sucursal AS VARCHAR) + '-' + CAST(numero AS VARCHAR)
            END) AS tickets,
            SUM(CASE WHEN CAST(fecha AS DATE) = ? THEN total_item ELSE 0 END) AS venta_hoy,
            SUM(CASE WHEN CAST(fecha AS DATE) = ? THEN cantidad ELSE 0 END) AS pares_hoy,
            SUM(CASE WHEN fecha >= DATEADD(day, -7, ?) THEN total_item ELSE 0 END) AS venta_semana
        FROM omicronvt.dbo.ventas1_vendedor
        WHERE viajante = ?
          AND codigo NOT IN (7, 36)
          AND fecha >= ?
          AND fecha <= ?
    """

    ventas = query(sql_ventas, 'omicronvt', (
        str(hoy), str(hoy), str(hoy),
        vend['viajante_cod'],
        str(primer_dia_mes), str(hoy),
    ))
    v = ventas[0] if ventas else {}

    venta_total = float(v.get('venta_total') or 0)
    costo_total = float(v.get('costo_total') or 0)
    pares = int(v.get('pares') or 0)
    tickets = int(v.get('tickets') or 0)

    fee_pct = float(vend.get('fee_pct_std') or 0.05)
    fee_estimado = venta_total * fee_pct

    margen_pct = ((venta_total - costo_total) / venta_total * 100) if venta_total > 0 else 0

    sql_ranking = """
        SELECT viajante, SUM(total_item) AS venta
        FROM omicronvt.dbo.ventas1_vendedor
        WHERE fecha >= ? AND fecha <= ?
          AND codigo NOT IN (7, 36)
        GROUP BY viajante
        ORDER BY venta DESC
    """
    ranking_rows = query(sql_ranking, 'omicronvt', (str(primer_dia_mes), str(hoy)))
    mi_posicion = 0
    total_vendedores = len(ranking_rows)
    for i, r in enumerate(ranking_rows, 1):
        if r['viajante'] == vend['viajante_cod']:
            mi_posicion = i
            break

    return {
        "vendedor": {
            "codigo": cod,
            "nombre": vend.get('nombre', ''),
            "instagram": vend.get('instagram', ''),
            "categoria_mono": vend.get('categoria_mono', ''),
        },
        "periodo": {
            "desde": str(primer_dia_mes),
            "hasta": str(hoy),
        },
        "kpis": {
            "venta_hoy": float(v.get('venta_hoy') or 0),
            "pares_hoy": int(v.get('pares_hoy') or 0),
            "venta_semana": float(v.get('venta_semana') or 0),
            "venta_mes": venta_total,
            "pares_mes": pares,
            "tickets_mes": tickets,
            "margen_pct": round(margen_pct, 1),
            "pares_por_ticket": round(pares / tickets, 1) if tickets > 0 else 0,
        },
        "fee": {
            "pct_base": fee_pct,
            "estimado_mes": round(fee_estimado, 0),
            "cuota_mono": float(vend.get('cuota_mono') or 0),
            "canon": float(vend.get('canon_mensual') or 0),
            "neto_estimado": round(
                fee_estimado - float(vend.get('cuota_mono') or 0) - float(vend.get('canon_mensual') or 0),
                0
            ),
        },
        "ranking": {
            "posicion": mi_posicion,
            "total": total_vendedores,
            "percentil": round((1 - mi_posicion / total_vendedores) * 100) if total_vendedores > 0 else 0,
        },
    }


@router.get("/{cod}/ventas")
async def ventas(cod: str, dias: int = 30):
    """Detalle de ventas del vendedor en los ultimos N dias."""
    vend = _get_vendedor(cod)

    sql = """
        SELECT
            CAST(fecha AS DATE) AS dia,
            SUM(total_item) AS venta,
            SUM(cantidad) AS pares,
            COUNT(DISTINCT CASE WHEN codigo=1 THEN
                CAST(sucursal AS VARCHAR) + '-' + CAST(numero AS VARCHAR)
            END) AS tickets
        FROM omicronvt.dbo.ventas1_vendedor
        WHERE viajante = ?
          AND codigo NOT IN (7, 36)
          AND fecha >= DATEADD(day, -?, GETDATE())
        GROUP BY CAST(fecha AS DATE)
        ORDER BY dia DESC
    """

    rows = query(sql, 'omicronvt', (vend['viajante_cod'], dias))
    fee_pct = float(vend.get('fee_pct_std') or 0.05)

    return {
        "vendedor": cod,
        "dias": dias,
        "detalle": [
            {
                "dia": str(r['dia']),
                "venta": float(r['venta'] or 0),
                "pares": int(r['pares'] or 0),
                "tickets": int(r['tickets'] or 0),
                "fee_estimado": round(float(r['venta'] or 0) * fee_pct, 0),
            }
            for r in rows
        ]
    }


@router.get("/{cod}/ranking")
async def ranking(cod: str):
    """Ranking completo de vendedores del mes actual (gamificacion)."""
    hoy = date.today()
    primer_dia = date(hoy.year, hoy.month, 1)

    sql = """
        SELECT
            v1.viajante,
            vj.descripcion AS nombre,
            SUM(v1.total_item) AS venta,
            SUM(v1.cantidad) AS pares,
            COUNT(DISTINCT CASE WHEN v1.codigo=1 THEN
                CAST(v1.sucursal AS VARCHAR) + '-' + CAST(v1.numero AS VARCHAR)
            END) AS tickets
        FROM omicronvt.dbo.ventas1_vendedor v1
        LEFT JOIN msgestionC.dbo.viajantes vj ON vj.codigo = v1.viajante
        WHERE v1.codigo NOT IN (7, 36)
          AND v1.fecha >= ? AND v1.fecha <= ?
        GROUP BY v1.viajante, vj.descripcion
        HAVING SUM(v1.total_item) > 100000
        ORDER BY venta DESC
    """

    rows = query(sql, 'omicronvt', (str(primer_dia), str(hoy)))

    vend = _get_vendedor(cod)
    mi_cod = vend['viajante_cod']

    return {
        "periodo": "%s-%02d" % (hoy.year, hoy.month),
        "ranking": [
            {
                "posicion": i,
                "viajante": r['viajante'],
                "nombre": (r['nombre'] or '').strip(),
                "venta": float(r['venta'] or 0),
                "pares": int(r['pares'] or 0),
                "tickets": int(r['tickets'] or 0),
                "es_yo": r['viajante'] == mi_cod,
            }
            for i, r in enumerate(rows, 1)
        ]
    }


@router.get("/{cod}/catalogo")
async def catalogo(cod: str, solo_nuevos: bool = False):
    """
    Catalogo de productos disponibles para compartir.
    Incluye contenido pre-generado para redes sociales.
    """
    vend = _get_vendedor(cod)

    sql = """
        SELECT cc.id, cc.sku_base, cc.titulo_corto, cc.descripcion_redes,
               cc.hashtags, cc.categoria_fee, cc.foto_principal,
               m.descripcion AS marca,
               (SELECT COUNT(*) FROM msgestion01art.dbo.articulo a2
                WHERE LEFT(a2.descripcion_1, LEN(cc.sku_base)) = cc.sku_base
                  AND a2.stock > 0) AS talles_con_stock,
               (SELECT MIN(a3.precio_1) FROM msgestion01art.dbo.articulo a3
                WHERE LEFT(a3.descripcion_1, LEN(cc.sku_base)) = cc.sku_base
                  AND a3.precio_1 > 0) AS precio_min,
               (SELECT MAX(a3.precio_1) FROM msgestion01art.dbo.articulo a3
                WHERE LEFT(a3.descripcion_1, LEN(cc.sku_base)) = cc.sku_base
                  AND a3.precio_1 > 0) AS precio_max
        FROM omicronvt.dbo.catalogo_comercial cc
        LEFT JOIN msgestionC.dbo.marcas m ON m.codigo = cc.marca_cod
        WHERE cc.activo = 1
        ORDER BY cc.fecha_modif DESC
    """
    productos = query(sql, 'omicronvt')

    sql_contenido = """
        SELECT sku_base, canal, estado, contenido_texto, link_atribucion
        FROM omicronvt.dbo.contenido_generado
        WHERE vendedor_id = ? AND estado IN ('LISTO', 'COMPARTIDO')
    """
    contenido = query(sql_contenido, 'omicronvt', (vend['id'],))

    if solo_nuevos:
        skus_compartidos = {c['sku_base'] for c in contenido if c.get('estado') == 'COMPARTIDO'}
        productos = [p for p in productos if p['sku_base'] not in skus_compartidos]
    contenido_map = {}
    for c in contenido:
        key = c['sku_base']
        if key not in contenido_map:
            contenido_map[key] = []
        contenido_map[key].append(c)

    fee_std = float(vend.get('fee_pct_std') or 0.05)
    fee_prem = float(vend.get('fee_pct_premium') or 0.08)

    resultado = []
    for p in productos:
        sku = p['sku_base']
        precio = float(p.get('precio_min') or 0)
        cat_fee = p.get('categoria_fee', 'STD')
        fee_pct = fee_prem if cat_fee == 'PREMIUM' else fee_std
        fee_est = round(precio * fee_pct, 0) if precio > 0 else 0

        resultado.append({
            "sku_base": sku,
            "titulo": p.get('titulo_corto', sku),
            "marca": (p.get('marca') or '').strip(),
            "descripcion_redes": p.get('descripcion_redes', ''),
            "hashtags": p.get('hashtags', ''),
            "categoria_fee": cat_fee,
            "fee_pct": fee_pct,
            "fee_estimado_por_par": fee_est,
            "precio_rango": {
                "min": float(p.get('precio_min') or 0),
                "max": float(p.get('precio_max') or 0),
            },
            "talles_con_stock": int(p.get('talles_con_stock') or 0),
            "foto": p.get('foto_principal', ''),
            "contenido_listo": contenido_map.get(sku, []),
            "link_compartir": "%s/%s?v=%s" % (
                "https://h4calzados.com/p", sku, cod
            ),
        })

    return {
        "vendedor": cod,
        "total_productos": len(resultado),
        "productos": resultado,
    }


@router.get("/{cod}/clientes")
async def clientes(cod: str):
    """CRM minimo: clientes del vendedor."""
    vend = _get_vendedor(cod)

    rows = query(
        "SELECT * FROM omicronvt.dbo.cliente_vendedor "
        "WHERE vendedor_id = ? ORDER BY ultima_compra DESC",
        'omicronvt',
        (vend['id'],),
    )

    return {
        "vendedor": cod,
        "total_clientes": len(rows),
        "clientes": [
            {
                "id": r['id'],
                "nombre": r.get('cliente_nombre', ''),
                "tel": r.get('cliente_tel', ''),
                "ig": r.get('cliente_ig', ''),
                "primera_compra": str(r.get('primera_compra', '')),
                "ultima_compra": str(r.get('ultima_compra', '')),
                "total_compras": int(r.get('total_compras') or 0),
                "total_monto": float(r.get('total_monto') or 0),
            }
            for r in rows
        ]
    }


@router.get("/{cod}/proyeccion")
async def proyeccion_monotributo(cod: str):
    """
    Proyeccion de facturacion del vendedor vs tope de su categoria de monotributo.
    Alerta si esta por pasarse.
    """
    vend = _get_vendedor(cod)
    hoy = date.today()

    primer_dia_anio = date(hoy.year, 1, 1)

    rows = query(
        "SELECT SUM(total_item) AS venta_anual "
        "FROM omicronvt.dbo.ventas1_vendedor "
        "WHERE viajante = ? AND fecha >= ?",
        'omicronvt',
        (vend['viajante_cod'], str(primer_dia_anio)),
    )
    venta_anual = float(rows[0]['venta_anual'] or 0) if rows else 0

    fee_pct = float(vend.get('fee_pct_std') or 0.05)
    facturacion_anual_est = venta_anual * fee_pct

    cat = vend.get('categoria_mono', 'D')
    tope = TOPES_MONO.get(cat, 25200000)

    dias_transcurridos = (hoy - primer_dia_anio).days + 1
    dias_anio = 366 if calendar.isleap(hoy.year) else 365
    proyeccion_anual = (facturacion_anual_est / dias_transcurridos * dias_anio) if dias_transcurridos > 0 else 0

    pct_usado = facturacion_anual_est / tope * 100 if tope > 0 else 0
    pct_proyectado = proyeccion_anual / tope * 100 if tope > 0 else 0

    if pct_proyectado > 90:
        alerta = "PELIGRO: proyeccion supera 90%% del tope. Considerar subir de categoria."
    elif pct_proyectado > 75:
        alerta = "ATENCION: proyeccion en 75-90%% del tope. Monitorear."
    else:
        alerta = None

    return {
        "vendedor": cod,
        "categoria_mono": cat,
        "tope_anual": tope,
        "facturado_acumulado": round(facturacion_anual_est, 0),
        "pct_usado": round(pct_usado, 1),
        "proyeccion_anual": round(proyeccion_anual, 0),
        "pct_proyectado": round(pct_proyectado, 1),
        "alerta": alerta,
        "meses_restantes": 12 - hoy.month,
        "disponible": round(tope - facturacion_anual_est, 0),
    }


@router.post("/{cod}/compartir")
async def marcar_compartido(cod: str, contenido_id: int):
    """
    Marca un contenido generado como compartido por el vendedor.
    Registra la fecha de compartido para tracking de actividad.
    """
    vend = _get_vendedor(cod)

    rows = query(
        "SELECT id, estado FROM contenido_generado "
        "WHERE id = ? AND vendedor_id = ?",
        'omicronvt',
        (contenido_id, vend['id']),
    )
    if not rows:
        raise HTTPException(404, "Contenido no encontrado para este vendedor")

    execute(
        "UPDATE omicronvt.dbo.contenido_generado "
        "SET estado = 'COMPARTIDO', fecha_compartido = GETDATE() "
        "WHERE id = ?",
        'omicronvt',
        (contenido_id,),
    )

    return {
        "contenido_id": contenido_id,
        "vendedor": cod,
        "estado": "COMPARTIDO",
    }
