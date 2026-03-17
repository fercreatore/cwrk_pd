# Mapa de Puertos — Cowork Pedidos

Todas las apps Streamlit usan puertos fijos para evitar conflictos.
**Antes de agregar una app nueva, elegir el siguiente puerto libre.**

## Streamlit Apps

| Puerto | App | Archivo | Dónde corre | Comando |
|--------|-----|---------|-------------|---------|
| 8501 | Carga Facturas | `app_carga.py` | **Solo 112** | `streamlit run app_carga.py` |
| 8502 | H4 Dashboard | `app_h4.py` | Mac / 112 | `streamlit run app_h4.py --server.port 8502` |
| 8503 | Reposición v2 | `app_reposicion.py` | Mac / 112 | `streamlit run app_reposicion.py --server.port 8503` |
| 8504 | *(libre)* | | | |
| 8505 | Multicanal | `app_multicanal.py` | Mac | `streamlit run app_multicanal.py --server.port 8505` |
| 8506 | Family Office | `_family_office/app_family_office.py` | Mac | `cd _family_office && streamlit run app_family_office.py --server.port 8506` |

## Servidores

| IP | Nombre | Rol | Notas |
|----|--------|-----|-------|
| 192.168.2.111 | DELL-SVR | Producción SQL Server 2012 | INSERT/UPDATE. Python: `py -3` |
| 192.168.2.112 | DATASVRW | Réplica + Streamlit apps | Solo SELECT (MCP sql-replica) |
| 200.58.109.125:5432 | PostgreSQL | Embeddings pgvector | DB: `clz_productos` |
