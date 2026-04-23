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
    .seo-score { font-size: 24px; font-weight: bold; color: #1a73e8; background: #e8f0fe; padding: 10px; border-radius: 50%; width: 60px; height: 60px; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

if 'history' not in st.session_state:
    st.session_state.history = []
if 'prefill' not in st.session_state:
    st.session_state.prefill = {}

# ─── SIDEBAR ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Gemini API Key", type="password")
    st.divider()
    st.caption("🤖 **Modelos Activos:**")
    st.caption("· Pre-análisis: `gemini-1.5-flash`")
    st.caption("· Estrategia SEO/Ads: `gemini-1.5-pro` (vía API Paga)")

# ─── MAIN UI ────────────────────────────────────────────────────────────────
st.title("🎯 SEO Ads Generator PRO")

# ── PASO 1: PRE-ANÁLISIS WEB ────────────────────────────────────────────────
st.subheader("1️⃣ Auditoría Web Inicial")
url_input = st.text_input("URL del cliente", placeholder="https://goldbeauty.ch")
if st.button("🔍 Iniciar Pre-Análisis", type="secondary"):
    if api_key and url_input:
        profile = analyze_website(api_key, url_input)
        if profile:
            st.session_state.prefill = profile
            st.session_state.prefill['url'] = url_input
    else:
        st.warning("Introduce API Key y URL.")

if st.session_state.prefill:
    p = st.session_state.prefill
    st.markdown(f"""
    <div class="profile-card">
        <strong>🏢 {p.get('business_name','')}</strong> — {p.get('category','')}<br>
        📍 {p.get('location','')} &nbsp;|&nbsp; 💱 {p.get('market_currency','')}<br>
        {' '.join(f'<span class="usp-tag">{u}</span>' for u in p.get('usp', []))}
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── PASO 2: GENERACIÓN DE PLAN ──────────────────────────────────────────────
st.subheader("2️⃣ Configuración y Generación de Plan Maestro")
p = st.session_state.prefill
with st.form("main_form"):
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Empresa", value=p.get('business_name', ''))
        url = st.text_input("URL", value=p.get('url', ''))
        location = st.text_input("Ubicación", value=p.get('location', ''))
    with c2:
        category = st.text_input("Categoría", value=p.get('category', ''))
        budget = st.number_input("Presupuesto Mensual", value=int(p.get('suggested_budget_eur', 500)))
        description = st.text_area("Brief Adicional", value=p.get('suggested_description', ''))
    
    submit = st.form_submit_button("🚀 GENERAR ANÁLISIS SEO + CAMPAÑA ADS", use_container_width=True)

if submit:
    with st.spinner("Gemini 1.5 Pro está realizando el análisis SEO profundo y redactando la campaña..."):
        results = run_analysis(api_key, {"name":name, "url":url, "location":location, "category":category, "budget":budget, "description":description})
        
        if results:
            st.session_state.history.append({"name": name, "time": datetime.datetime.now()})
            
            t0, t1, t2, t3 = st.tabs(["🔍 Auditoría SEO", "📢 Anuncios Ads", "🔑 Keywords", "🛠️ Estrategia"])
            
            with t0:
                audit = results.get('seo_audit', {})
                c_s1, c_s2 = st.columns([1, 4])
                with c_s1:
                    st.markdown(f'<div class="seo-score">{audit.get("current_health_score", 0)}</div>', unsafe_allow_html=True)
                    st.caption("SEO Health Score")
                with c_s2:
                    st.subheader("Recomendaciones de Optimización")
                    st.write(f"**Título sugerido:** {audit.get('suggested_title')}")
                    st.write(f"**Meta sugerida:** {audit.get('suggested_meta_desc')}")
                
                st.divider()
                st.write("**Elementos faltantes o mejorables:**")
                for item in audit.get('missing_elements', []): st.write(f"• {item}")
                st.info(f"**Análisis de brecha de contenido:** {audit.get('content_gap_analysis')}")

            with t1:
                for i, ad in enumerate(results.get('ads', [])):
                    with st.expander(f"Anuncio {i+1}: {ad['language']}"):
                        st.write(f"**Títulos:** {', '.join(ad['titles'])}")
                        st.write(f"**Descripciones:** {', '.join(ad['descriptions'])}")

            with t2:
                st.dataframe(pd.DataFrame(results.get('keywords', [])), use_container_width=True)
                st.write("**Negativas sugeridas:**")
                st.info(", ".join(results.get('negative_keywords', [])))

            with t3:
                st.write(f"**Estrategia:** {results.get('opportunity_analysis')}")
                st.subheader("Resumen Ejecutivo")
                st.json(results.get('executive_summary'))
