import requests
import re
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel
import json
import unicodedata


# ─── MODELOS PYDANTIC ──────────────────────────────────────────────────────────

class Sitelink(BaseModel):
    text: str
    url: str

class AdCopy(BaseModel):
    language: str          # "Deutsch" | "English" | "Italiano"
    focus: str             # "Coiffeur" | "Servicios Específicos" | etc.
    titles: list[str]      # 9 títulos, max 30 chars c/u
    descriptions: list[str]  # 4 descripciones, max 90 chars c/u
    path1: str             # Fragmento URL ej: "coiffeur-zurich"
    path2: str             # Fragmento URL ej: "bellevue"
    cta: str               # "Jetzt Buchen" | "Book Now" | etc.

class KeywordDetail(BaseModel):
    keyword: str
    language: str          # "DE" | "EN"
    volume_est: int
    cpc_est: float
    currency: str          # "CHF" | "EUR" | etc.
    competition: str       # "Alta" | "Media" | "Baja"
    match_type: str        # "Exact" | "Phrase" | "Broad"
    priority: str          # "🔴 Crítica" | "🟠 Alta" | "🟢 Oportunidad"

class ExtensionSet(BaseModel):
    sitelinks: list[Sitelink]   # FIX: Sitelink tipado, no dict genérico
    callouts: list[str]

class TechnicalConfig(BaseModel):
    geo_zone: str               # "Zürich Bellevue — radio 2 km"
    radius_km: float
    languages: list[str]
    bidding_strategy_month1: str
    bidding_strategy_month2: str
    mobile_bid_adjustment: str
    daily_budget_est: float
    currency: str
    schedule: str

class ExecutiveSummary(BaseModel):
    total_keywords: int
    negative_keywords_count: int
    total_monthly_volume: int
    estimated_cpa_min: float
    estimated_cpa_max: float
    estimated_clients_per_month: str
    management_fee: float

class SEOAnalysisResult(BaseModel):
    ads: list[AdCopy]
    keywords: list[KeywordDetail]
    negative_keywords: list[str]
    extensions: ExtensionSet
    technical_config: TechnicalConfig
    executive_summary: ExecutiveSummary
    google_business_posts: list[str]   # 2 posts: DE y EN alternativos
    opportunity_analysis: str
    top5_roi_keywords: list[str]       # Las 5 mejores por ROI, con justificación


# ─── UTILIDADES ────────────────────────────────────────────────────────────────

def sanitize(text: str) -> str:
    """Normaliza unicode y elimina caracteres de control para evitar errores ASCII."""
    if not isinstance(text, str):
        return str(text)
    text = unicodedata.normalize('NFKC', text)
    return ''.join(c for c in text if unicodedata.category(c)[0] != 'C')


@st.cache_data(ttl=3600)
def google_autocomplete(query: str) -> list[str]:
    """Keywords gratuitas vía Google Suggest."""
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={query}"
    try:
        resp = requests.get(url, timeout=5)
        resp.encoding = 'utf-8'
        return [sanitize(s) for s in resp.json()[1] if s.lower().startswith(query.lower())][:10]
    except Exception:
        return [f"{query} near me", f"best {query}"]


@st.cache_data(ttl=3600)
def scrape_basic(url: str) -> tuple[str, str]:
    """Extrae title y meta description de la web del cliente."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        html = resp.content.decode('utf-8', errors='ignore')
        title_m = re.search(r'<title[^>]*>([^<]+)', html, re.I)
        meta_m = re.search(r'<meta\s+name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.I)
        if not meta_m:
            meta_m = re.search(r'<meta\s+property=["\']og:description["\'][^>]*content=["\']([^"\']*)', html, re.I)
        title = sanitize(title_m.group(1).strip()) if title_m else "Sin titulo"
        desc = sanitize(meta_m.group(1).strip()) if meta_m else "Sin meta description"
        return title, desc
    except Exception:
        return "Error de lectura", "No accesible"


# ─── ANÁLISIS PRINCIPAL ────────────────────────────────────────────────────────

def run_analysis(api_key: str, company_data: dict) -> dict | None:
    st.info("🚀 Generando Plan Maestro de Google Ads (Nivel Agencia)...")
    progress_bar = st.progress(0)

    keywords_suggest = google_autocomplete(company_data['category'])
    progress_bar.progress(25)

    title_web, desc_web = scrape_basic(company_data['url'])
    progress_bar.progress(50)

    client = genai.Client(api_key=api_key)

    # Prompt de Nivel Agencia SEM Senior
    prompt = f"""
