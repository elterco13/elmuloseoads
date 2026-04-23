import requests
import re
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel
import json
import unicodedata


# ─── MODELOS PYDANTIC ──────────────────────────────────────────────────────────

class SEOAudit(BaseModel):
    current_health_score: int       # 1-100
    missing_elements: list[str]     # Qué le falta a la web (H1, alt tags, etc.)
    suggested_title: str            # Título SEO optimizado
    suggested_meta_desc: str        # Meta descripción optimizada
    content_gap_analysis: str       # Breve análisis de qué contenido falta para rankear

class Sitelink(BaseModel):
    text: str
    url: str

class AdCopy(BaseModel):
    language: str
    focus: str
    titles: list[str]
    descriptions: list[str]
    path1: str
    path2: str
    cta: str

class KeywordDetail(BaseModel):
    keyword: str
    language: str
    volume_est: int
    cpc_est: float
    currency: str
    competition: str
    match_type: str
    priority: str

class ExecutiveSummary(BaseModel):
    total_keywords: int
    negative_keywords_count: int
    total_monthly_volume: int
    estimated_cpa_min: float
    estimated_cpa_max: float
    estimated_clients_per_month: str
    management_fee: float

class SEOAnalysisResult(BaseModel):
    seo_audit: SEOAudit             # NUEVO: Bloque de Auditoría SEO explícito
    ads: list[AdCopy]
    keywords: list[KeywordDetail]
    negative_keywords: list[str]
    extensions: dict                # Sitelinks y Callouts
    technical_config: dict
    executive_summary: ExecutiveSummary
    google_business_posts: list[str]
    opportunity_analysis: str
    top5_roi_keywords: list[str]


# ─── UTILIDADES ────────────────────────────────────────────────────────────────

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
        return [f"{query} near me", f"best {query}"]

@st.cache_data(ttl=3600)
def scrape_basic(url: str) -> tuple[str, str]:
    if not url.startswith(('http://', 'https://')): url = 'https://' + url
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        html = resp.content.decode('utf-8', errors='ignore')
        title_m = re.search(r'<title[^>]*>([^<]+)', html, re.I)
        meta_m = re.search(r'<meta\s+name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.I)
        title = sanitize(title_m.group(1).strip()) if title_m else "Sin titulo"
        desc = sanitize(meta_m.group(1).strip()) if meta_m else "Sin meta description"
        return title, desc
    except:
        return "Error de lectura", "No accesible"


# ─── ANÁLISIS PRINCIPAL (Usa Gemini 1.5 Pro) ───────────────────────────────────

def run_analysis(api_key: str, company_data: dict) -> dict | None:
    st.info("🚀 Iniciando Motor de Inteligencia (Gemini 1.5 Pro)...")
    progress_bar = st.progress(0)

    keywords_suggest = google_autocomplete(company_data['category'])
    progress_bar.progress(20)

    title_web, desc_web = scrape_basic(company_data['url'])
    progress_bar.progress(40)

    client = genai.Client(api_key=api_key)

    prompt = f"""
Eres un Senior SEO & SEM Strategist. Tu misión es realizar un análisis 360 del negocio y generar un Plan Maestro de Google Ads.

DATOS DEL NEGOCIO:
- Nombre: {sanitize(company_data['name'])}
- Web: {sanitize(company_data['url'])} (Título actual: {title_web} | Meta: {desc_web})
- Categoría: {sanitize(company_data['category'])}
- Ubicación: {sanitize(company_data['location'])}
- Brief: {sanitize(company_data['description'])}
- Budget: {company_data['budget']} EUR/mes

TAREAS REQUERIDAS:
1. AUDITORÍA SEO: Evalúa la web actual y sugiere mejoras críticas en Title/Meta y contenido para rankear en {company_data['location']}.
2. ESTRATEGIA SEM: Genera 3 anuncios RSA multilingües (2 DE, 1 EN si es zona mixta). Máx 30 car por título, 90 car por descripción.
3. KEYWORDS: Lista de 28 keywords (DE/EN) con Vol, CPC (suizo/premium +40%) y Match Type.
4. NEGATIVAS: Lista de 30-40 negativas categorizadas.
5. RESUMEN EJECUTIVO: Métricas de éxito esperadas (CPA, Clientes, ROI).

RESPONDE EXCLUSIVAMENTE EN JSON cumpliendo el esquema SEOAnalysisResult.
"""

    try:
        # Usamos gemini-1.5-pro por su capacidad de razonamiento superior en planes complejos
        response = client.models.generate_content(
            model='gemini-1.5-pro',
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
        st.error(f"Error en Gemini 1.5 Pro: {e}")
        return None
