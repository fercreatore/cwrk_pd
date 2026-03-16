# -*- coding: utf-8 -*-
"""
API del Catálogo Comercial.
Gestiona fotos, descripciones y contenido para redes sociales.

Endpoints:
  GET  /api/v1/catalogo/productos           → Lista productos con/sin contenido
  GET  /api/v1/catalogo/producto/{sku}       → Detalle de un producto
  POST /api/v1/catalogo/producto/{sku}       → Crear/actualizar contenido comercial
  GET  /api/v1/catalogo/pendientes           → Productos sin contenido (cola de trabajo)
  POST /api/v1/catalogo/generar_contenido    → Genera posts para todos los vendedores
  GET  /api/v1/catalogo/stock/{sku}          → Stock por talle de un SKU
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from db import query_omicronvt, query_articulos, execute, get_db
from config import settings

router = APIRouter()


class ContenidoIn(BaseModel):
    titulo_corto: str
    descripcion_redes: Optional[str] = None
    hashtags: Optional[str] = None
    categoria_fee: str = "STD"      # STD o PREMIUM
    foto_principal: Optional[str] = None
    marca_cod: Optional[int] = None


@router.get("/productos")
async def lista_productos(pagina: int = 1, limite: int = 50, solo_sin_contenido: bool = False):
    """Lista de productos agrupados por SKU base, con estado de contenido comercial."""

    # SKUs base unicos desde articulo (agrupados por primeros 5 chars de descripcion_1)
    sql = """
        SELECT TOP %d
            LEFT(a.descripcion_1, 5) AS sku_base,
            MIN(a.descripcion_1) AS descripcion,
            m.descripcion AS marca,
            a.marca AS marca_cod,
            COUNT(*) AS talles,
            SUM(CASE WHEN s.stock_actual > 0 THEN 1 ELSE 0 END) AS talles_con_stock,
            MIN(a.precio_1) AS precio_min,
            MAX(a.precio_1) AS precio_max,
            cc.id AS contenido_id,
            cc.titulo_corto,
            cc.descripcion_redes,
            CASE WHEN cc.id IS NOT NULL THEN 1 ELSE 0 END AS tiene_contenido
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN msgestionC.dbo.marcas m ON m.codigo = a.marca
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stock_actual
            FROM omicronvt.dbo.stock_por_codigo
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        LEFT JOIN omicronvt.dbo.catalogo_comercial cc ON cc.sku_base = LEFT(a.descripcion_1, 5)
        WHERE a.precio_1 > 0
          AND LEN(a.descripcion_1) >= 5
          %s
        GROUP BY LEFT(a.descripcion_1, 5), m.descripcion, a.marca,
                 cc.id, cc.titulo_corto, cc.descripcion_redes
        ORDER BY tiene_contenido ASC, marca
    """ % (
        limite,
        "AND cc.id IS NULL" if solo_sin_contenido else "",
    )

    return {"productos": query_omicronvt(sql)}


@router.get("/producto/{sku}")
async def detalle_producto(sku: str):
    """Detalle completo de un SKU base con todos sus talles y stock."""

    # Info del catalogo comercial
    cc = query_omicronvt(
        "SELECT * FROM catalogo_comercial WHERE sku_base = '%s'" % sku
    )
    contenido = cc[0] if cc else None

    # Talles y stock
    sql_talles = """
        SELECT a.codigo, a.descripcion_1, a.descripcion_5 AS talle,
               a.precio_1, a.precio_2, a.precio_3, a.precio_4,
               ISNULL(s.stock_actual, 0) AS stock,
               m.descripcion AS marca
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stock_actual
            FROM omicronvt.dbo.stock_por_codigo
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        LEFT JOIN msgestionC.dbo.marcas m ON m.codigo = a.marca
        WHERE LEFT(a.descripcion_1, %d) = '%s'
        ORDER BY a.descripcion_5
    """ % (len(sku), sku)

    talles = query_omicronvt(sql_talles)

    return {
        "sku_base": sku,
        "contenido_comercial": contenido,
        "talles": talles,
        "resumen": {
            "total_talles": len(talles),
            "talles_con_stock": sum(1 for t in talles if (t.get('stock') or 0) > 0),
            "stock_total": sum(int(t.get('stock') or 0) for t in talles),
            "precio_min": min((float(t.get('precio_1') or 0) for t in talles if (t.get('precio_1') or 0) > 0), default=0),
            "precio_max": max((float(t.get('precio_1') or 0) for t in talles), default=0),
        }
    }


@router.post("/producto/{sku}")
async def crear_actualizar_contenido(sku: str, data: ContenidoIn):
    """Crear o actualizar contenido comercial de un SKU."""
    existe = query_omicronvt(
        "SELECT id FROM catalogo_comercial WHERE sku_base = '%s'" % sku
    )

    if existe:
        sql = """
            UPDATE omicronvt.dbo.catalogo_comercial SET
                titulo_corto = N'%s',
                descripcion_redes = N'%s',
                hashtags = N'%s',
                categoria_fee = '%s',
                foto_principal = '%s',
                marca_cod = %s,
                fecha_modif = GETDATE()
            WHERE sku_base = '%s'
        """ % (
            (data.titulo_corto or '').replace("'", "''"),
            (data.descripcion_redes or '').replace("'", "''"),
            (data.hashtags or '').replace("'", "''"),
            data.categoria_fee,
            data.foto_principal or '',
            data.marca_cod if data.marca_cod else 'NULL',
            sku
        )
        execute(sql, 'omicronvt')
        return {"sku": sku, "accion": "actualizado"}
    else:
        sql = """
            INSERT INTO omicronvt.dbo.catalogo_comercial
            (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, foto_principal, marca_cod)
            VALUES (
                '%s', N'%s', N'%s', N'%s', '%s', '%s', %s
            )
        """ % (
            sku,
            (data.titulo_corto or '').replace("'", "''"),
            (data.descripcion_redes or '').replace("'", "''"),
            (data.hashtags or '').replace("'", "''"),
            data.categoria_fee,
            data.foto_principal or '',
            data.marca_cod if data.marca_cod else 'NULL',
        )
        execute(sql, 'omicronvt')
        return {"sku": sku, "accion": "creado"}


@router.get("/pendientes")
async def pendientes():
    """Productos activos (con stock > 0) que no tienen contenido comercial."""
    sql = """
        SELECT
            LEFT(a.descripcion_1, 5) AS sku_base,
            MIN(a.descripcion_1) AS descripcion,
            m.descripcion AS marca,
            COUNT(*) AS talles,
            SUM(CASE WHEN s.stock_actual > 0 THEN 1 ELSE 0 END) AS talles_con_stock
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN msgestionC.dbo.marcas m ON m.codigo = a.marca
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stock_actual
            FROM omicronvt.dbo.stock_por_codigo
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        WHERE a.precio_1 > 0
          AND LEN(a.descripcion_1) >= 5
          AND NOT EXISTS (
              SELECT 1 FROM omicronvt.dbo.catalogo_comercial cc
              WHERE cc.sku_base = LEFT(a.descripcion_1, 5)
          )
        GROUP BY LEFT(a.descripcion_1, 5), m.descripcion
        HAVING SUM(CASE WHEN s.stock_actual > 0 THEN 1 ELSE 0 END) > 0
        ORDER BY talles_con_stock DESC
    """
    return {"pendientes": query_omicronvt(sql)}


@router.post("/generar_contenido/{sku}")
async def generar_contenido_vendedores(sku: str):
    """
    Genera contenido pre-armado (texto para IG/WA) para cada vendedor activo.
    Cada vendedor obtiene su version personalizada con su link de atribucion.
    """
    # Info del producto
    cc = query_omicronvt(
        "SELECT * FROM catalogo_comercial WHERE sku_base = '%s' AND activo = 1" % sku
    )
    if not cc:
        raise HTTPException(404, "Producto sin contenido comercial. Cargarlo primero.")
    prod = cc[0]

    # Vendedores activos
    vendedores = query_omicronvt(
        "SELECT * FROM vendedor_freelance WHERE activo = 1"
    )

    count = 0
    for vend in vendedores:
        link = "%s/%s?v=%s" % (settings.LINK_BASE, sku, vend['codigo_atrib'])

        # Template Instagram
        texto_ig = "%s\n%s\n\n%s\n\nConsultame por disponibilidad y talles\n%s" % (
            prod.get('titulo_corto', sku),
            prod.get('descripcion_redes', ''),
            prod.get('hashtags', ''),
            link,
        )

        # Template WhatsApp
        texto_wa = "*%s*\n%s\n\nLink: %s\n\nEscribime para consultar talles y stock" % (
            prod.get('titulo_corto', sku),
            prod.get('descripcion_redes', ''),
            link,
        )

        for canal, texto in [('INSTAGRAM', texto_ig), ('WHATSAPP', texto_wa)]:
            # Solo si no existe ya uno LISTO
            existe = query_omicronvt(
                "SELECT id FROM contenido_generado "
                "WHERE sku_base = '%s' AND vendedor_id = %d AND canal = '%s' AND estado = 'LISTO'"
                % (sku, vend['id'], canal)
            )
            if not existe:
                sql = """
                    INSERT INTO omicronvt.dbo.contenido_generado
                    (sku_base, vendedor_id, canal, contenido_texto, link_atribucion, estado)
                    VALUES ('%s', %d, '%s', N'%s', '%s', 'LISTO')
                """ % (
                    sku, vend['id'], canal,
                    texto.replace("'", "''"),
                    link,
                )
                execute(sql, 'omicronvt')
                count += 1

    return {"sku": sku, "contenido_generado": count, "vendedores": len(vendedores)}


@router.get("/stock/{sku}")
async def stock_por_talle(sku: str):
    """Stock por talle de un SKU (para que el vendedor consulte disponibilidad)."""
    sql = """
        SELECT a.descripcion_5 AS talle,
               ISNULL(SUM(s.stock_actual), 0) AS stock,
               a.precio_1 AS precio
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stock_actual
            FROM omicronvt.dbo.stock_por_codigo
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        WHERE LEFT(a.descripcion_1, %d) = '%s'
        GROUP BY a.descripcion_5, a.precio_1
        ORDER BY a.descripcion_5
    """ % (len(sku), sku)

    talles = query_omicronvt(sql)
    return {
        "sku": sku,
        "talles": [
            {
                "talle": (t.get('talle') or '').strip(),
                "stock": int(t.get('stock') or 0),
                "disponible": int(t.get('stock') or 0) > 0,
                "precio": float(t.get('precio') or 0),
            }
            for t in talles
        ]
    }
