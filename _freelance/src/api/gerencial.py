# -*- coding: utf-8 -*-
"""
API del Dashboard Gerencial Freelance.
Vista ejecutiva para Fernando: como rinde la red de vendedores.

Endpoints:
  GET /api/v1/gerencial/dashboard          → KPIs globales de la red
  GET /api/v1/gerencial/ahorro             → Comparacion vs modelo empleado
  GET /api/v1/gerencial/vendedores         → Lista de vendedores con metricas
  GET /api/v1/gerencial/franjas            → Rendimiento por franja horaria
  POST /api/v1/gerencial/alta_vendedor     → Dar de alta un vendedor freelance
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date
from db import query, execute, execute_returning_id

router = APIRouter()


class AltaVendedorIn(BaseModel):
    viajante_cod: int
    cuit: Optional[str] = None
    razon_social: Optional[str] = None
    categoria_mono: str = "D"
    cuota_mono: float = 72414
    fee_pct_std: float = 0.05
    fee_pct_premium: float = 0.08
    instagram: Optional[str] = None
    whatsapp: Optional[str] = None
    canon_mensual: float = 0


TOPES_MONO = {
    'A': 10300000, 'B': 15300000, 'C': 20200000, 'D': 25200000,
    'E': 29600000, 'F': 37000000, 'G': 44400000, 'H': 55300000,
    'I': 66400000, 'J': 82100000, 'K': 108400000,
}


@router.get("/dashboard")
async def dashboard(meses: int = 1):
    """KPIs globales de la red de vendedores freelance."""
    hoy = date.today()
    primer_dia = date(hoy.year, hoy.month, 1)

    vendedores = query(
        "SELECT COUNT(*) AS total FROM vendedor_freelance WHERE activo = 1",
        'omicronvt',
    )
    total_vendedores = int(vendedores[0]['total']) if vendedores else 0

    sql_ventas = """
        SELECT
            ISNULL(SUM(va.monto_producto), 0) AS total_producto,
            ISNULL(SUM(va.fee_monto), 0) AS total_fee,
            COUNT(*) AS operaciones,
            ISNULL(SUM(va.cant_pares), 0) AS pares,
            COUNT(DISTINCT va.vendedor_id) AS vendedores_activos
        FROM omicronvt.dbo.venta_atribucion va
        WHERE va.fecha >= ?
    """
    ventas = query(sql_ventas, 'omicronvt', (str(primer_dia),))
    v = ventas[0] if ventas else {}

    sql_canales = """
        SELECT canal_origen, COUNT(*) AS ops,
               SUM(monto_producto) AS monto, SUM(fee_monto) AS fee
        FROM omicronvt.dbo.venta_atribucion
        WHERE fecha >= ?
        GROUP BY canal_origen
        ORDER BY monto DESC
    """
    canales = query(sql_canales, 'omicronvt', (str(primer_dia),))

    sql_alertas = """
        SELECT vf.codigo_atrib, vf.categoria_mono,
               vj.descripcion AS nombre,
               SUM(va.fee_monto) AS facturado_anual
        FROM omicronvt.dbo.vendedor_freelance vf
        JOIN msgestionC.dbo.viajantes vj ON vj.codigo = vf.viajante_cod
        LEFT JOIN omicronvt.dbo.venta_atribucion va
            ON va.vendedor_id = vf.id AND YEAR(va.fecha) = ?
        WHERE vf.activo = 1
        GROUP BY vf.codigo_atrib, vf.categoria_mono, vj.descripcion, vf.id
    """
    alertas_data = query(sql_alertas, 'omicronvt', (hoy.year,))
    alertas = []
    for row in alertas_data:
        cat = row.get('categoria_mono', 'D')
        tope = TOPES_MONO.get(cat, 25200000)
        facturado = float(row.get('facturado_anual') or 0)
        pct = facturado / tope * 100 if tope > 0 else 0
        if pct > 75:
            alertas.append({
                "vendedor": row.get('codigo_atrib', ''),
                "nombre": (row.get('nombre') or '').strip(),
                "categoria": cat,
                "pct_tope": round(pct, 1),
                "tipo": "PELIGRO" if pct > 90 else "ATENCION",
            })

    return {
        "periodo": str(primer_dia) + " a " + str(hoy),
        "red": {
            "vendedores_registrados": total_vendedores,
            "vendedores_con_ventas": int(v.get('vendedores_activos') or 0),
        },
        "ventas": {
            "total_producto": float(v.get('total_producto') or 0),
            "total_fee": float(v.get('total_fee') or 0),
            "operaciones": int(v.get('operaciones') or 0),
            "pares": int(v.get('pares') or 0),
        },
        "canales": [
            {
                "canal": c['canal_origen'],
                "operaciones": int(c.get('ops') or 0),
                "monto": float(c.get('monto') or 0),
                "fee": float(c.get('fee') or 0),
            }
            for c in canales
        ],
        "alertas_monotributo": alertas,
    }


@router.get("/ahorro")
async def ahorro_vs_empleado(anio: int = None, mes: int = None):
    """
    Compara el costo real del modelo freelance vs lo que hubiera costado
    con empleados de comercio CCT 130/75.
    """
    hoy = date.today()
    a = anio or hoy.year
    m = mes or hoy.month

    sql = """
        SELECT vf.id, vf.codigo_atrib, vf.viajante_cod, vf.cuota_mono, vf.canon_mensual,
               vj.descripcion AS nombre,
               (SELECT TOP 1 SUM(me.importe)
                FROM msgestionC.dbo.moviempl1 me
                WHERE me.numero_cuenta = vf.viajante_cod
                  AND me.codigo_movimiento IN (8,10,30,31)
                  AND YEAR(me.fecha_contable) = ? AND MONTH(me.fecha_contable) = ?
               ) AS sueldo_bruto,
               (SELECT ISNULL(SUM(va.fee_monto), 0)
                FROM omicronvt.dbo.venta_atribucion va
                WHERE va.vendedor_id = vf.id
                  AND YEAR(va.fecha) = ? AND MONTH(va.fecha) = ?
               ) AS fee_total
        FROM omicronvt.dbo.vendedor_freelance vf
        JOIN msgestionC.dbo.viajantes vj ON vj.codigo = vf.viajante_cod
        WHERE vf.activo = 1
    """

    vendedores = query(sql, 'omicronvt', (a, m, a, m))

    CONTRIBUCIONES = 0.265
    SAC = 0.0833
    VACACIONES = 0.04
    DEDUCCIONES = 0.24

    comparacion = []
    total_costo_empleado = 0
    total_costo_freelance = 0
    total_neto_empleado = 0
    total_neto_freelance = 0

    for v in vendedores:
        sueldo = float(v.get('sueldo_bruto') or 0)
        fee = float(v.get('fee_total') or 0)
        canon = float(v.get('canon_mensual') or 0)
        mono = float(v.get('cuota_mono') or 0)

        if sueldo > 0:
            contrib = sueldo * CONTRIBUCIONES
            sac = sueldo * SAC
            vac = sueldo * VACACIONES
            cargas_extras = (sac + vac) * CONTRIBUCIONES
            costo_empleado = sueldo + contrib + sac + vac + cargas_extras
            neto_empleado = sueldo * (1 - DEDUCCIONES)

            costo_freelance = fee
            neto_freelance = fee - mono

            ahorro = costo_empleado - costo_freelance
            mejora_vendedor = neto_freelance - neto_empleado

            total_costo_empleado += costo_empleado
            total_costo_freelance += costo_freelance
            total_neto_empleado += neto_empleado
            total_neto_freelance += neto_freelance

            comparacion.append({
                "vendedor": v.get('codigo_atrib', ''),
                "nombre": (v.get('nombre') or '').strip(),
                "sueldo_bruto": sueldo,
                "modelo_empleado": {
                    "costo_total": round(costo_empleado, 0),
                    "neto_vendedor": round(neto_empleado, 0),
                },
                "modelo_freelance": {
                    "fee_total": round(fee, 0),
                    "costo_h4": 0,
                    "mono": mono,
                    "neto_vendedor": round(neto_freelance, 0),
                },
                "ahorro_h4": round(costo_empleado, 0),
                "mejora_vendedor": round(mejora_vendedor, 0),
            })

    return {
        "periodo": "%d-%02d" % (a, m),
        "totales": {
            "costo_modelo_empleado": round(total_costo_empleado, 0),
            "costo_modelo_freelance": round(total_costo_freelance, 0),
            "ahorro_total": round(total_costo_empleado, 0),
            "ahorro_pct": 100.0,
            "mejora_neto_vendedores": round(total_neto_freelance - total_neto_empleado, 0),
        },
        "nota": "En el modelo freelance, H4 no paga sueldo ni cargas. "
                "El fee lo paga el cliente directamente al vendedor. "
                "El ahorro de H4 es el 100%% del costo laboral anterior.",
        "detalle": comparacion,
    }


@router.get("/vendedores")
async def lista_vendedores():
    """Lista de todos los vendedores freelance con metricas resumidas."""
    sql = """
        SELECT vf.*, vj.descripcion AS nombre
        FROM omicronvt.dbo.vendedor_freelance vf
        JOIN msgestionC.dbo.viajantes vj ON vj.codigo = vf.viajante_cod
        ORDER BY vf.activo DESC, vj.descripcion
    """
    return {"vendedores": query(sql, 'omicronvt')}


@router.post("/alta_vendedor")
async def alta_vendedor(data: AltaVendedorIn):
    """Dar de alta un nuevo vendedor freelance."""
    vj = query(
        "SELECT codigo, descripcion FROM viajantes WHERE codigo = ?",
        'msgestionC',
        (data.viajante_cod,),
    )
    if not vj:
        raise HTTPException(404, "Viajante no existe en el sistema")

    existe = query(
        "SELECT id FROM vendedor_freelance WHERE viajante_cod = ?",
        'omicronvt',
        (data.viajante_cod,),
    )
    if existe:
        raise HTTPException(400, "Viajante ya esta registrado como freelance")

    codigo_atrib = "V%d" % data.viajante_cod

    sql = """
        INSERT INTO omicronvt.dbo.vendedor_freelance (
            viajante_cod, cuit, razon_social, categoria_mono, cuota_mono,
            fee_pct_std, fee_pct_premium, instagram, whatsapp,
            codigo_atrib, canon_mensual, fecha_inicio
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
    """

    new_id = execute_returning_id(sql, 'omicronvt', (
        data.viajante_cod,
        data.cuit,
        data.razon_social,
        data.categoria_mono, data.cuota_mono,
        data.fee_pct_std, data.fee_pct_premium,
        data.instagram,
        data.whatsapp,
        codigo_atrib, data.canon_mensual,
    ))

    return {
        "id": new_id,
        "codigo_atrib": codigo_atrib,
        "nombre": (vj[0].get('descripcion') or '').strip(),
        "mensaje": "Vendedor freelance dado de alta exitosamente",
    }


@router.get("/franjas")
async def rendimiento_franjas(mes: int = None, anio: int = None):
    """Analisis de ventas por franja horaria (para ajustar incentivos)."""
    hoy = date.today()
    a = anio or hoy.year
    m = mes or hoy.month

    sql = """
        SELECT
            CASE
                WHEN hora_venta < '12:00' THEN 'Manana (9-12)'
                WHEN hora_venta < '16:00' THEN 'Mediodia (12-16)'
                WHEN hora_venta < '20:00' THEN 'Tarde (16-20)'
                ELSE 'Fuera de horario'
            END AS franja,
            COUNT(*) AS operaciones,
            SUM(monto_producto) AS monto_total,
            SUM(fee_monto) AS fee_total,
            AVG(monto_producto) AS ticket_promedio,
            COUNT(DISTINCT vendedor_id) AS vendedores
        FROM omicronvt.dbo.venta_atribucion
        WHERE YEAR(fecha) = ? AND MONTH(fecha) = ?
          AND hora_venta IS NOT NULL
        GROUP BY
            CASE
                WHEN hora_venta < '12:00' THEN 'Manana (9-12)'
                WHEN hora_venta < '16:00' THEN 'Mediodia (12-16)'
                WHEN hora_venta < '20:00' THEN 'Tarde (16-20)'
                ELSE 'Fuera de horario'
            END
        ORDER BY MIN(hora_venta)
    """

    return {
        "periodo": "%d-%02d" % (a, m),
        "franjas": query(sql, 'omicronvt', (a, m)),
    }
