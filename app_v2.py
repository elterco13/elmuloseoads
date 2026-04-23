import streamlit as st
import pandas as pd
from modules.seo_analyzer import run_analysis
from modules.web_analyzer import analyze_website
import os
import json
import datetime

st.set_page_config(page_title="SEO Ads Generator PRO", page_icon="🎯", layout="wide")

st.markdown("""
    <style>
    .ad-preview { border:1px solid #dfe1e5; border-radius:8px; padding:15px; background:white; margin-bottom:12px; font-family:Arial,sans-serif; }
    .ad-url { color:#202124; font-size:13px; margin-bottom:2px; }
    .ad-badge { display:inline-block; background:#e8f0fe; color:#1a73e8; border-radius:3px; font-size:11px; padding:1px 5px; margin-right:5px; }
    .ad-title { color:#1a0dab; font-size:19px; margin-bottom:4px; }
    .ad-desc { color:#4d5156; font-size:14px; line-height:1.4; }
    .char-ok { color:#2d7d46; font-size:12px; }
    .char-warn { color:#d93025; font-size:12px; font-weight:bold; }
    .profile-card { background:#f0f7ff; border-radius:10px; padding:16px; margin-bottom:16px; border-left:4px solid #1a73e8; }
    .usp-tag { display:inline-block; background:#e6f4ea; color:#137333; border-radius:12px; padding:3px 10px; margin:2px; font-size:13px; }
    </style>
""", unsafe_allow_html=True)

if 'history' not in st.session_state:
    st.session_state.history = []
if 'prefill' not in st.session_state:
    st.session_state.prefill = {}

