# CLAUDE.md — _freelance/

## QUÉ HACE
Sistema de gestión de vendedores freelance para H4/Calzalindo. Reemplaza modelo empleado (43% carga social) por red de microemprendedores con comisión (5-8%). Cada vendedor tiene dashboard propio, catálogo con contenido pre-generado para redes, tracking de atribución por canal, y liquidación mensual automática.

**Owner**: Fernando.

---

## ARQUITECTURA

- **Backend**: FastAPI + Uvicorn (port 8001, coexiste con web2py en 8000)
- **DB**: SQL Server 2012 (111 producción, 112 réplica) — tablas en `omicronvt`
- **Auth**: MySQL `clz_ventas_mysql` (109) — compatible con web2py PBKDF2
- **Frontend**: Jinja2 templates, mobile-first

---

## ARCHIVOS CLAVE

| Archivo | Función |
|---------|---------|
| `src/main.py` | Entry point FastAPI, routers, templates |
| `src/config.py` | Settings: DB creds, fees (5%/8%), monotributo topes |
| `src/db.py` | Pool pyodbc + helpers (query_omicronvt, etc.) |
| `src/api/auth.py` | Login contra MySQL, PBKDF2, sesiones 7 días |
| `src/api/vendedor.py` | Dashboard vendedor: KPIs, ventas, ranking, catálogo, proyección monotributo |
| `src/api/catalogo.py` | Productos con contenido social, stock por talle |
| `src/api/atribucion.py` | Registro de ventas por vendedor + canal (IG, WA, ML, presencial) |
| `src/api/liquidacion.py` | Liquidación mensual: fee base + bonus - canon - mono = neto |
| `src/api/gerencial.py` | Dashboard gerencia: KPIs red, ahorro vs empleado, alertas |
| `src/sql/001_crear_tablas_freelance.sql` | DDL 7 tablas en omicronvt |
| `src/templates/` | 3 HTML: home (login), panel_vendedor, admin_dashboard |
| `ARQUITECTURA_SISTEMA_VENDEDOR_FREELANCE.md` | Spec completa (623 líneas) |

---

## TABLAS (en `omicronvt`)

1. `vendedor_freelance` — Extiende viajantes con datos freelance (CUIT, monotributo, fee, redes)
2. `franjas_incentivo` — Bonus por franja horaria (gamificación)
3. `catalogo_comercial` — Catálogo con metadata social (títulos, hashtags, fotos)
4. `venta_atribucion` — Tracking venta → vendedor → canal
5. `cliente_vendedor` — Mini CRM por vendedor
6. `contenido_generado` — Posts pre-armados para cada vendedor×producto×canal
7. `liquidacion_vendedor` — Liquidación mensual (BORR → APROBADA → PAGADA)

---

## CÓMO SE USA

```bash
# En servidor 111
cd _freelance/src
python -m uvicorn main:app --host 0.0.0.0 --port 8001

# Setup DB (primera vez)
sqlcmd -S 192.168.2.111 -U am -P dl -d omicronvt -i src/sql/001_crear_tablas_freelance.sql
```

API docs: `http://192.168.2.111:8001/docs`

---

## CONEXIÓN CON PROYECTO PRINCIPAL

- Lee de `msgestionC` (ventas, viajantes), `msgestion01art` (artículos, stock, precios)
- Escribe en `omicronvt` (tablas freelance propias)
- Auth compartida con web2py (MySQL `clz_ventas_mysql`)
- Ortogonal al pipeline de pedidos (pedidos = compras entrantes, freelance = ventas salientes)

## ESTADO

Fase 1-2 implementada (backend completo, UI funcional). Falta: generación de contenido con Pillow, integración ML/TN/WA API, auto-sync desde ventas1_vendedor.

## QUÉ NO TOCAR

- Compatibilidad PBKDF2 con web2py en `auth.py`
- Estructura de tablas en `001_crear_tablas_freelance.sql` (ya deployadas)

## DEPENDENCIAS

fastapi, uvicorn, pyodbc, pymysql, pydantic, jinja2, pillow, python-dateutil
