import streamlit as st
import pandas as pd
from modules.seo_analyzer import run_analysis
import os
import json
import datetime

st.set_page_config(page_title="SEO Ads Generator PRO", page_icon="🎯", layout="wide")

# Estilos CSS personalizados para el reporte y previsualización
st.markdown("""
    <style>
    .ad-preview { border: 1px solid #dfe1e5; border-radius: 8px; padding: 15px; background: white; margin-bottom: 10px; }
    .ad-url { color: #202124; font-size: 13px; }
    .ad-title { color: #1a0dab; font-size: 18px; text-decoration: none; }
    .ad-desc { color: #4d5156; font-size: 14px; }
    .metric-card { background: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #007bff; }
    </style>
""", unsafe_allow_html=True)

if 'history' not in st.session_state:
    st.session_state.history = []

def load_templates():
    if os.path.exists('templates.json'):
        with open('templates.json', 'r') as f: return json.load(f)
    return {}

templates = load_templates()

def generate_full_report(company_data, results):
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    md = f"""# 🏆 PLAN MAESTRO GOOGLE ADS: {company_data['name'].upper()}
**Fecha:** {date_str} | **Objetivo:** Lanzamiento Mes 1

## 📌 ESTRATEGIA Y ENFOQUE
- **Ubicación:** {company_data['location']}
- **Estrategia Geográfica:** {results['technical_config']['geo_strategy']}
- **Presupuesto Diario:** {results['technical_config']['daily_budget_est']}€
- **Puja:** {results['technical_config']['bidding_strategy']}

## 📢 COPYWRITING DE ANUNCIOS (RSA)
"""
    for i, ad in enumerate(results['ads']):
        md += f"### Anuncio {i+1} - Focus: {ad['focus']} ({ad['language']})\n"
        md += "**Títulos Sugeridos:**\n"
        for t in ad['titles']: md += f"- {t}\n"
        md += "\n**Descripciones:**\n"
        for d in ad['descriptions']: md += f"- {d}\n"
        md += f"\n**URL Final:** {company_data['url']}/{ad['path1']}\n\n"

    md += "## 🔑 KEYWORDS - INFORME DETALLADO\n"
    md += "| Keyword | Vol/Mes | CPC Est. | Competencia | Match |\n"
    md += "| :--- | :--- | :--- | :--- | :--- |\n"
    for kw in results['keywords']:
        md += f"| {kw['keyword']} | {kw['volume_est']} | {kw['cpc_est']}€ | {kw['competition']} | {kw['match_type']} |\n"

    md += "\n## 🚫 KEYWORDS NEGATIVAS\n"
    md += ", ".join(results['negative_keywords']) + "\n"

    md += "\n## 🛠️ EXTENSIONES Y OTROS\n"
    md += "**Sitelinks:**\n"
    for sl in results['extensions']['sitelinks']: md += f"- {sl['text']} ({sl['url']})\n"
    md += "\n**Callouts:**\n"
    for co in results['extensions']['callouts']: md += f"- {co}\n"

    md += f"\n## 📈 ANÁLISIS DE OPORTUNIDAD\n{results['opportunity_analysis']}\n"
    md += "\n---\n*Generado por SEO Ads Generator PRO*"
    return md

# UI SIDEBAR
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    if st.session_state.history:
        st.header("📚 Historial")
        for item in reversed(st.session_state.history[-5:]):
            st.button(f"📄 {item['name']}", key=f"hist_{item['time']}")

# MAIN UI
st.title("🎯 SEO Ads Generator PRO")
st.markdown("Genera planes de Google Ads de nivel agencia en segundos.")

selected_template = st.selectbox("Cargar plantilla de sector", ["Ninguna"] + list(templates.keys()))
default_desc = templates[selected_template]['description'] if selected_template != "Ninguna" else ""

