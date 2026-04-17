"""
app_transferencias.py — Gestor de transferencias inter-depósito
Puerto 8506. App liviana: solo lee autorepo_propuestas y genera movistoc.
Sin análisis, sin carga pesada.
"""
import os, sys
import streamlit as st
import pandas as pd
import pyodbc

# ── SSL fix para SQL Server 2012 ──────────────────────────────────────────
OPENSSL_LEGACY_CNF = "/tmp/openssl_legacy.cnf"
if not os.path.exists(OPENSSL_LEGACY_CNF):
    with open(OPENSSL_LEGACY_CNF, "w") as f:
        f.write("[openssl_init]\nssl_conf = ssl_sect\n[ssl_sect]\nsystem_default = ssl_default_sect\n[ssl_default_sect]\nMinProtocol = TLSv1\nCipherString = DEFAULT@SECLEVEL=1\n")

CONN_111 = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;DATABASE=omicronvt;"
    "UID=am;PWD=dl;TrustServerCertificate=yes;Encrypt=no;"
)

# Nombres desde routing (fuente única de verdad)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autorepo.routing import DEPOSITO_NOMBRE as _DN
def _dep(n): return _DN.get(n, f"Dep {n}")

st.set_page_config(page_title="Transferencias", page_icon="🔁", layout="wide")

# ── Conexión ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    os.environ["OPENSSL_CONF"] = OPENSSL_LEGACY_CNF
    return pyodbc.connect(CONN_111, autocommit=False)

def q(sql, params=None):
    os.environ["OPENSSL_CONF"] = OPENSSL_LEGACY_CNF
    conn = pyodbc.connect(CONN_111)
    df = pd.read_sql(sql, conn)
    conn.close()
    return df

def exec_sql(sql, *params):
    os.environ["OPENSSL_CONF"] = OPENSSL_LEGACY_CNF
    conn = pyodbc.connect(CONN_111, autocommit=False)
    try:
        conn.execute(sql, *params)
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()

# ── UI ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧭 Navegación")
    st.markdown("""| App | Link |
|-----|------|
| 🏠 Dashboard H4 | [8502](http://localhost:8502) |
| 🔄 Reposición | [8503](http://localhost:8503) |
| 🔁 Transferencias | **acá** |
| 🏪 Locales | [8504](http://localhost:8504) |
| 🛒 Carga facturas | [8501](http://localhost:8501) |
| 🌐 Multicanal | [8505](http://localhost:8505) |
| 👥 RRHH | [8507](http://localhost:8507) |""")
    st.divider()

st.title("🔁 Transferencias Inter-Depósito")
st.caption("Aprobá propuestas del motor Autorepo para generar la salida al dep 198 (tránsito).")

tab_pend, tab_hist = st.tabs(["📋 Pendientes", "✅ Historial"])

