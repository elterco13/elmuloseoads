import streamlit as st
import pandas as pd
from modules.seo_analyzer import run_analysis
import os
import json
import datetime

st.set_page_config(page_title="SEO Ads Generator", page_icon="🚀", layout="wide")

# Inicializar estado de memoria de sesión (sin guardado en disco para compatibilidad Cloud)
if 'history' not in st.session_state:
    st.session_state.history = []

def save_history(data):
    st.session_state.history.append(data)

# Cargar templates
def load_templates():
    if os.path.exists('templates.json'):
        with open('templates.json', 'r') as f:
            return json.load(f)
    return {}

templates = load_templates()

# Función para generar reporte Markdown
def generate_markdown_report(company_data, results):
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    md = f"""# 🚀 Informe de Estrategia SEO y SEM
**Generado el:** {date_str}

## 🏢 Resumen del Negocio
- **Empresa:** {company_data['name']}
- **Categoría:** {company_data['category']}
- **Ubicación:** {company_data['location']}
- **Web:** {company_data['url']}
- **Presupuesto Mensual:** €{company_data['budget']}

## 📊 Evaluación de Mercado
- **Puntuación de Competencia:** {results.get('competition_score', 0)}/100
- **CPC Estimado (Mín):** €{results.get('estimated_cpc_min', 0.0):.2f}
- **CPC Estimado (Máx):** €{results.get('estimated_cpc_max', 0.0):.2f}

## 🎯 Estrategia de Palabras Clave
### Keywords Principales (High Intent)
"""
    for kw in results.get('primary_keywords', []):
        md += f"- `{kw}`\n"
        
    md += "\n### Keywords Long-tail (Nicho de Oportunidad)\n"
    for kw in results.get('longtail_keywords', []):
        md += f"- `{kw}`\n"

    md += "\n## 💡 Recomendaciones Estratégicas\n"
    for rec in results.get('recommendations', []):
        md += f"- {rec}\n"
        
    md += "\n---\n*Generado automáticamente por SEO Ads Generator V2*"
    return md

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Gemini API Key", type="password", help="Obtén tu API key en Google AI Studio")
    if not api_key:
        st.warning("⚠️ Ingresa tu API Key para continuar")
        
    st.markdown("---")
    st.header("📚 Historial de la Sesión")
    if not st.session_state.history:
        st.info("No hay campañas generadas en esta sesión.")
    else:
        for i, item in enumerate(reversed(st.session_state.history[-5:])): # Mostrar últimos 5
            st.markdown(f"**{item['company_name']}** ({item['category']})")
            st.caption(f"Keywords: {len(item['primary_keywords'])} | Competencia: {item['competition_score']}")
            st.divider()

# Main Header
st.title("🚀 SEO Ads Generator V2")
st.markdown("Genera campañas de Google Ads optimizadas con Inteligencia Artificial.")

# Template selector
col_t1, col_t2 = st.columns([1, 3])
with col_t1:
    selected_template = st.selectbox("Cargar plantilla rápida (opcional)", ["Ninguna"] + list(templates.keys()))

default_desc = ""
default_budget = 500
if selected_template != "Ninguna":
    default_desc = templates[selected_template].get("description", "")
    default_budget = templates[selected_template].get("budget", 500)

# Formulario principal
with st.form("company_data_form"):
    st.subheader("Datos del Negocio")
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("Nombre de la empresa *", placeholder="Ej: Clínica Dental San Juan")
        category = st.text_input("Categoría del negocio *", value=selected_template if selected_template != "Ninguna" else "", placeholder="Ej: Dentista, Restaurante, Ecommerce")
        url = st.text_input("URL del sitio web *", placeholder="Ej: www.misitio.com")
        
    with col2:
        location = st.text_input("Ubicación objetivo *", placeholder="Ej: Madrid, España")
        description = st.text_area("Breve descripción", value=default_desc, placeholder="Especialistas en implantes y ortodoncia invisible...")
        budget = st.number_input("Presupuesto mensual (€)", min_value=10, value=default_budget)
        
    submit_button = st.form_submit_button("Generar Campaña con Gemini 🚀")

