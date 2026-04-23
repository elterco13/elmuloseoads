import requests
import re
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel
import json
import unicodedata

# Modelos detallados para calidad de agencia
class AdCopy(BaseModel):
    language: str
    focus: str
    titles: list[str]  # 9-15 títulos
    descriptions: list[str]  # 4 descripciones
    path1: str
    path2: str

class KeywordDetail(BaseModel):
    keyword: str
    volume_est: int
    cpc_est: float
    competition: str
    match_type: str
    priority: str

class ExtensionSet(BaseModel):
    sitelinks: list[dict]  # [{"text": "...", "url": "..."}]
    callouts: list[str]

class TechnicalConfig(BaseModel):
    geo_strategy: str
    languages: list[str]
    bidding_strategy: str
    daily_budget_est: float
    schedule: str

class SEOAnalysisResult(BaseModel):
    ads: list[AdCopy]
    keywords: list[KeywordDetail]
    negative_keywords: list[str]
    extensions: ExtensionSet
    technical_config: TechnicalConfig
    google_business_posts: list[str]
    opportunity_analysis: str
    competition_score: int

def sanitize(text: str) -> str:
    if not isinstance(text, str): return str(text)
    text = unicodedata.normalize('NFKC', text)
    return ''.join(c for c in text if unicodedata.category(c)[0] != 'C')

@st.cache_data(ttl=3600)
def google_autocomplete(query: str) -> list[str]:
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={query}"
    try:
        resp = requests.get(url, timeout=5)
        resp.encoding = 'utf-8'
        return [sanitize(s) for s in resp.json()[1] if s.lower().startswith(query.lower())][:10]
    except:
        return [f"{query} cerca de mi", f"mejor {query}"]

@st.cache_data(ttl=3600)
def scrape_basic(url: str) -> tuple[str, str]:
    if not url.startswith(('http://', 'https://')): url = 'https://' + url
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        html = resp.content.decode('utf-8', errors='ignore')
        title = re.search(r'<title[^>]*>([^<]+)', html, re.I)
        meta = re.search(r'<meta\s+name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.I)
        if not meta: meta = re.search(r'<meta\s+property=["\']og:description["\'][^>]*content=["\']([^"\']*)', html, re.I)
        return sanitize(title.group(1).strip()) if title else "Web sin titulo", sanitize(meta.group(1).strip()) if meta else "Sin meta desc"
    except:
        return "Error de lectura", "No accesible"

def run_analysis(api_key: str, company_data: dict) -> dict:
    st.info("🚀 Generando Plan Maestro de Google Ads (Calidad Agencia)...")
    progress_bar = st.progress(0)
    
    keywords_suggest = google_autocomplete(company_data['category'])
    progress_bar.progress(30)
    
    title_web, desc_web = scrape_basic(company_data['url'])
    progress_bar.progress(60)
    
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    Eres un Senior Media Buyer y Experto en Google Ads. Tu objetivo es crear un PIANO MESE 1 (Plan del Mes 1) para:
    EMPRESA: {company_data['name']}
    CATEGORIA: {company_data['category']}
    UBICACION: {company_data['location']}
    WEB: {company_data['url']}
    INFO EXTRA: {company_data['description']}
    BUDGET: {company_data['budget']}€/mes
    
    CONTEXTO WEB ACTUAL:
    Title: {title_web} | Meta: {desc_web}
    Keywords Sugeridas: {keywords_suggest}

    INSTRUCCIONES DE CALIDAD:
    1. ESTRATEGIA: Foco absoluto en la ubicacion especifica. "Maxima potencia, cero dispersion".
    2. ANUNCIOS RSA: Genera 3 variantes de anuncios (Responsive Search Ads).
       - Cada variante debe tener al menos 9 TITULOS (max 30 car.) y 3-4 DESCRIPCIONES (max 90 car.).
       - Si el negocio es internacional o en zona multilingue, adapta los anuncios a los idiomas locales.
    3. KEYWORDS: Lista detallada con Volumen, CPC est. en la moneda local, Competencia y Match Type (Phrase/Exact).
    4. NEGATIVAS: Lista de al menos 20-30 negativas categorizadas (Gratis, Empleo, Competencia, etc.).
    5. EXTENSIONES: Define Sitelinks potentes y Callouts de valor.
    6. GOOGLE BUSINESS: Escribe 2 propuestas de post para el perfil de empresa.
    7. ANALISIS ROI: Breve explicacion de por que esta estrategia funcionara.

    RESPONDE EXCLUSIVAMENTE EN JSON siguiendo el esquema SEOAnalysisResult.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SEOAnalysisResult,
                temperature=0.1,
            ),
        )
        progress_bar.progress(100)
        return json.loads(response.text)
    except Exception as e:
        st.error(f"Error critico en IA: {e}")
        return None