def load_templates():
    if os.path.exists('templates.json'):
        with open('templates.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

templates = load_templates()

def char_label(text: str, limit: int) -> str:
    n = len(text)
    css = "char-ok" if n <= limit else "char-warn"
    return f'<span class="{css}">[{n}/{limit}]</span>'

def generate_full_report(company_data: dict, results: dict) -> str:
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    es = results.get('executive_summary', {})
    tc = results.get('technical_config', {})

    md = f"""# 🏆 PLAN MAESTRO GOOGLE ADS — {company_data['name'].upper()}
**Fecha:** {date_str} | **Objetivo:** Lanzamiento Mes 1
**Herramienta:** SEO Ads Generator PRO · Powered by Gemini

---

## 📌 ESTRATEGIA Y ENFOQUE
| Parámetro | Valor |
|:---|:---|
| Zona Geográfica | {tc.get('geo_zone', '-')} |
| Radio | {tc.get('radius_km', '-')} km |
| Idiomas Activos | {', '.join(tc.get('languages', []))} |
| Puja Mes 1 | {tc.get('bidding_strategy_month1', '-')} |
| Puja Mes 2+ | {tc.get('bidding_strategy_month2', '-')} |
| Ajuste Móvil | {tc.get('mobile_bid_adjustment', '-')} |
| Horario | {tc.get('schedule', '-')} |
| Budget Diario Est. | {tc.get('daily_budget_est', '-')} {tc.get('currency', '')} |

---

## 📊 RESUMEN EJECUTIVO
| Métrica | Valor |
|:---|:---|
| Keywords Activas Totales | {es.get('total_keywords', '-')} |
| Keywords Negativas | {es.get('negative_keywords_count', '-')} |
| Volumen Total Mensual Est. | ~{es.get('total_monthly_volume', '-')} búsquedas/mes |
| CPA Estimado | {tc.get('currency','CHF')} {es.get('estimated_cpa_min','-')}–{es.get('estimated_cpa_max','-')}/cliente |
| Clientes Estimados/Mes | {es.get('estimated_clients_per_month', '-')} |
| Fee de Gestión Sugerido | €{es.get('management_fee', '-')}/mes |

---

## 📢 COPYWRITING DE ANUNCIOS (RSA)
"""
    for i, ad in enumerate(results.get('ads', [])):
        md += f"\n### Anuncio {i+1} — {ad['language'].upper()} · Focus: {ad['focus']}\n"
        md += f"**URL final:** `{company_data['url']}/{ad['path1']}/{ad['path2']}`  |  **CTA:** {ad['cta']}\n\n"
        md += "**Títulos:**\n"
        for j, t in enumerate(ad['titles']):
            n = len(t)
            flag = "⚠️" if n > 30 else ""
            md += f"{j+1}. {t} [{n}/30] {flag}\n"
        md += "\n**Descripciones:**\n"
        for j, d in enumerate(ad['descriptions']):
            n = len(d)
            flag = "⚠️" if n > 90 else ""
            md += f"{j+1}. {d} [{n}/90] {flag}\n"

    md += "\n---\n\n## 🔑 INFORME DE KEYWORDS\n"
    md += "| # | Keyword | Idioma | Vol/Mes | CPC Est. | Competencia | Match | Prioridad |\n"
    md += "|:--|:--------|:-------|:--------|:---------|:------------|:------|:----------|\n"
    for j, kw in enumerate(results.get('keywords', []), 1):
        md += f"| {j} | {kw['keyword']} | {kw['language']} | {kw['volume_est']} | {kw['cpc_est']} {kw['currency']} | {kw['competition']} | {kw['match_type']} | {kw['priority']} |\n"

    md += "\n---\n\n## 🚫 KEYWORDS NEGATIVAS\n"
    negs = results.get('negative_keywords', [])
    md += ", ".join(f"`{n}`" for n in negs) + "\n"

    md += "\n---\n\n## 🛠️ EXTENSIONES\n\n### Sitelinks\n"
    for sl in results.get('extensions', {}).get('sitelinks', []):
        md += f"- **{sl['text']}** → {sl['url']}\n"
    md += "\n### Callouts\n"
    for co in results.get('extensions', {}).get('callouts', []):
        md += f"- {co}\n"

    md += "\n---\n\n## 📱 POSTS GOOGLE BUSINESS\n"
    posts = results.get('google_business_posts', [])
    labels = ["🇩🇪 Semanas 1 y 3 (Alemán)", "🇬🇧 Semanas 2 y 4 (Inglés)"]
    for i, post in enumerate(posts):
        label = labels[i] if i < len(labels) else f"Post {i+1}"
        md += f"\n**{label}:**\n```\n{post}\n```\n"

    md += "\n---\n\n## 🏆 TOP 5 KEYWORDS POR ROI\n"
    for item in results.get('top5_roi_keywords', []):
        md += f"- {item}\n"

    md += f"\n---\n\n## 📈 ANÁLISIS DE OPORTUNIDAD\n{results.get('opportunity_analysis','')}\n"
    md += "\n---\n*Generado por SEO Ads Generator PRO · Gemini 2.5 Pro + Flash*"
    return md


# ─── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Gemini API Key", type="password", help="Obtén tu clave en Google AI Studio")
    if not api_key:
        st.warning("Introduce tu API Key para comenzar")

    st.divider()
    st.caption("🤖 **Modelos en uso:**")
    st.caption("· Pre-análisis web: `gemini-2.5-flash`")
    st.caption("· Plan Maestro Ads: `gemini-2.5-pro`")

    st.divider()
    if st.session_state.history:
        st.header("📚 Historial de sesión")
        for item in reversed(st.session_state.history[-5:]):
            time_str = item['time'].strftime("%H:%M") if isinstance(item['time'], datetime.datetime) else str(item['time'])
            st.caption(f"📄 {item['name']} · {time_str}")


# ─── MAIN UI ────────────────────────────────────────────────────────────────
st.title("🎯 SEO Ads Generator PRO")
st.markdown("Genera planes de Google Ads de nivel agencia directamente desde la web del cliente.")

# ── PASO 1: PRE-ANÁLISIS WEB ────────────────────────────────────────────────
st.subheader("Paso 1 — Análisis del Sitio Web")
st.markdown("Introduce la URL del cliente y deja que la IA extraiga toda la información relevante automáticamente.")

col_url, col_btn = st.columns([3, 1])
with col_url:
    url_input = st.text_input("URL del sitio web del cliente", placeholder="https://goldbeauty.ch", label_visibility="collapsed")
with col_btn:
    analyze_btn = st.button("🔍 Analizar Web", use_container_width=True, type="secondary")

if analyze_btn:
    if not api_key:
        st.error("Introduce la API Key en la barra lateral primero.")
    elif not url_input:
        st.error("Introduce una URL.")
    else:
        profile = analyze_website(api_key, url_input)
        if profile:
            st.session_state.prefill = profile
            st.session_state.prefill['url'] = url_input

if st.session_state.prefill:
    p = st.session_state.prefill
    st.success("✅ Perfil de negocio extraído correctamente. Revisa y edita si es necesario.")

    # Tarjeta de resumen visual
    usp_html = "".join(f'<span class="usp-tag">{u}</span>' for u in p.get('usp', []))
    services_preview = " · ".join(p.get('services', [])[:5])
    st.markdown(f"""
    <div class="profile-card">
        <strong>🏢 {p.get('business_name','')}</strong> — {p.get('category','')}<br>
        <span style="color:#5f6368">📍 {p.get('location','')} &nbsp;|&nbsp; 📞 {p.get('phone','')} &nbsp;|&nbsp; 💱 Mercado: {p.get('market_currency','')}</span><br><br>
        <strong>Servicios detectados:</strong> {services_preview}<br><br>
        {usp_html}
    </div>
    """, unsafe_allow_html=True)

    with st.expander("👁️ Ver datos completos extraídos"):
        st.json(p)

st.divider()

# ── PASO 2: FORMULARIO (pre-rellenado si hay análisis) ──────────────────────
st.subheader("Paso 2 — Confirmar Datos y Generar Plan")
st.markdown("Revisa los datos extraídos, ajusta si es necesario y genera el Plan Maestro.")

p = st.session_state.prefill
selected_template = st.selectbox("O carga una plantilla de sector", ["Ninguna"] + list(templates.keys()))
default_desc = templates[selected_template]['description'] if selected_template != "Ninguna" else p.get('suggested_description', "")
default_budget = templates[selected_template].get('budget', p.get('suggested_budget_eur', 500)) if selected_template != "Ninguna" else p.get('suggested_budget_eur', 500)

with st.form("main_form"):
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Nombre de la Empresa *", value=p.get('business_name', ''))
        category = st.text_input("Categoría de Negocio *", value=p.get('category', selected_template if selected_template != "Ninguna" else ""))
        url = st.text_input("URL del Sitio Web *", value=p.get('url', url_input if 'url_input' in dir() else ''))
    with c2:
        location = st.text_input("Ubicación Objetivo *", value=p.get('location', ''), placeholder="Ej: Zürich Bellevue, radio 2km")
        budget = st.number_input("Presupuesto Mensual (€/CHF)", min_value=50, value=int(default_budget))
        description = st.text_area(
            "Brief del cliente",
            value=default_desc,
            height=120,
            help="Pre-rellenado automáticamente. Añade detalles adicionales si los tienes."
        )

    # Mostrar servicios detectados como referencia
    if p.get('services'):
        st.info(f"🛎️ **Servicios detectados:** {', '.join(p.get('services', []))}")

    submit = st.form_submit_button("GENERAR PLAN MAESTRO 🚀", use_container_width=True)

if submit:
    if not api_key:
        st.error("Introduce la Gemini API Key en la barra lateral.")
    elif not all([name, category, url, location]):
        st.error("Rellena todos los campos obligatorios (*).")
    else:
        with st.spinner("Generando plan completo con Gemini 2.5 Pro... (30-60 segundos)"):
            results = run_analysis(api_key, {
                "name": name, "category": category, "url": url,
                "location": location, "budget": budget, "description": description
            })

        if results:
            st.session_state.history.append({"name": name, "time": datetime.datetime.now()})
            st.success("✅ Plan Maestro generado correctamente")
            st.header("📊 Dashboard de Campaña")

            t1, t2, t3, t4 = st.tabs([
                "📢 Anuncios RSA",
                "🔑 Keywords",
                "🛠️ Config. Técnica",
                "📱 Google Business"
            ])

            # ── TAB 1: ANUNCIOS ──────────────────────────────────────────
            with t1:
                for i, ad in enumerate(results.get('ads', [])):
                    with st.expander(f"Anuncio {i+1} — {ad['language']} · {ad['focus']}", expanded=(i == 0)):
                        col_l, col_r = st.columns([1, 1])
                        with col_l:
                            st.write("**Títulos** (Google muestra 3 simultáneamente):")
                            for t_text in ad['titles']:
                                n = len(t_text)
                                css = "char-ok" if n <= 30 else "char-warn"
                                st.markdown(f'<span class="{css}">[{n}/30]</span> {t_text}', unsafe_allow_html=True)
                            st.write("**Descripciones:**")
                            for d_text in ad['descriptions']:
                                n = len(d_text)
                                css = "char-ok" if n <= 90 else "char-warn"
                                st.markdown(f'<span class="{css}">[{n}/90]</span> {d_text}', unsafe_allow_html=True)
                        with col_r:
                            st.write("**Vista previa en Google:**")
                            title_preview = " | ".join(ad['titles'][:3])
                            st.markdown(f"""
                                <div class="ad-preview">
                                    <div class="ad-url"><span class="ad-badge">Anuncio</span>{url}/{ad['path1']}</div>
                                    <div class="ad-title">{title_preview}</div>
                                    <div class="ad-desc">{ad['descriptions'][0] if ad['descriptions'] else ''}</div>
                                </div>
                            """, unsafe_allow_html=True)
                            st.caption(f"CTA: **{ad.get('cta', '')}**")

            # ── TAB 2: KEYWORDS ──────────────────────────────────────────
            with t2:
                kws = results.get('keywords', [])
                if kws:
                    df_kw_inner = pd.DataFrame(kws)
                    df_de = df_kw_inner[df_kw_inner['language'] == 'DE'] if 'language' in df_kw_inner.columns else df_kw_inner
                    df_en = df_kw_inner[df_kw_inner['language'] == 'EN'] if 'language' in df_kw_inner.columns else pd.DataFrame()

                    col_de, col_en = st.columns(2)
                    with col_de:
                        st.subheader("🇩🇪 Keywords Alemán")
                        if not df_de.empty:
                            st.dataframe(df_de[['keyword','priority','volume_est','cpc_est','match_type']], use_container_width=True)
                    with col_en:
                        st.subheader("🇬🇧 Keywords Inglés")
                        if not df_en.empty:
                            st.dataframe(df_en[['keyword','priority','volume_est','cpc_est','match_type']], use_container_width=True)

                    st.subheader("🚫 Keywords Negativas")
                    negs = results.get('negative_keywords', [])
                    st.info(", ".join(negs) if negs else "No generadas")

                    st.subheader("🏆 Top 5 Keywords por ROI")
                    for item in results.get('top5_roi_keywords', []):
                        st.write(f"• {item}")

            # ── TAB 3: CONFIG TÉCNICA ────────────────────────────────────
            with t3:
                tc = results.get('technical_config', {})
                es = results.get('executive_summary', {})

                st.subheader("Resumen Ejecutivo")
                r1, r2, r3 = st.columns(3)
                r1.metric("Keywords Activas", es.get('total_keywords', '-'))
                r2.metric("Volumen Total/Mes", f"~{es.get('total_monthly_volume', '-')}")
                r3.metric("CPA Estimado", f"{tc.get('currency','€')} {es.get('estimated_cpa_min','-')}–{es.get('estimated_cpa_max','-')}")

                r4, r5, r6 = st.columns(3)
                r4.metric("Clientes Est./Mes", es.get('estimated_clients_per_month', '-'))
                r5.metric("Budget Diario", f"{tc.get('daily_budget_est','-')} {tc.get('currency','')}")
                r6.metric("Fee Gestión Sugerido", f"€{es.get('management_fee','-')}/mes")

                st.subheader("Parámetros de Campaña")
                c_t1, c_t2 = st.columns(2)
                c_t1.write(f"**Zona Geográfica:** {tc.get('geo_zone','-')}")
                c_t1.write(f"**Radio:** {tc.get('radius_km','-')} km")
                c_t1.write(f"**Idiomas:** {', '.join(tc.get('languages',[]))}")
                c_t1.write(f"**Horario:** {tc.get('schedule','-')}")
                c_t2.write(f"**Puja Mes 1:** {tc.get('bidding_strategy_month1','-')}")
                c_t2.write(f"**Puja Mes 2+:** {tc.get('bidding_strategy_month2','-')}")
                c_t2.write(f"**Ajuste Móvil:** {tc.get('mobile_bid_adjustment','-')}")

                st.subheader("Extensiones")
                col_sl, col_co = st.columns(2)
                with col_sl:
                    st.write("**Sitelinks:**")
                    for sl in results.get('extensions', {}).get('sitelinks', []):
                        st.write(f"— {sl['text']} → `{sl['url']}`")
                with col_co:
                    st.write("**Callouts:**")
                    for co in results.get('extensions', {}).get('callouts', []):
                        st.write(f"• {co}")

                st.subheader("📈 Análisis de Oportunidad")
                st.write(results.get('opportunity_analysis', ''))

            # ── TAB 4: GOOGLE BUSINESS ───────────────────────────────────
            with t4:
                posts = results.get('google_business_posts', [])
                labels = ["🇩🇪 Semanas 1 y 3 (Alemán)", "🇬🇧 Semanas 2 y 4 (Inglés)"]
                for i, post in enumerate(posts):
                    label = labels[i] if i < len(labels) else f"Post {i+1}"
                    st.subheader(label)
                    st.code(post, language=None)

            # ── DESCARGAS ────────────────────────────────────────────────
            st.divider()
            st.subheader("📥 Exportar Resultados")

            kws_all = results.get('keywords', [])
            df_kw_export = pd.DataFrame(kws_all) if kws_all else pd.DataFrame()

            col_d1, col_d2 = st.columns(2)
            if not df_kw_export.empty:
                csv_bytes = df_kw_export.to_csv(index=False).encode('utf-8')
                col_d1.download_button(
                    "📥 CSV de Keywords",
                    csv_bytes,
                    f"{name.replace(' ','_')}_keywords.csv",
                    "text/csv",
                    use_container_width=True
                )

            full_md = generate_full_report({"name": name, "category": category, "url": url, "location": location, "budget": budget}, results)
            col_d2.download_button(
                "📄 Informe Pro Completo (.md)",
                full_md.encode('utf-8'),
                f"{name.replace(' ','_')}_plan_maestro.md",
                "text/markdown",
                type="primary",
                use_container_width=True
            )