# Ejecución
if submit_button:
    if not api_key:
        st.error("Por favor, ingresa tu Gemini API Key en la barra lateral.")
    elif not all([name, category, url, location]):
        st.error("Por favor, rellena todos los campos obligatorios marcados con *.")
    else:
        company_data = {
            "name": name,
            "category": category,
            "url": url,
            "location": location,
            "description": description,
            "budget": budget
        }
        
        with st.spinner("Procesando datos y analizando mercado..."):
            results = run_analysis(api_key, company_data)
            
            # Guardar en historial de sesión
            save_history({
                "company_name": name,
                "category": category,
                "primary_keywords": results.get('primary_keywords', []),
                "competition_score": results.get('competition_score', 0)
            })
            
            st.divider()
            st.subheader("📊 Panel de Estrategia SEO")
            
            # Row 1: Metricas
            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("Puntuación de Competencia", f"{results.get('competition_score', 0)}/100")
            col_res2.metric("CPC Mínimo Estimado", f"€{results.get('estimated_cpc_min', 0.0):.2f}")
            col_res3.metric("CPC Máximo Estimado", f"€{results.get('estimated_cpc_max', 0.0):.2f}")
            
            st.divider()
            
            # Row 2: Recomendaciones y Keywords
            col_k1, col_k2 = st.columns(2)
            with col_k1:
                st.write("🎯 **Keywords Principales (High Intent):**")
                for kw in results.get('primary_keywords', []):
                    st.markdown(f"- `{kw}`")
                    
                st.write("🔍 **Keywords Long-tail (Nicho):**")
                for kw in results.get('longtail_keywords', []):
                    st.markdown(f"- `{kw}`")
            
            with col_k2:
                st.write("💡 **Recomendaciones Estratégicas:**")
                for rec in results.get('recommendations', []):
                    st.info(rec)
                    
                # Preview Visual Mockup
                st.write("📱 **Vista Previa del Anuncio (Mockup)**")
                headline = f"Mejor {category} en {location}"[:30]
                desc_text = description[:90] if description else f"Descubre {name}, líderes en {category}."
                st.markdown(f"""
                <div style="border: 1px solid #dfe1e5; border-radius: 8px; padding: 15px; background: white; font-family: Arial, sans-serif;">
                    <div style="color: #202124; font-size: 14px; margin-bottom: 2px;"><strong>Ad</strong> · {url}</div>
                    <div style="color: #1a0dab; font-size: 20px; text-decoration: none; margin-bottom: 4px;">{headline} | {name}</div>
                    <div style="color: #4d5156; font-size: 14px; line-height: 1.4;">{desc_text} Consulta nuestras ofertas de temporada y solicita presupuesto sin compromiso.</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.divider()
            
            # Editor CSV
            st.subheader("📝 Editor de Anuncios y Descargas")
            st.write("Modifica el copy directamente en la tabla antes de exportarlo.")
            
            ads_data = []
            for kw in results.get('primary_keywords', []) + results.get('longtail_keywords', []):
                ads_data.append({
                    "Campaign": f"Search - {category} - {location}",
                    "Ad Group": kw.title(),
                    "Keyword": f"[{kw}]",
                    "Criterion Type": "Exact",
                    "Headline 1": f"Mejor {category} en {location}"[:30],
                    "Headline 2": f"{name} Oficial"[:30],
                    "Description 1": description[:90] if description else f"Descubre {name}, líderes en {category}.",
                    "Final URL": url
                })
                
            df = pd.DataFrame(ads_data)
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
            
            # Botones de descarga
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                csv = edited_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descargar CSV para Google Ads",
                    data=csv,
                    file_name=f"{name.replace(' ', '_')}_google_ads.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )
                
            with col_d2:
                md_report = generate_markdown_report(company_data, results)
                st.download_button(
                    label="📄 Descargar Informe Estratégico (.md)",
                    data=md_report.encode('utf-8'),
                    file_name=f"{name.replace(' ', '_')}_informe_seo.md",
                    mime="text/markdown",
                    use_container_width=True
                )