Eres un Senior Media Buyer especialista en Google Ads con 10 años de experiencia en mercados de habla alemana y anglófona (Suiza, Alemania, Austria, UK).
Tu tarea es crear un PIANO MESE 1 (Plan del Mes 1) completo y listo para activar en Google Ads.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATOS DEL CLIENTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Empresa: {sanitize(company_data['name'])}
Categoría de negocio: {sanitize(company_data['category'])}
Ubicación exacta: {sanitize(company_data['location'])}
URL del sitio: {sanitize(company_data['url'])}
Descripción / Brief del cliente: {sanitize(company_data['description'])}
Presupuesto mensual: {company_data['budget']} EUR/mes
Title web actual: {title_web}
Meta description actual: {desc_web}
Keywords sugeridas por Google: {keywords_suggest}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRINCIPIO ESTRATÉGICO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"Máxima potencia, cero dispersión." Toda la energía concentrada en la zona exacta.
Si el negocio es local (barrio, calle), ajusta el radio geográfico a 1-2 km.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUCCIONES DE ENTREGA — SIGUE EXACTAMENTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ANUNCIOS RSA (Responsive Search Ads):
   - Genera EXACTAMENTE 3 anuncios.
   - Si la zona es multilingüe (ej: Suiza), usa: 2 anuncios en alemán + 1 en inglés.
   - Cada anuncio debe tener EXACTAMENTE 9 títulos, MÁXIMO 30 caracteres cada uno.
   - Cada anuncio debe tener EXACTAMENTE 4 descripciones, MÁXIMO 90 caracteres cada una.
   - Los títulos deben incluir: keyword principal + nombre de marca + zona geográfica + CTA.
   - Incluye en los títulos frases de diferenciación: "5-Sterne", "Made in Italy", "Premium", etc.
   - El path1 y path2 deben ser cortos y descriptivos (ej: "coiffeur-zurich" / "bellevue").

2. KEYWORDS (obligatorio 14 DE + 14 EN si el mercado es bilingüe, o 28 en el idioma principal):
   - Incluye: keyword, idioma (DE/EN), volume_est, cpc_est en moneda local, currency, competition, match_type, priority.
   - Prioridades: 🔴 Crítica (alto vol+intent), 🟠 Alta (medio vol, bajo CPC), 🟢 Oportunidad (nicho, baja competencia).
   - Match types: "Exact" para keywords geolocales, "Phrase" para keywords genéricas de alto volumen.
   - NUNCA incluyas keywords genéricas sin modificador de ubicación para negocios locales.
   - Calcula CPC con +40% sobre media global si el mercado es suizo o premium.

3. KEYWORDS NEGATIVAS (mínimo 30):
   - Categoriza por intención: gratis/price, empleo, producto (no servicio), zona incorrecta, plataformas competencia, intención informacional.

4. EXTENSIONES:
   - Sitelinks: 4 sitelinks con texto y URL específica.
   - Callouts: 6-8 callouts cortos de valor.

5. CONFIGURACIÓN TÉCNICA:
   - Estrategia de puja mes 1: Maximizar clics.
   - Estrategia de puja mes 2+: Maximizar conversiones.
   - Incluye ajuste de puja móvil (+20% recomendado).
   - Horario: Lun-Sab 08:00-20:00 típico para servicios locales premium.

6. RESUMEN EJECUTIVO:
   - Total keywords activas, keywords negativas, volumen total mensual estimado.
   - CPA estimado (min-max), clientes estimados por mes, fee de gestión sugerido.

7. POSTS GOOGLE BUSINESS:
   - 2 posts: uno en alemán (semanas 1 y 3) y uno en inglés (semanas 2 y 4).
   - Incluir emojis, hashtags, dirección física y CTA con enlace.

8. ANÁLISIS DE OPORTUNIDAD:
   - Compara alemán vs inglés (volumen, CPC, competencia, público).
   - Justifica la estrategia elegida.

9. TOP 5 KEYWORDS ROI:
   - Lista las 5 mejores keywords por retorno potencial con justificación breve.

RESPONDE ÚNICAMENTE CON EL JSON ESTRUCTURADO. Sin texto fuera del JSON.
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
        progress_bar.progress(100)
        st.error(f"Error en la generación con Gemini: {e}")
        return None
