# -*- coding: utf-8 -*-
"""
API de Liquidación mensual de vendedores freelance.

Endpoints:
  POST /api/v1/liquidacion/generar        → Genera liquidaciones del mes
  GET  /api/v1/liquidacion/resumen        → Resumen de todas las liquidaciones
  GET  /api/v1/liquidacion/{vendedor_cod} → Liquidacion detallada de un vendedor
  POST /api/v1/liquidacion/aprobar/{id}   → Aprobar liquidacion
"""
from fastapi import APIRouter, HTTPException
from datetime import date
from db import query_omicronvt, execute, get_db

router = APIRouter()


@router.post("/generar")
async def generar_liquidaciones(anio: int = None, mes: int = None):
    """
    Genera (o actualiza) las liquidaciones de TODOS los vendedores freelance
    para un periodo dado. Si ya existe, la recalcula.
    """
    hoy = date.today()
    a = anio or hoy.year
    m = mes or hoy.month

    # Obtener todos los vendedores activos
    vendedores = query_omicronvt(
        "SELECT * FROM vendedor_freelance WHERE activo = 1"
    )
    if not vendedores:
        return {"mensaje": "No hay vendedores freelance activos", "generadas": 0}

    generadas = 0
    resultados = []

    for vend in vendedores:
        vid = vend['id']

        # Sumar atribuciones del periodo
        sql_atrib = """
            SELECT
                COUNT(*) AS operaciones,
                ISNULL(SUM(monto_producto), 0) AS total_producto,
                ISNULL(SUM(cant_pares), 0) AS total_pares,
                ISNULL(SUM(fee_monto), 0) AS total_fee,
                ISNULL(SUM(fee_monto) - SUM(monto_producto * fee_pct_base), 0) AS total_bonus
            FROM omicronvt.dbo.venta_atribucion
            WHERE vendedor_id = %d
              AND YEAR(fecha) = %d AND MONTH(fecha) = %d
        """ % (vid, a, m)
        atrib = query_omicronvt(sql_atrib)
        at = atrib[0] if atrib else {}

        total_fee = float(at.get('total_fee') or 0)
        total_bonus = float(at.get('total_bonus') or 0)
        total_fee_base = total_fee - total_bonus
        canon = float(vend.get('canon_mensual') or 0)
        cuota = float(vend.get('cuota_mono') or 0)
        neto = total_fee - canon - cuota

        # Upsert liquidacion
        existe = query_omicronvt(
            "SELECT id FROM liquidacion_vendedor "
            "WHERE vendedor_id = %d AND periodo_anio = %d AND periodo_mes = %d"
            % (vid, a, m)
        )

        if existe:
            sql_update = """
                UPDATE omicronvt.dbo.liquidacion_vendedor SET
                    ventas_producto = %.2f,
                    cant_operaciones = %d,
                    cant_pares = %d,
                    total_fee_base = %.2f,
                    total_bonus = %.2f,
                    total_fee = %.2f,
                    canon_espacio = %.2f,
                    cuota_mono = %.2f,
                    neto_estimado = %.2f,
                    estado = CASE WHEN estado IN ('BORR') THEN 'BORR' ELSE estado END
                WHERE vendedor_id = %d AND periodo_anio = %d AND periodo_mes = %d
            """ % (
                float(at.get('total_producto') or 0),
                int(at.get('operaciones') or 0),
                int(at.get('total_pares') or 0),
                total_fee_base, total_bonus, total_fee,
                canon, cuota, neto,
                vid, a, m
            )
            execute(sql_update, 'omicronvt')
        else:
            sql_insert = """
                INSERT INTO omicronvt.dbo.liquidacion_vendedor (
                    vendedor_id, periodo_anio, periodo_mes,
                    ventas_producto, cant_operaciones, cant_pares,
                    total_fee_base, total_bonus, total_fee,
                    canon_espacio, cuota_mono, neto_estimado,
                    estado
                ) VALUES (
                    %d, %d, %d,
                    %.2f, %d, %d,
                    %.2f, %.2f, %.2f,
                    %.2f, %.2f, %.2f,
                    'BORR'
                )
            """ % (
                vid, a, m,
                float(at.get('total_producto') or 0),
                int(at.get('operaciones') or 0),
                int(at.get('total_pares') or 0),
                total_fee_base, total_bonus, total_fee,
                canon, cuota, neto,
            )
            execute(sql_insert, 'omicronvt')

        generadas += 1
        resultados.append({
            "vendedor": vend.get('codigo_atrib', ''),
            "nombre": vend.get('razon_social', ''),
            "ventas_producto": float(at.get('total_producto') or 0),
            "total_fee": round(total_fee, 0),
            "neto": round(neto, 0),
        })

    return {
        "periodo": "%d-%02d" % (a, m),
        "generadas": generadas,
        "detalle": resultados,
    }


