# -*- coding: utf-8 -*-
"""
API de Atribución de Ventas.
Registra qué vendedor generó cada venta y por qué canal.

Endpoints:
  POST /api/v1/atribucion/registrar       → Registrar atribucion manual
  POST /api/v1/atribucion/sync_viajante   → Sync automatico desde ventas1_vendedor
  GET  /api/v1/atribucion/por_vendedor    → Atribuciones de un vendedor
  GET  /api/v1/atribucion/por_canal       → Breakdown por canal
  GET  /api/v1/atribucion/pendientes      → Ventas sin factura de servicio emitida
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from db import query_omicronvt, execute, get_db

router = APIRouter()


class AtribucionIn(BaseModel):
    vendedor_cod: str           # V569
    canal_origen: str           # INSTAGRAM, WHATSAPP, PRESENCIAL, ML, WEB
    monto_producto: float
    cant_pares: int = 1
    hora_venta: Optional[str] = None   # HH:MM
    # Referencia opcional al comprobante del ERP
    empresa: Optional[str] = None
    vta_codigo: Optional[int] = None
    vta_letra: Optional[str] = None
    vta_sucursal: Optional[int] = None
    vta_numero: Optional[int] = None
    vta_orden: Optional[int] = None


@router.post("/registrar")
async def registrar_atribucion(data: AtribucionIn):
    """
    Registra una venta atribuida a un vendedor.
    Calcula automaticamente el fee segun franja horaria.
    """
    # Buscar vendedor
    rows = query_omicronvt(
        "SELECT * FROM vendedor_freelance WHERE codigo_atrib = '%s' AND activo = 1"
        % data.vendedor_cod
    )
    if not rows:
        raise HTTPException(404, "Vendedor %s no encontrado" % data.vendedor_cod)
    vend = rows[0]

    # Determinar fee base (STD o PREMIUM — por ahora STD para todas)
    fee_base = float(vend.get('fee_pct_std') or 0.05)

    # Buscar bonus por franja horaria
    bonus = 0.0
    if data.hora_venta:
        hoy = datetime.now()
        dia_semana = hoy.isoweekday()  # 1=Lunes
        bonus_rows = query_omicronvt(
            "SELECT bonus_fee_pct FROM franjas_incentivo "
            "WHERE dia_semana = %d AND hora_desde <= '%s' AND hora_hasta > '%s'"
            % (dia_semana, data.hora_venta, data.hora_venta)
        )
        if bonus_rows:
            bonus = float(bonus_rows[0]['bonus_fee_pct'] or 0)

    fee_total = fee_base + bonus
    fee_monto = round(data.monto_producto * fee_total, 2)

    # Insertar atribucion
    sql = """
        INSERT INTO omicronvt.dbo.venta_atribucion (
            empresa, vta_codigo, vta_letra, vta_sucursal, vta_numero, vta_orden,
            vendedor_id, canal_origen, fecha, hora_venta,
            monto_producto, cant_pares,
            fee_pct_base, bonus_franja, fee_pct_total, fee_monto,
            estado_factura
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %d, '%s', GETDATE(), %s,
            %.2f, %d,
            %.4f, %.4f, %.4f, %.2f,
            'PEND'
        )
    """ % (
        ("'%s'" % data.empresa) if data.empresa else 'NULL',
        data.vta_codigo if data.vta_codigo else 'NULL',
        ("'%s'" % data.vta_letra) if data.vta_letra else 'NULL',
        data.vta_sucursal if data.vta_sucursal else 'NULL',
        data.vta_numero if data.vta_numero else 'NULL',
        data.vta_orden if data.vta_orden else 'NULL',
        vend['id'], data.canal_origen,
        ("'%s'" % data.hora_venta) if data.hora_venta else 'NULL',
        data.monto_producto, data.cant_pares,
        fee_base, bonus, fee_total, fee_monto,
    )

    with get_db('omicronvt') as cur:
        cur.execute(sql)
        cur.execute("SELECT SCOPE_IDENTITY() AS id")
        new_id = cur.fetchone()['id']

    return {
        "id": new_id,
        "vendedor": data.vendedor_cod,
        "canal": data.canal_origen,
        "monto_producto": data.monto_producto,
        "fee": {
            "base": fee_base,
            "bonus_franja": bonus,
            "total_pct": fee_total,
            "monto": fee_monto,
        },
        "estado": "PEND",
    }


@router.post("/sync_viajante")
async def sync_desde_viajante(fecha_desde: str = None):
    """
    Sync automatico: toma ventas de ventas1_vendedor que tengan viajante
    asociado a un vendedor_freelance y crea atribuciones automaticas
    para las que no existan.
    Canal: PRESENCIAL (default para ventas sin tracking de link).
    """
    if not fecha_desde:
        fecha_desde = str(date.today())

    sql = """
        INSERT INTO omicronvt.dbo.venta_atribucion (
            empresa, vta_codigo, vta_letra, vta_sucursal, vta_numero, vta_orden,
            vendedor_id, canal_origen, fecha, hora_venta,
            monto_producto, cant_pares,
            fee_pct_base, bonus_franja, fee_pct_total, fee_monto,
            estado_factura
        )
        SELECT
            v.empresa, v.codigo, v.letra, v.sucursal, v.numero, v.orden,
            vf.id, 'PRESENCIAL', v.fecha,
            RIGHT('0' + CAST(DATEPART(hour, v.fecha) AS VARCHAR), 2) + ':' +
            RIGHT('0' + CAST(DATEPART(minute, v.fecha) AS VARCHAR), 2),
            SUM(v.total_item),
            SUM(v.cantidad),
            vf.fee_pct_std, 0, vf.fee_pct_std,
            SUM(v.total_item) * vf.fee_pct_std,
            'PEND'
        FROM omicronvt.dbo.ventas1_vendedor v
        JOIN omicronvt.dbo.vendedor_freelance vf ON vf.viajante_cod = v.viajante AND vf.activo = 1
        WHERE v.fecha >= '%s'
          AND v.codigo = 1  -- solo facturas, no NC
          AND NOT EXISTS (
              SELECT 1 FROM omicronvt.dbo.venta_atribucion va
              WHERE va.empresa = v.empresa
                AND va.vta_codigo = v.codigo
                AND va.vta_sucursal = v.sucursal
                AND va.vta_numero = v.numero
                AND va.vta_orden = v.orden
          )
        GROUP BY v.empresa, v.codigo, v.letra, v.sucursal, v.numero, v.orden,
                 vf.id, v.fecha, vf.fee_pct_std
    """ % fecha_desde

    count = execute(sql, 'omicronvt')
    return {"sincronizadas": count, "desde": fecha_desde}


@router.get("/por_vendedor/{cod}")
async def por_vendedor(cod: str, mes: int = None, anio: int = None):
    """Atribuciones de un vendedor en un periodo."""
    rows = query_omicronvt(
        "SELECT id FROM vendedor_freelance WHERE codigo_atrib = '%s'" % cod
    )
    if not rows:
        raise HTTPException(404, "Vendedor no encontrado")
    vend_id = rows[0]['id']

    hoy = date.today()
    m = mes or hoy.month
    a = anio or hoy.year

    sql = """
        SELECT va.*, vf.codigo_atrib
        FROM omicronvt.dbo.venta_atribucion va
        JOIN omicronvt.dbo.vendedor_freelance vf ON vf.id = va.vendedor_id
        WHERE va.vendedor_id = %d
          AND YEAR(va.fecha) = %d AND MONTH(va.fecha) = %d
        ORDER BY va.fecha DESC
    """ % (vend_id, a, m)

    atribs = query_omicronvt(sql)
    total_fee = sum(float(r.get('fee_monto') or 0) for r in atribs)
    total_producto = sum(float(r.get('monto_producto') or 0) for r in atribs)

    # Breakdown por canal
    canales = {}
    for r in atribs:
        c = r.get('canal_origen', 'OTRO')
        if c not in canales:
            canales[c] = {"count": 0, "monto": 0, "fee": 0}
        canales[c]["count"] += 1
        canales[c]["monto"] += float(r.get('monto_producto') or 0)
        canales[c]["fee"] += float(r.get('fee_monto') or 0)

    return {
        "vendedor": cod,
        "periodo": "%d-%02d" % (a, m),
        "total_operaciones": len(atribs),
        "total_producto": round(total_producto, 0),
        "total_fee": round(total_fee, 0),
        "por_canal": canales,
        "pendientes_factura": sum(1 for r in atribs if r.get('estado_factura') == 'PEND'),
    }


@router.get("/por_canal")
async def por_canal(mes: int = None, anio: int = None):
    """Breakdown global de ventas por canal (para gerencia)."""
    hoy = date.today()
    m = mes or hoy.month
    a = anio or hoy.year

    sql = """
        SELECT
            canal_origen,
            COUNT(*) AS operaciones,
            SUM(monto_producto) AS total_producto,
            SUM(fee_monto) AS total_fee,
            COUNT(DISTINCT vendedor_id) AS vendedores
        FROM omicronvt.dbo.venta_atribucion
        WHERE YEAR(fecha) = %d AND MONTH(fecha) = %d
        GROUP BY canal_origen
        ORDER BY total_producto DESC
    """ % (a, m)

    return {
        "periodo": "%d-%02d" % (a, m),
        "canales": query_omicronvt(sql),
    }


@router.get("/pendientes")
async def pendientes_factura(cod: str = None):
    """Ventas sin factura de servicio emitida."""
    where_extra = ""
    if cod:
        where_extra = " AND vf.codigo_atrib = '%s'" % cod

    sql = """
        SELECT va.*, vf.codigo_atrib, vf.cuit AS vendedor_cuit
        FROM omicronvt.dbo.venta_atribucion va
        JOIN omicronvt.dbo.vendedor_freelance vf ON vf.id = va.vendedor_id
        WHERE va.estado_factura = 'PEND'%s
        ORDER BY va.fecha DESC
    """ % where_extra

    return {"pendientes": query_omicronvt(sql)}
