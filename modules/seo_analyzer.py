import requests
import re
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel
import json
import unicodedata

class SEOAnalysisResult(BaseModel):
    primary_keywords: list[str]
    longtail_keywords: list[str]
    competition_score: int
    recommendations: list[str]
    estimated_cpc_min: float
    estimated_cpc_max: float

def sanitize(text: str) -> str:
    """Limpia caracteres problemáticos para evitar errores de encoding ASCII."""
    if not isinstance(text, str):
        return str(text)
    # Normalizar unicode (convierte ñ, tildes, etc. a formas estándar)
    text = unicodedata.normalize('NFKC', text)
    # Eliminar caracteres de control no imprimibles
    return ''.join(c for c in text if unicodedata.category(c)[0] != 'C')

@st.cache_data(ttl=3600)
def google_autocomplete(query: str) -> list[str]:
    """Keywords GRATIS vía Google Suggest con cache y manejo de errores"""
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={query}"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        suggestions = resp.json()[1]
        return [sanitize(s) for s in suggestions if s.lower().startswith(query.lower())][:10]
    except Exception as e:
        st.warning(f"No se pudieron obtener sugerencias de Google: {e}")
        return [f"{query} ofertas", f"comprar {query}"]

@st.cache_data(ttl=3600)
def scrape_basic(url: str) -> tuple[str, str]:
    """Scraping básico SIN BeautifulSoup con manejo de timeouts y errores 404"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        resp.raise_for_status()
        # Forzar decodificación UTF-8 ignorando caracteres inválidos
        html = resp.content.decode('utf-8', errors='ignore')
        
        title_match = re.search(r'<title[^>]*>([^<]+)', html, re.I)
        title = sanitize(title_match.group(1).strip()) if title_match else "Sin titulo"
        
        meta_match = re.search(r'<meta\s+name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.I)
        if not meta_match:
             meta_match = re.search(r'<meta\s+property=["\']og:description["\'][^>]*content=["\']([^"\']*)', html, re.I)
        desc = sanitize(meta_match.group(1).strip()) if meta_match else "Sin descripcion meta"
        
        return title, desc
    except requests.exceptions.RequestException as e:
        st.warning(f"Error al analizar la URL: {e}")
        return "Error de lectura", "No accesible"

def run_analysis(api_key: str, company_data: dict) -> dict:
    st.info("Iniciando analisis estrategico...")
    
    progress_bar = st.progress(0)
    
    # 1. Autocomplete keywords GRATIS
    st.text("Paso 1: Obteniendo tendencias de busqueda...")
    base_query = company_data['category'].lower()
    keywords = google_autocomplete(base_query)
    progress_bar.progress(33)
    
    # 2. Scraping básico
    st.text("Paso 2: Analizando presencia web actual...")
    title, meta_desc = scrape_basic(company_data['url'])
    progress_bar.progress(66)
    
    # 3. Gemini hace el análisis inteligente
    st.text("Paso 3: Generando estrategia SEO y estimacion de Costes (CPC)...")
    
    client = genai.Client(api_key=api_key)
    
    # Sanitizar todos los campos del prompt antes de construirlo
    s_name = sanitize(company_data['name'])
    s_category = sanitize(company_data['category'])
    s_location = sanitize(company_data['location'])
    s_budget = sanitize(str(company_data['budget']))
    s_url = sanitize(company_data['url'])
    s_title = sanitize(title)
    s_meta = sanitize(meta_desc)
    s_keywords = [sanitize(k) for k in keywords]
    
    prompt = (
        f"Empresa: {s_name} | {s_category} | {s_location}\n"
        f"Presupuesto: {s_budget}\n"
        f"Web: {s_url}\n"
        f"Title: {s_title}\n"
        f"Meta: {s_meta}\n"
        f"Keywords base: {s_keywords}\n\n"
        "Como experto en SEM y Google Ads, analiza y enriquece esta informacion:\n"
        "- Prioriza las palabras clave mas comerciales.\n"
        "- Sugiere 5 long tail basadas en la intencion de compra.\n"
        "- Calcula un Score de competencia (0-100).\n"
        "- Estima el Coste por Clic (CPC) minimo y maximo esperado en euros.\n"
    )
    
    try:
        # NOTA: google_search y response_schema no son compatibles simultáneamente.
        # Usamos solo response_schema para garantizar salida JSON estructurada.
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SEOAnalysisResult,
                temperature=0.2,
            ),
        )
        results = json.loads(response.text)
        progress_bar.progress(100)
        st.success("Analisis completado!")
        return results
    except Exception as e:
        progress_bar.progress(100)
        st.error(f"Error al generar el analisis con Gemini: {e}")
        return {
            "primary_keywords": keywords[:5],
            "longtail_keywords": [
                f"{s_name} {s_category}",
                f"mejor {s_category.lower()} {s_location}"
            ],
            "competition_score": 50,
            "estimated_cpc_min": 0.50,
            "estimated_cpc_max": 2.50,
            "recommendations": ["Optimiza title", "Añade meta desc"]
        }