@router.get("/resumen")
async def resumen_liquidaciones(anio: int = None, mes: int = None):
    """Resumen de todas las liquidaciones de un periodo."""
    hoy = date.today()
    a = anio or hoy.year
    m = mes or hoy.month

    sql = """
        SELECT l.*, vf.codigo_atrib,
               vj.descripcion AS nombre_vendedor
        FROM omicronvt.dbo.liquidacion_vendedor l
        JOIN omicronvt.dbo.vendedor_freelance vf ON vf.id = l.vendedor_id
        LEFT JOIN msgestionC.dbo.viajantes vj ON vj.codigo = vf.viajante_cod
        WHERE l.periodo_anio = %d AND l.periodo_mes = %d
        ORDER BY l.total_fee DESC
    """ % (a, m)

    liqs = query_omicronvt(sql)

    totales = {
        "ventas_producto": sum(float(r.get('ventas_producto') or 0) for r in liqs),
        "total_fee": sum(float(r.get('total_fee') or 0) for r in liqs),
        "total_neto": sum(float(r.get('neto_estimado') or 0) for r in liqs),
        "vendedores": len(liqs),
    }

    return {
        "periodo": "%d-%02d" % (a, m),
        "totales": totales,
        "liquidaciones": [
            {
                "id": r['id'],
                "vendedor": r.get('codigo_atrib', ''),
                "nombre": (r.get('nombre_vendedor') or '').strip(),
                "operaciones": int(r.get('cant_operaciones') or 0),
                "pares": int(r.get('cant_pares') or 0),
                "ventas_producto": float(r.get('ventas_producto') or 0),
                "fee_base": float(r.get('total_fee_base') or 0),
                "bonus": float(r.get('total_bonus') or 0),
                "fee_total": float(r.get('total_fee') or 0),
                "canon": float(r.get('canon_espacio') or 0),
                "mono": float(r.get('cuota_mono') or 0),
                "neto": float(r.get('neto_estimado') or 0),
                "estado": r.get('estado', 'BORR'),
            }
            for r in liqs
        ]
    }


@router.get("/{cod}")
async def liquidacion_vendedor(cod: str, anio: int = None, mes: int = None):
    """Liquidacion detallada de un vendedor con cada operacion."""
    hoy = date.today()
    a = anio or hoy.year
    m = mes or hoy.month

    # Datos del vendedor
    vrows = query_omicronvt(
        "SELECT vf.*, vj.descripcion AS nombre "
        "FROM vendedor_freelance vf "
        "JOIN msgestionC.dbo.viajantes vj ON vj.codigo = vf.viajante_cod "
        "WHERE vf.codigo_atrib = '%s'" % cod
    )
    if not vrows:
        raise HTTPException(404, "Vendedor no encontrado")
    vend = vrows[0]

    # Liquidacion del periodo
    liq = query_omicronvt(
        "SELECT * FROM liquidacion_vendedor "
        "WHERE vendedor_id = %d AND periodo_anio = %d AND periodo_mes = %d"
        % (vend['id'], a, m)
    )
    liq_data = liq[0] if liq else None

    # Detalle de operaciones
    ops = query_omicronvt(
        "SELECT * FROM venta_atribucion "
        "WHERE vendedor_id = %d AND YEAR(fecha) = %d AND MONTH(fecha) = %d "
        "ORDER BY fecha" % (vend['id'], a, m)
    )

    return {
        "vendedor": {
            "codigo": cod,
            "nombre": (vend.get('nombre') or '').strip(),
            "cuit": vend.get('cuit', ''),
            "categoria_mono": vend.get('categoria_mono', ''),
        },
        "periodo": "%d-%02d" % (a, m),
        "liquidacion": {
            "ventas_producto": float(liq_data.get('ventas_producto') or 0) if liq_data else 0,
            "operaciones": int(liq_data.get('cant_operaciones') or 0) if liq_data else 0,
            "fee_base": float(liq_data.get('total_fee_base') or 0) if liq_data else 0,
            "bonus": float(liq_data.get('total_bonus') or 0) if liq_data else 0,
            "fee_total": float(liq_data.get('total_fee') or 0) if liq_data else 0,
            "canon": float(liq_data.get('canon_espacio') or 0) if liq_data else 0,
            "cuota_mono": float(liq_data.get('cuota_mono') or 0) if liq_data else 0,
            "neto": float(liq_data.get('neto_estimado') or 0) if liq_data else 0,
            "estado": liq_data.get('estado', 'SIN DATOS') if liq_data else 'SIN DATOS',
        } if liq_data else None,
        "operaciones": [
            {
                "fecha": str(r.get('fecha', '')),
                "hora": r.get('hora_venta', ''),
                "canal": r.get('canal_origen', ''),
                "monto_producto": float(r.get('monto_producto') or 0),
                "pares": int(r.get('cant_pares') or 0),
                "fee_pct": float(r.get('fee_pct_total') or 0),
                "fee_monto": float(r.get('fee_monto') or 0),
                "estado_factura": r.get('estado_factura', ''),
            }
            for r in ops
        ],
    }


@router.post("/aprobar/{liq_id}")
async def aprobar_liquidacion(liq_id: int):
    """Gerencia aprueba una liquidacion (cambia estado de BORR a APROBADA)."""
    count = execute(
        "UPDATE omicronvt.dbo.liquidacion_vendedor "
        "SET estado = 'APROBADA', fecha_aprobacion = GETDATE() "
        "WHERE id = %d AND estado = 'BORR'" % liq_id,
        'omicronvt'
    )
    if count == 0:
        raise HTTPException(400, "Liquidacion no encontrada o ya aprobada")
    return {"id": liq_id, "estado": "APROBADA"}
