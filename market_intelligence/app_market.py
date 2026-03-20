"""
App Streamlit para Market Intelligence.

Uso:
    streamlit run market_intelligence/app_market.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import time
from datetime import datetime

# Add parent dir to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from market_intelligence.ml_scraper import MLScraper
from market_intelligence.analyzer import MarketAnalyzer, fetch_exchange_rate
from market_intelligence.instagram import InstagramAuditor
from market_intelligence.facebook import FacebookAuditor
from market_intelligence.whatsapp import WhatsAppChecker
from market_intelligence.website_audit import WebsiteAuditor
from market_intelligence.skills import SkillsAudit

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

st.set_page_config(page_title="Market Intelligence", layout="wide")
st.title("Market Intelligence — Importación")

# --- Sidebar config ---
st.sidebar.header("Configuración")
auto_rate = st.sidebar.checkbox("TC automático (DolarAPI)", value=True)
if auto_rate:
    exchange_rate = fetch_exchange_rate()
    st.sidebar.info(f"TC actual: ${exchange_rate:,.0f} ARS/USD")
else:
    exchange_rate = st.sidebar.number_input("Tipo de cambio USD/ARS", value=1250, step=50)
ml_commission = st.sidebar.number_input("Comisión ML Premium %", value=16.0, step=0.5)
pages = st.sidebar.slider("Páginas ML por búsqueda", 1, 5, 2)

# --- Tab layout ---
tab_scan, tab_compare, tab_social, tab_website, tab_competitor, tab_history = st.tabs([
    "Scan ML",
    "Comparar categorías",
    "Redes Sociales",
    "Auditoría Web",
    "Competidores",
    "Historial",
])

# ============================
# TAB 1: Scan individual
# ============================
with tab_scan:
    st.subheader("Escanear una categoría en MercadoLibre")

    col1, col2 = st.columns(2)
    with col1:
        query = st.text_input("Búsqueda ML", value="valijas de viaje")
    with col2:
        landed_usd = st.number_input("Costo landed USD (puesto en AR)", value=12.0, step=0.5)

    if st.button("Escanear", type="primary", key="btn_scan"):
        scraper = MLScraper()

        with st.spinner(f"Buscando '{query}' en MercadoLibre..."):
            items = scraper.search(query, pages=pages)
            analysis = scraper.analyze(items)

        if not items:
            st.error("No se encontraron resultados")
        else:
            # Save results
            scraper.save_results(items, analysis, query)

            # Market overview
            st.subheader(f"Mercado: {query}")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Items", analysis["total_items"])
            m2.metric("Precio Mediana", f"${analysis['price_median']:,}")
            m3.metric("Rango", f"${analysis['price_min']:,} — ${analysis['price_max']:,}")
            m4.metric("Envío gratis", f"{analysis['free_shipping_pct']}%")

            # Price distribution (histogram)
            st.subheader("Distribución de precios")
            prices = [i["price"] for i in items if i["price"] > 0]
            if prices:
                df_prices = pd.DataFrame({"Precio ARS": prices})
                n_bins = min(20, len(set(prices)))
                hist_counts, bin_edges = np.histogram(prices, bins=n_bins)
                bin_labels = [f"${int(bin_edges[i]):,}-${int(bin_edges[i+1]):,}" for i in range(len(hist_counts))]
                df_hist = pd.DataFrame({"Rango de precio": bin_labels, "Cantidad": hist_counts})
                st.bar_chart(df_hist.set_index("Rango de precio"))

            # Segments
            st.subheader("Segmentos de precio")
            seg_data = []
            for seg_name, seg in analysis["segments"].items():
                seg_data.append({
                    "Segmento": seg_name,
                    "Rango": seg["range"],
                    "Items": seg["count"],
                    "Ejemplos": ", ".join(f'{i["title"][:40]}' for i in seg["items"]),
                })
            st.dataframe(pd.DataFrame(seg_data), use_container_width=True)

            # Brands
            if analysis["top_brands"]:
                st.subheader("Marcas dominantes")
                df_brands = pd.DataFrame(analysis["top_brands"], columns=["Marca", "Cantidad"])
                st.bar_chart(df_brands.set_index("Marca"))

            # Import opportunity
            st.subheader("Oportunidad de importación")
            landed_ars = landed_usd * exchange_rate
            net_median = analysis["price_median"] * (1 - ml_commission / 100)
            margin = (net_median - landed_ars) / net_median * 100 if net_median > 0 else 0

            o1, o2, o3 = st.columns(3)
            o1.metric("Costo landed", f"${landed_ars:,.0f} ARS")
            o2.metric("Margen a mediana", f"{margin:.1f}%",
                       delta="Viable" if margin >= 25 else "Ajustado")
            bep_denom = 1 - 0.25 - ml_commission / 100
            bep = landed_ars / bep_denom if bep_denom > 0 else float('inf')
            o3.metric("Break-even (25%)", f"${bep:,.0f}" if bep != float('inf') else "N/A")

            # Suggested prices table
            margins = [30, 35, 40, 45, 50]
            price_table = []
            for m in margins:
                denom = 1 - m / 100 - ml_commission / 100
                if denom <= 0:
                    continue
                p = landed_ars / denom
                position = ""
                if p < analysis["price_q1"]:
                    position = "Por debajo de Q1 (muy competitivo)"
                elif p < analysis["price_median"]:
                    position = "Entre Q1 y Mediana (competitivo)"
                elif p < analysis["price_q3"]:
                    position = "Entre Mediana y Q3"
                else:
                    position = "Por encima de Q3 (premium)"
                price_table.append({
                    "Margen": f"{m}%",
                    "Precio ML": f"${p:,.0f}",
                    "Posición": position,
                })
            st.table(pd.DataFrame(price_table))

            # Raw listings
            with st.expander("Ver listings completos"):
                df_items = pd.DataFrame(items)
                df_items = df_items[["title", "price", "brand", "free_shipping"]]
                df_items.columns = ["Título", "Precio", "Marca", "Envío gratis"]
                st.dataframe(df_items.sort_values("Precio"), use_container_width=True)


# ============================
# TAB 2: Comparar categorías
# ============================
with tab_compare:
    st.subheader("Comparar múltiples categorías")
    st.caption("Ingresá categorías con su costo landed estimado en USD")

    default_categories = """carry on cabina rigida,12