# ── TAB PENDIENTES ────────────────────────────────────────────────────────
with tab_pend:
    df = q("""
        SELECT id, tipo, deposito_emisor, deposito_receptor,
               total_pares, CAST(total_costo_cer AS INT) AS costo_cer,
               score_promedio, fecha_corrida
        FROM omicronvt.dbo.autorepo_propuestas
        WHERE estado = 'PENDIENTE'
        ORDER BY score_promedio DESC
    """)

    if df.empty:
        st.info("No hay propuestas pendientes. El motor corre diariamente a las 07:00.")
    else:
        df["emisor_nom"] = df["deposito_emisor"].map(lambda x: _dep(int(x)))
        df["receptor_nom"] = df["deposito_receptor"].map(lambda x: _dep(int(x)))

        st.metric("Propuestas pendientes", len(df))
        st.dataframe(
            df[["id","emisor_nom","receptor_nom","total_pares","costo_cer","score_promedio","fecha_corrida"]],
            use_container_width=True, hide_index=True,
            column_config={
                "id": "ID",
                "emisor_nom": "Origen",
                "receptor_nom": "Destino",
                "total_pares": "Pares",
                "costo_cer": st.column_config.NumberColumn("Costo $", format="$%d"),
                "score_promedio": st.column_config.NumberColumn("Score", format="%.1f"),
                "fecha_corrida": "Generada",
            }
        )

        st.divider()
        prop_id = st.selectbox("Seleccioná propuesta para ver detalle", df["id"].tolist(),
                               format_func=lambda x: f"#{x} — {df[df['id']==x]['emisor_nom'].values[0]} → {df[df['id']==x]['receptor_nom'].values[0]} ({int(df[df['id']==x]['total_pares'].values[0])} pares)")

        if prop_id:
            row = df[df["id"] == prop_id].iloc[0]

            df_det = q(f"""
                SELECT d.articulo, a.codigo_sinonimo AS sinonimo,
                       a.descripcion_1 AS descripcion, m.descripcion AS marca,
                       d.cantidad, CAST(d.precio_costo AS INT) AS precio_costo,
                       ROUND(d.score,1) AS score,
                       ROUND(d.vel_destino * 30, 1) AS vel_mes_dest,
                       CAST(d.dias_cobertura_destino AS INT) AS dias_cob_destino,
                       d.motivo
                FROM omicronvt.dbo.autorepo_propuestas_det d
                LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = d.articulo
                LEFT JOIN msgestionC.dbo.marcas m ON m.codigo = a.marca
                WHERE d.propuesta_id = {prop_id}
                ORDER BY d.score DESC
            """)

            col1, col2, col3 = st.columns(3)
            col1.metric("Origen", _dep(int(row['deposito_emisor'])))
            col2.metric("Destino final", _dep(int(row['deposito_receptor'])))
            col3.metric("Pares", int(row["total_pares"]))

            st.dataframe(df_det, use_container_width=True, hide_index=True)

            st.divider()
            if st.button(f"✅ Aprobar y generar salida → dep 198 (tránsito)", type="primary", key=f"btn_{prop_id}"):
                st.session_state[f"conf_{prop_id}"] = True

            if st.session_state.get(f"conf_{prop_id}"):
                st.warning(
                    f"Genera salida real: **{_dep(int(row['deposito_emisor']))} → dep 198**. "
                    f"El dep {_dep(int(row['deposito_receptor']))} lo recibe cuando llega. ¿Confirmás?"
                )
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Sí, confirmar", type="primary", key=f"si_{prop_id}"):
                        try:
                            sys.path.insert(0, os.path.dirname(__file__))
                            from autorepo.insertar_transferencia import insertar_salida_transito
                            lineas = df_det[["articulo","sinonimo","descripcion","cantidad","precio_costo"]].to_dict("records")
                            conn_str = (
                                "DRIVER={ODBC Driver 17 for SQL Server};"
                                "SERVER=192.168.2.111;DATABASE=msgestionC;"
                                "UID=am;PWD=dl;TrustServerCertificate=yes;Encrypt=no;"
                            )
                            res = insertar_salida_transito(
                                propuesta_id=int(prop_id),
                                deposito_emisor=int(row["deposito_emisor"]),
                                deposito_receptor_final=int(row["deposito_receptor"]),
                                lineas=lineas, conn_string=conn_str,
                            )
                            exec_sql(
                                "UPDATE omicronvt.dbo.autorepo_propuestas SET estado='APROBADA' WHERE id=?",
                                [int(prop_id)]
                            )
                            st.success(
                                f"✅ Doc #{res['numero']} generado en {res['base']} — "
                                f"{res['renglones']} renglones. "
                                f"Avisale a dep {int(row['deposito_receptor'])} que viene mercadería."
                            )
                            st.session_state[f"conf_{prop_id}"] = False
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
                with c2:
                    if st.button("Cancelar", key=f"no_{prop_id}"):
                        st.session_state[f"conf_{prop_id}"] = False
                        st.rerun()

# ── TAB HISTORIAL ─────────────────────────────────────────────────────────
with tab_hist:
    df_hist = q("""
        SELECT p.id, p.deposito_emisor, p.deposito_receptor,
               p.total_pares, CAST(p.total_costo_cer AS INT) AS costo_cer,
               p.estado, p.fecha_corrida,
               d.articulo, a.codigo_sinonimo,
               a.descripcion_1 AS descripcion, m.descripcion AS marca,
               d.cantidad, CAST(d.precio_costo AS INT) AS precio_costo
        FROM omicronvt.dbo.autorepo_propuestas p
        JOIN omicronvt.dbo.autorepo_propuestas_det d ON d.propuesta_id = p.id
        LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = d.articulo
        LEFT JOIN msgestionC.dbo.marcas m ON m.codigo = a.marca
        WHERE p.estado <> 'PENDIENTE'
        ORDER BY p.fecha_corrida DESC, p.id, d.score DESC
    """)
    if df_hist.empty:
        st.info("Sin historial aún.")
    else:
        df_hist["emisor_nom"]   = df_hist["deposito_emisor"].map(lambda x: _dep(int(x)))
        df_hist["receptor_nom"] = df_hist["deposito_receptor"].map(lambda x: _dep(int(x)))
        for prop_id, grp in df_hist.groupby("id", sort=False):
            row0 = grp.iloc[0]
            with st.expander(
                f"#{prop_id} — {row0['emisor_nom']} → {row0['receptor_nom']} "
                f"| {int(row0['total_pares'])} pares | {row0['estado']} | {str(row0['fecha_corrida'])[:16]}"
            ):
                st.dataframe(
                    grp[["articulo","codigo_sinonimo","descripcion","marca","cantidad","precio_costo"]],
                    use_container_width=True, hide_index=True,
                    column_config={
                        "articulo":        "Código",
                        "codigo_sinonimo": "Sinónimo",
                        "descripcion":     "Descripción",
                        "marca":           "Marca",
                        "cantidad":        "Cant",
                        "precio_costo":    st.column_config.NumberColumn("Costo $", format="$%d"),
                    }
                )
