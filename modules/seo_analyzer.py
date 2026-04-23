import requests
import re
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel
import json

class SEOAnalysisResult(BaseModel):
    primary_keywords: list[str]
    longtail_keywords: list[str]
    competition_score: int
    recommendations: list[str]
    estimated_cpc_min: float
    estimated_cpc_max: float

@st.cache_data(ttl=3600)
def google_autocomplete(query):
    """Keywords GRATIS vía Google Suggest con cache y manejo de errores"""
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={query}"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        suggestions = resp.json()[1]
        return [s for s in suggestions if s.lower().startswith(query.lower())][:10]
    except Exception as e:
        st.warning(f"No se pudieron obtener sugerencias de Google: {e}")
        return [f"{query} ofertas", f"comprar {query}"]

@st.cache_data(ttl=3600)
def scrape_basic(url):
    """Scraping básico SIN BeautifulSoup con manejo de timeouts y errores 404"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        resp.raise_for_status()
        
        title_match = re.search(r'<title[^>]*>([^<]+)', resp.text, re.I)
        title = title_match.group(1).strip() if title_match else "Sin título"
        
        meta_match = re.search(r'<meta\s+name=["\']description["\'][^>]*content=["\']([^"\']*)', resp.text, re.I)
        if not meta_match: # Fallback to property=og:description
             meta_match = re.search(r'<meta\s+property=["\']og:description["\'][^>]*content=["\']([^"\']*)', resp.text, re.I)
        desc = meta_match.group(1).strip() if meta_match else "Sin descripción meta"
        
        return title, desc
    except requests.exceptions.RequestException as e:
        st.warning(f"Error al analizar la URL: {e}")
        return "Error de lectura", "No accesible"

def run_analysis(api_key, company_data):
    st.info("🔍 Iniciando análisis estratégico...")
    
    progress_bar = st.progress(0)
    
    # 1. Autocomplete keywords GRATIS
    st.text("Paso 1: Obteniendo tendencias de búsqueda...")
    base_query = company_data['category'].lower()
    keywords = google_autocomplete(base_query)
    progress_bar.progress(33)
    
    # 2. Scraping básico
    st.text("Paso 2: Analizando presencia web actual...")
    title, meta_desc = scrape_basic(company_data['url'])
    progress_bar.progress(66)
    
    # 3. Gemini hace el análisis inteligente
    st.text("Paso 3: Generando estrategia SEO y estimación de Costes (CPC)...")
    
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Empresa: {company_data['name']} | {company_data['category']} | {company_data['location']}
    Presupuesto: {company_data['budget']}
    Web: {company_data['url']}
    Title: {title}
    Meta: {meta_desc}
    Keywords base: {keywords}
    
    Como experto en SEM y Google Ads, analiza y ENRIQUECE esta información:
    - Prioriza las palabras clave más comerciales.
    - Sugiere 5 long tail basadas en la intención de compra.
    - Calcula un Score de competencia (0-100).
    - Basado en la ubicación y el sector, estima el Coste por Clic (CPC) mínimo y máximo esperado en euros.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SEOAnalysisResult,
                temperature=0.2,
                tools=[{"google_search": {}}],
            ),
        )
        results = json.loads(response.text)
        progress_bar.progress(100)
        st.success("¡Análisis completado!")
        return results
    except Exception as e:
        progress_bar.progress(100)
        st.error(f"Error al generar el análisis con Gemini: {e}")
        return {
            "primary_keywords": keywords[:5],
            "longtail_keywords": [f"{company_data['name']} {company_data['category']}", 
                                f"mejor {company_data['category'].lower()} {company_data['location']}"],
            "competition_score": 50,
            "estimated_cpc_min": 0.50,
            "estimated_cpc_max": 2.50,
            "recommendations": ["Optimiza title", "Añade meta desc"]
        }