with st.form("main_form"):
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Nombre de la Empresa *")
        category = st.text_input("Categoría de Negocio *", value=selected_template if selected_template != "Ninguna" else "")
        url = st.text_input("URL del Sitio Web *")
    with c2:
        location = st.text_input("Ubicación Objetivo *", placeholder="Ej: Zürich Bellevue, raggio 2km")
        budget = st.number_input("Presupuesto Mensual (€)", min_value=10, value=500)
        description = st.text_area("Breve descripción / Brief", value=default_desc)
    submit = st.form_submit_button("GENERAR PLAN MAESTRO 🚀")

if submit:
    if not api_key or not all([name, category, url, location]):
        st.error("Rellena todos los campos y la API Key.")
    else:
        with st.spinner("Nuestra IA Senior está analizando el mercado y redactando los anuncios..."):
            results = run_analysis(api_key, {"name":name, "category":category, "url":url, "location":location, "budget":budget, "description":description})
            
            if results:
                st.session_state.history.append({"name": name, "time": datetime.datetime.now()})
                
                # DASHBOARD DE RESULTADOS
                st.header("📊 Resultado del Análisis")
                
                t1, t2, t3 = st.tabs(["📢 Anuncios y Copy", "🔑 Keywords y Negativas", "🛠️ Configuración y Estrategia"])
                
                with t1:
                    st.subheader("Anuncios Responsive Search Ads (RSA)")
                    for i, ad in enumerate(results['ads']):
                        with st.expander(f"Anuncio {i+1}: {ad['focus']} ({ad['language']})", expanded=True):
                            col_a, col_b = st.columns([1, 1])
                            with col_a:
                                st.write("**Títulos Sugeridos:**")
                                for t in ad['titles']: st.text(f"[{len(t)}/30] {t}")
                            with col_b:
                                st.write("**Vista Previa Google:**")
                                st.markdown(f"""
                                    <div class="ad-preview">
                                        <div class="ad-url">Ad · {url}/{ad['path1']}</div>
                                        <div class="ad-title">{ad['titles'][0]} | {ad['titles'][1]}</div>
                                        <div class="ad-desc">{ad['descriptions'][0]}</div>
                                    </div>
                                """, unsafe_allow_html=True)
                
                with t2:
                    col_k1, col_k2 = st.columns([2, 1])
                    with col_k1:
                        st.subheader("Plan de Keywords")
                        df_kw = pd.DataFrame(results['keywords'])
                        st.dataframe(df_kw, use_container_width=True)
                    with col_k2:
                        st.subheader("Keywords Negativas")
                        st.info(", ".join(results['negative_keywords']))

                with t3:
                    st.subheader("Configuración Técnica")
                    c_t1, c_t2 = st.columns(2)
                    c_t1.write(f"**Geo:** {results['technical_config']['geo_strategy']}")
                    c_t1.write(f"**Horario:** {results['technical_config']['schedule']}")
                    c_t2.write(f"**Estrategia de Puja:** {results['technical_config']['bidding_strategy']}")
                    c_t2.write(f"**Presupuesto Diario Sugerido:** {results['technical_config']['daily_budget_est']}€")
                    
                    st.subheader("Post Google Business")
                    for post in results['google_business_posts']:
                        st.code(post)

                st.divider()
                
                # DESCARGAS
                st.subheader("📥 Exportar Resultados")
                col_d1, col_d2 = st.columns(2)
                
                # CSV Export (Simplificado a las keywords)
                csv = df_kw.to_csv(index=False).encode('utf-8')
                col_d1.download_button("📥 Descargar CSV de Keywords", csv, f"{name}_keywords.csv", "text/csv", use_container_width=True)
                
                # MD Report Export
                full_md = generate_full_report({"name":name, "category":category, "url":url, "location":location, "budget":budget}, results)
                col_d2.download_button("📄 Descargar Informe Pro (.md)", full_md.encode('utf-8'), f"{name}_plan_ads.md", "text/markdown", type="primary", use_container_width=True)