set valijas rigidas,28
bolso de viaje grande,6
neceser viaje,3
organizador de valija,2.5
mochila viaje carry on,10
cartera mujer cuero,8
mochila urbana mujer,7"""

    categories_text = st.text_area(
        "Categorías (una por línea: búsqueda,costo_usd)",
        value=default_categories,
        height=200,
    )

    if st.button("Comparar todas", type="primary", key="btn_compare"):
        scraper = MLScraper()
        results = []

        lines = [l.strip() for l in categories_text.strip().split("\n") if l.strip()]
        progress = st.progress(0)

        for idx, line in enumerate(lines):
            parts = line.split(",")
            if len(parts) != 2:
                continue
            q = parts[0].strip()
            cost = float(parts[1].strip())

            with st.spinner(f"Escaneando: {q}..."):
                items = scraper.search(q, pages=1)
                analysis = scraper.analyze(items)

            landed_ars = cost * exchange_rate
            net_median = analysis["price_median"] * (1 - ml_commission / 100)
            margin = (net_median - landed_ars) / net_median * 100 if net_median > 0 else 0
            bep_d = 1 - 0.25 - ml_commission / 100
            bep = landed_ars / bep_d if bep_d > 0 else float('inf')

            p40_d = 1 - 0.40 - ml_commission / 100
            p40 = landed_ars / p40_d if p40_d > 0 else float('inf')

            results.append({
                "Categoría": q,
                "Landed USD": cost,
                "Landed ARS": landed_ars,
                "ML Mediana": analysis["price_median"],
                "ML Q1": analysis["price_q1"],
                "Margen %": round(margin, 1),
                "BEP 25%": round(bep),
                "Precio 40%": round(p40),
                "Items": analysis["total_items"],
                "Status": "OK" if margin >= 25 else ("AJUSTADO" if margin >= 15 else "INVIABLE"),
            })

            progress.progress((idx + 1) / len(lines))
            if idx < len(lines) - 1:
                time.sleep(1.5)

        df = pd.DataFrame(results).sort_values("Margen %", ascending=False)
        st.dataframe(
            df.style.apply(
                lambda x: ["background-color: #d4edda" if v == "OK"
                           else "background-color: #fff3cd" if v == "AJUSTADO"
                           else "background-color: #f8d7da" if v == "INVIABLE"
                           else "" for v in x],
                subset=["Status"]
            ),
            use_container_width=True,
        )

        # Chart
        st.subheader("Margen por categoría")
        chart_df = df[["Categoría", "Margen %"]].set_index("Categoría")
        st.bar_chart(chart_df)


# ============================
# TAB 3: Redes Sociales
# ============================
with tab_social:
    st.subheader("Auditoría de Redes Sociales")

    social_tab_ig, social_tab_fb, social_tab_wa = st.tabs([
        "Instagram", "Facebook", "WhatsApp"
    ])

    # --- Instagram ---
    with social_tab_ig:
        st.markdown("#### Auditoría de Instagram")
        ig_usernames = st.text_area(
            "Usuarios de Instagram (uno por línea, sin @)",
            value="samsonite_ar\ndelsey_ar\nroncato_ar",
            height=120,
            key="ig_users",
        )

        if st.button("Auditar Instagram", type="primary", key="btn_ig"):
            auditor = InstagramAuditor()
            usernames = [u.strip() for u in ig_usernames.strip().split("\n") if u.strip()]

            progress = st.progress(0)
            results = []
            for i, username in enumerate(usernames):
                with st.spinner(f"Auditando @{username}..."):
                    result = auditor.audit_profile(username)
                    results.append(result)
                progress.progress((i + 1) / len(usernames))
                if i < len(usernames) - 1:
                    time.sleep(3)

            # Tabla resumen
            table_data = []
            for r in results:
                table_data.append({
                    "Usuario": f"@{r['username']}",
                    "Accesible": "Si" if r.get("accessible") else "No",
                    "Followers": r.get("followers") or "-",
                    "Following": r.get("following") or "-",
                    "Posts": r.get("posts_count") or "-",
                    "Business": "Si" if r.get("is_business") else "-",
                    "Verificado": "Si" if r.get("is_verified") else "-",
                    "Web": r.get("external_url") or "-",
                })
            st.dataframe(pd.DataFrame(table_data), use_container_width=True)

            # Comparativa
            comparison = auditor.compare_profiles(results)
            if "ranking" in comparison:
                st.subheader("Ranking por followers")
                rank_data = pd.DataFrame(comparison["ranking"])
                st.dataframe(rank_data, use_container_width=True)

            # Guardar
            auditor.save_audit(results)
            st.success("Resultados guardados en data/")

    # --- Facebook ---
    with social_tab_fb:
        st.markdown("#### Auditoría de Facebook")
        fb_pages = st.text_area(
            "Páginas de Facebook (una por línea)",
            value="samsonite.argentina\ndelsey.ar",
            height=120,
            key="fb_pages",
        )

        if st.button("Auditar Facebook", type="primary", key="btn_fb"):
            auditor = FacebookAuditor()
            page_ids = [p.strip() for p in fb_pages.strip().split("\n") if p.strip()]

            progress = st.progress(0)
            results = []
            for i, page_id in enumerate(page_ids):
                with st.spinner(f"Auditando FB/{page_id}..."):
                    result = auditor.audit_page(page_id)
                    results.append(result)
                progress.progress((i + 1) / len(page_ids))
                if i < len(page_ids) - 1:
                    time.sleep(3)

            table_data = []
            for r in results:
                table_data.append({
                    "Página": r.get("page_name") or r["page_id"],
                    "Accesible": "Si" if r.get("accessible") else "No",
                    "Followers": r.get("followers") or "-",
                    "Likes": r.get("likes") or "-",
                    "Categoría": r.get("category") or "-",
                    "Rating": r.get("rating") or "-",
                    "Verificado": "Si" if r.get("is_verified") else "-",
                    "Tienda": "Si" if r.get("has_shop") else "-",
                    "Web": r.get("website") or "-",
                })
            st.dataframe(pd.DataFrame(table_data), use_container_width=True)
            auditor.save_audit(results)
            st.success("Resultados guardados en data/")

    # --- WhatsApp ---
    with social_tab_wa:
        st.markdown("#### Check WhatsApp Business")
        wa_numbers = st.text_area(
            "Números de WhatsApp (uno por línea, con código de país)",
            value="5491112345678",
            height=120,
            key="wa_numbers",
        )

        if st.button("Verificar WhatsApp", type="primary", key="btn_wa"):
            checker = WhatsAppChecker()
            numbers = [n.strip() for n in wa_numbers.strip().split("\n") if n.strip()]

            progress = st.progress(0)
            results = []
            for i, number in enumerate(numbers):
                with st.spinner(f"Verificando {number}..."):
                    result = checker.check_number(number)
                    results.append(result)
                progress.progress((i + 1) / len(numbers))
                if i < len(numbers) - 1:
                    time.sleep(2)

            table_data = []
            for r in results:
                table_data.append({
                    "Número": r.get("clean_number", ""),
                    "WhatsApp": "Si" if r.get("has_whatsapp") else "No",
                    "Business": r.get("business_name") or "-",
                    "Catálogo": "Si" if r.get("has_catalog") else "No",
                    "Link": r.get("wa_me_url", ""),
                })
            st.dataframe(pd.DataFrame(table_data), use_container_width=True)
            checker.save_audit(results)
            st.success("Resultados guardados en data/")


# ============================
# TAB 4: Auditoría Web
# ============================
with tab_website:
    st.subheader("Auditoría de Sitios Web")

    web_urls = st.text_area(
        "URLs a auditar (una por línea)",
        value="calzalindo.com.ar\nsamsonite.com.ar",
        height=120,
        key="web_urls",
    )

    if st.button("Auditar sitios", type="primary", key="btn_web"):
        auditor = WebsiteAuditor()
        urls = [u.strip() for u in web_urls.strip().split("\n") if u.strip()]

        progress = st.progress(0)
        results = []
        for i, url in enumerate(urls):
            with st.spinner(f"Auditando {url}..."):
                result = auditor.audit(url)
                results.append(result)
            progress.progress((i + 1) / len(urls))
            if i < len(urls) - 1:
                time.sleep(3)

        # Ranking
        st.subheader("Ranking")
        comparison = auditor.compare_sites(results)
        if "ranking" in comparison:
            rank_df = pd.DataFrame(comparison["ranking"])
            st.dataframe(rank_df, use_container_width=True)

        # Detalle por sitio
        for r in results:
            domain = r.get("domain", "?")
            score = r.get("score", 0)
            with st.expander(f"{domain} — Score: {score}/100"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**SSL**")
                    ssl_info = r.get("ssl", {})
                    st.write(f"HTTPS: {'Si' if ssl_info.get('has_ssl') else 'No'}")
                    st.write(f"Válido: {'Si' if ssl_info.get('valid') else 'No'}")
                    st.write(f"Emisor: {ssl_info.get('issuer', '-')}")

                    st.markdown("**Performance**")
                    perf = r.get("performance", {})
                    st.write(f"Respuesta: {perf.get('response_time_ms', '?')}ms")
                    st.write(f"Tamaño: {perf.get('content_length_kb', '?')}KB")
                    st.write(f"GZIP: {'Si' if perf.get('has_gzip') else 'No'}")

                with col2:
                    st.markdown("**SEO**")
                    seo = r.get("seo", {})
                    st.write(f"Title: {seo.get('title', '-')[:50]}")
                    st.write(f"H1: {seo.get('h1_count', 0)} tags")
                    st.write(f"Canonical: {'Si' if seo.get('has_canonical') else 'No'}")
                    st.write(f"OG Tags: {'Si' if seo.get('has_og_tags') else 'No'}")
                    st.write(f"JSON-LD: {'Si' if seo.get('has_structured_data') else 'No'}")
                    st.write(f"Imgs sin alt: {seo.get('images_without_alt', 0)}/{seo.get('total_images', 0)}")

                    st.markdown("**Mobile**")
                    mobile = r.get("mobile", {})
                    st.write(f"Viewport: {'Si' if mobile.get('has_viewport') else 'No'}")
                    st.write(f"Responsive: {'Si' if mobile.get('has_responsive_meta') else 'No'}")

                with col3:
                    st.markdown("**Redes Sociales**")
                    social = r.get("social_links", {})
                    for network, link in social.items():
                        if link:
                            st.write(f"{network.title()}: Si")
                        else:
                            st.write(f"{network.title()}: -")

                    st.markdown("**Ecommerce**")
                    ecom = r.get("ecommerce", {})
                    st.write(f"Plataforma: {ecom.get('platform', '-')}")
                    st.write(f"Carrito: {'Si' if ecom.get('has_cart') else 'No'}")
                    st.write(f"Buscador: {'Si' if ecom.get('has_search') else 'No'}")
                    if ecom.get("payment_methods"):
                        st.write(f"Pagos: {', '.join(ecom['payment_methods'])}")

                # Issues
                issues = r.get("issues", [])
                if issues:
                    st.markdown("**Issues encontrados:**")
                    for issue in issues:
                        st.write(f"- {issue}")

                # Technologies
                techs = r.get("technologies", [])
                if techs:
                    st.markdown(f"**Tecnologías:** {', '.join(techs)}")

        auditor.save_audit(results)
        st.success("Resultados guardados en data/")


# ============================
# TAB 5: Auditoría Competidores (unificada)
# ============================
with tab_competitor:
    st.subheader("Auditoría Completa de Competidores")
    st.caption("Combiná todos los canales en un solo reporte por competidor")

    num_competitors = st.number_input("Cantidad de competidores", min_value=1, max_value=10, value=2)

    competitors = []
    for i in range(int(num_competitors)):
        with st.expander(f"Competidor {i+1}", expanded=(i == 0)):
            name = st.text_input("Nombre", key=f"comp_name_{i}", value=f"Competidor {i+1}")
            c1, c2 = st.columns(2)
            with c1:
                website = st.text_input("Website", key=f"comp_web_{i}", placeholder="ejemplo.com.ar")
                instagram = st.text_input("Instagram", key=f"comp_ig_{i}", placeholder="usuario_ig")
                ml_query = st.text_input("Búsqueda ML", key=f"comp_ml_{i}", placeholder="producto marca")
            with c2:
                facebook = st.text_input("Facebook", key=f"comp_fb_{i}", placeholder="pagina.facebook")
                whatsapp = st.text_input("WhatsApp", key=f"comp_wa_{i}", placeholder="5491112345678")

            competitors.append({
                "name": name,
                "website": website or None,
                "instagram": instagram or None,
                "facebook": facebook or None,
                "whatsapp": whatsapp or None,
                "ml_query": ml_query or None,
            })

    if st.button("Ejecutar auditoría completa", type="primary", key="btn_full_audit"):
        audit = SkillsAudit(exchange_rate=exchange_rate)

        progress = st.progress(0)
        reports = []
        for i, comp in enumerate(competitors):
            with st.spinner(f"Auditando {comp['name']}..."):
                report = audit.full_competitor_audit(**comp)
                reports.append(report)
            progress.progress((i + 1) / len(competitors))

        # Summary cards
        st.subheader("Resumen")
        cols = st.columns(len(reports))
        for col, report in zip(cols, reports):
            summary = report.get("summary", {})
            with col:
                st.markdown(f"### {report['competitor']}")
                st.metric("Score Digital", f"{summary.get('digital_presence_score', 0)}/100")
                st.write(f"Canales activos: {len(summary.get('channels_active', []))}")

                if summary.get("strengths"):
                    st.markdown("**Fortalezas:**")
                    for s in summary["strengths"][:3]:
                        st.write(f"+ {s}")

                if summary.get("weaknesses"):
                    st.markdown("**Debilidades:**")
                    for w in summary["weaknesses"][:3]:
                        st.write(f"- {w}")

        # Comparison table
        if len(reports) > 1:
            st.subheader("Comparativa")
            comp_data = []
            for r in sorted(reports, key=lambda x: x.get("summary", {}).get("digital_presence_score", 0), reverse=True):
                s = r.get("summary", {})
                comp_data.append({
                    "Competidor": r["competitor"],
                    "Score": s.get("digital_presence_score", 0),
                    "Canales": len(s.get("channels_active", [])),
                    "Faltantes": ", ".join(s.get("channels_missing", [])),
                })
            st.dataframe(pd.DataFrame(comp_data), use_container_width=True)

        # Save
        all_data = {"reports": reports, "timestamp": datetime.now().isoformat()}
        audit.save_report(all_data, "full_competitor_audit")
        st.success("Reporte guardado en data/")


# ============================
# TAB 6: Historial
# ============================
with tab_history:
    st.subheader("Scans anteriores")

    if os.path.exists(DATA_DIR):
        files = sorted(
            [f for f in os.listdir(DATA_DIR) if f.endswith(".json")],
            reverse=True,
        )

        # Filtro por tipo
        file_types = {
            "Todos": "",
            "ML Analysis": "_analysis.json",
            "Instagram": "instagram_",
            "Facebook": "facebook_",
            "WhatsApp": "whatsapp_",
            "Website": "website_",
            "Competidores": "competitor_",
            "Skills Audit": "skills_",
        }
        filter_type = st.selectbox("Filtrar por tipo", list(file_types.keys()))
        filter_str = file_types[filter_type]

        filtered = [f for f in files if filter_str in f] if filter_str else files

        if filtered:
            for f in filtered[:30]:
                try:
                    with open(os.path.join(DATA_DIR, f)) as fh:
                        data = json.load(fh)

                    # Try to get a descriptive label
                    label = data.get("query", data.get("competitor", f.rsplit("_", 2)[0]))
                    ts = data.get("timestamp", "?")[:16]

                    with st.expander(f"{ts} — {label} ({f})"):
                        st.json(data)
                except Exception:
                    with st.expander(f):
                        st.error("Error al leer el archivo")
        else:
            st.info("No hay archivos para el filtro seleccionado.")
    else:
        st.info("Directorio de datos no encontrado.")
