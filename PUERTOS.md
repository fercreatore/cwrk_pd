# Mapa de Puertos — Cowork Pedidos
> Actualizado: 24 de marzo de 2026

Todas las apps Streamlit usan puertos fijos para evitar conflictos.
**Antes de agregar una app nueva, elegir el siguiente puerto libre.**

---

## Streamlit Apps

| Puerto | App | Archivo | Donde corre | Comando |
|--------|-----|---------|-------------|---------|
| 8501 | Carga Facturas | `app_carga.py` | Mac / 112 | `streamlit run app_carga.py` (default en `.streamlit/config.toml`) |
| 8502 | H4 Dashboard | `app_h4.py` | Mac / 112 | `streamlit run app_h4.py --server.port 8502` |
| 8503 | Reposicion v2 | `app_reposicion.py` | Mac / 112 | `streamlit run app_reposicion.py --server.port 8503` |
| 8504 | Modelo Locales | `app_locales.py` | Mac | `streamlit run app_locales.py --server.port 8504` |
| 8505 | Multicanal | `app_multicanal.py` | Mac | `streamlit run app_multicanal.py --server.port 8505` |
| 8506 | Family Office | `_family_office/app_family_office.py` | Mac | Proyecto eliminado, puerto libre |
| 8507 | RRHH Dashboard | `app_rrhh.py` | Mac / 112 | `streamlit run app_rrhh.py --server.port 8507` |
| 8508-8509 | *(libres)* | | | |
| 8510 | Go! Get it | `gogetit/app.py` | 112 | `cd C:\gogetit && streamlit run app.py --server.port 8510` |

> **Nota 112**: `iniciar_streamlit.bat` levanta app_h4 en 8502 y app_carga en 8503 (distinto al Mac).
> `instalar_server.bat` y `deploy_carga_112.sh` usan 8501 para app_carga. Verificar cual config esta activa.

---

## Otros Servicios

| Puerto | App | Servidor | Proceso | Notas |
|--------|-----|----------|---------|-------|
| 1433 | SQL Server 2012 RTM | 111 (DELL-SVR) | sqlservr | Produccion. Bases: msgestion01, 03, C, omicronvt |
| 1433 | SQL Server (replica) | 112 (DATASVRW) | sqlservr | Solo SELECT. MCP sql-replica conecta aca |
| 8000 | web2py | 111 (DELL-SVR) | python web2py.py | calzalindo_informes, clz_ventas, clz_lpa, clz_wpu |
| 8001 | FastAPI freelance | 112 (DATASVRW) | uvicorn main:app | `C:\calzalindo_freelance\`, start_freelance.bat |
| 3000 | Metabase | 106 | java | metabase_mcp_wrapper.sh |
| 5432 | PostgreSQL pgvector | 200.58.109.125 | postgres | DB: clz_productos (embeddings) |

---

## Servidores

| IP | Nombre | Rol | Notas |
|----|--------|-----|-------|
| 192.168.2.111 | DELL-SVR | Produccion SQL + web2py | INSERT/UPDATE. Python: `py -3` |
| 192.168.2.112 | DATASVRW | Replica + Streamlit + FastAPI | Solo SELECT (MCP). Python 3.14 |
| 192.168.2.106 | — | Metabase | BI / dashboards |
| 200.58.109.125 | — | PostgreSQL remoto | pgvector embeddings |
