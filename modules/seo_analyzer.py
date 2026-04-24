import os
import sys
import requests
import re
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel
from . import logger_utils
from .utils import sanitize
import json
import unicodedata


# --- MODELOS PYDANTIC ---------------------------------------------------------

class Sitelink(BaseModel):
    text: str
    url: str

class AdCopy(BaseModel):
    language: str          # "Deutsch" | "English" | "Italiano"
    focus: str             # "Coiffeur" | "Hair Extensions" etc.
    campaign_name: str     # Naming convention: GOOG_Search_[Audience]_[Offer]_M1
    titles: list[str]      # 9 titles, max 30 chars each
    descriptions: list[str]  # 4 descriptions, max 90 chars each
    path1: str             # URL fragment e.g. "coiffeur-zurich"
    path2: str             # URL fragment e.g. "bellevue"
    cta: str               # "Jetzt Buchen" | "Book Now" | etc.
    copy_framework: str    # "PAS" | "BAB" | "Social Proof" -- framework used for copy

class KeywordDetail(BaseModel):
    keyword: str
    language: str          # "DE" | "EN"
    volume_est: int
    cpc_est: float
    currency: str          # "CHF" | "EUR" etc.
    competition: str       # "Alta" | "Media" | "Baja"
    match_type: str        # "Exact" | "Phrase" | "Broad"
    priority: str          # "Critical" | "High" | "Opportunity"
    intent: str            # "Transactional" | "Commercial" | "Informational"

class ExtensionSet(BaseModel):
    sitelinks: list[Sitelink]
    callouts: list[str]
    structured_snippets: list[str]   # e.g. "Services: Hair Extensions, Coiffeur, Braiding"

class TechnicalConfig(BaseModel):
    geo_zone: str
    radius_km: float
    languages: list[str]
    bidding_strategy_month1: str     # "Maximize Clicks" (learning phase)
    bidding_strategy_month2: str     # "Maximize Conversions / Target CPA"
    mobile_bid_adjustment: str
    daily_budget_est: float
    currency: str
    schedule: str
    budget_split_testing: str        # "70% proven campaigns / 30% testing" framing
    conversion_tracking_note: str    # Reminder: must install tag before launch

class ExecutiveSummary(BaseModel):
    total_keywords: int
    negative_keywords_count: int
    total_monthly_volume: int
    estimated_cpa_min: float
    estimated_cpa_max: float
    estimated_clients_per_month: str
    management_fee: float
    estimated_roas: str              # Estimated ROAS range for month 2+
    quality_score_target: str        # Target Quality Score range (e.g. "7-9/10")

class OptimizationPlaybook(BaseModel):
    if_cpa_too_high: list[str]       # Ordered action list from paid_ads skill
    if_ctr_too_low: list[str]        # Ordered action list
    weekly_checklist: list[str]      # Weekly review items

class SEOAnalysisResult(BaseModel):
    ads: list[AdCopy]
    keywords: list[KeywordDetail]
    negative_keywords: list[str]
    extensions: ExtensionSet
    technical_config: TechnicalConfig
    executive_summary: ExecutiveSummary
    google_business_posts: list[str]
    opportunity_analysis: str
    top5_roi_keywords: list[str]
    optimization_playbook: OptimizationPlaybook
    setup_checklist: list[str]


# --- UTILIDADES ---------------------------------------------------------------

def sanitize(text: str) -> str:
    """Convierte texto a ASCII puro eliminando diacriticos y caracteres problematicos.

    Pipeline:
    1. NFKD descompone caracteres combinados (u + dieresis).
    2. Filtra categorias 'M' (combining marks) y 'C' (control chars).
    3. Encode ASCII con replace como red final.
    """
    if not isinstance(text, str):
        text = str(text)
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(
        c for c in text
        if unicodedata.category(c)[0] not in ('M', 'C')
    )
    return text.encode('ascii', errors='replace').decode('ascii')


@st.cache_data(ttl=3600)
def google_autocomplete(query: str) -> list[str]:
    """Keywords gratuitas via Google Suggest."""
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={query}"
    try:
        logger_utils.info(f"Google Suggest query: {query}")
        resp = requests.get(url, timeout=5)
        resp.encoding = 'utf-8'
        results = [sanitize(s) for s in resp.json()[1] if s.lower().startswith(query.lower())][:10]
        logger_utils.info(f"Google Suggest returned {len(results)} results")
        return results
    except Exception as e:
        logger_utils.warn(f"Google Suggest failed: {e}")
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
        logger_utils.info(f"Basic scrape of {url} successful: {title[:30]}...")
        return title, desc
    except Exception as e:
        logger_utils.warn(f"Basic scrape of {url} failed: {e}")
        return "Error de lectura", "No accesible"


# --- ANALISIS PRINCIPAL -------------------------------------------------------

def run_analysis(api_key: str, model_name: str, company_data: dict) -> dict | None:
    st.info("Generando Plan Maestro de Google Ads (Nivel Agencia)...")
    progress_bar = st.progress(0)

    keywords_suggest = google_autocomplete(company_data['category'])
    progress_bar.progress(25)

    title_web, desc_web = scrape_basic(company_data['url'])
    progress_bar.progress(50)

    # Use raw API Key (sanitization corrupts the key)
    client = genai.Client(api_key=api_key.strip())

    prompt = (
        "You are a Senior Performance Marketing Strategist with 10+ years experience in German-speaking markets "
        "(Switzerland, Germany, Austria) and English-speaking premium markets.\n\n"
        "You combine two expert roles:\n"
        "1. Google Ads Senior Media Buyer -- you create high-performance RSA campaigns ready to activate.\n"
        "2. Paid Ads Strategist -- you follow proven frameworks for ad copy, bid strategies, and campaign structure.\n\n"
        "========================================\n"
        "CLIENT DATA\n"
        "========================================\n"
        f"Company: {sanitize(company_data['name'])}\n"
        f"Business category: {sanitize(company_data['category'])}\n"
        f"Target location: {sanitize(company_data['location'])}\n"
        f"Website URL: {sanitize(company_data['url'])}\n"
        f"Client brief: {sanitize(company_data['description'])}\n"
        f"Monthly budget: {company_data['budget']} EUR/month\n"
        f"Website title: {title_web}\n"
        f"Website meta description: {desc_web}\n"
        f"Google Suggest keywords: {keywords_suggest}\n\n"
        "========================================\n"
        "STRATEGIC PRINCIPLE\n"
        "========================================\n"
        "\"Maximum power, zero dispersion.\" Concentrate all energy in the exact target zone.\n"
        "For local businesses: tighten geo radius to 1-2 km. Never waste impressions outside the target area.\n\n"
        "========================================\n"
        "PAID ADS METHODOLOGY -- FOLLOW THESE FRAMEWORKS\n"
        "========================================\n\n"
        "COPY FRAMEWORKS (use the best fit per ad):\n"
        "  - PAS (Problem-Agitate-Solve): State the search pain -> agitate it -> present the service as solution -> CTA\n"
        "  - BAB (Before-After-Bridge): Current painful state -> desired result -> your service as the bridge\n"
        "  - Social Proof Lead: Lead with a compelling stat or result -> what you do -> CTA\n\n"
        "HEADLINE FORMULAS for Search Ads:\n"
        "  - [Keyword] + [Benefit]: e.g. \"Coiffeur Zurich Bellevue\"\n"
        "  - [Action] + [Outcome]: e.g. \"Buchen & Jetzt Strahlen\"\n"
        "  - [Question]: e.g. \"Suchen Sie einen Coiffeur?\"\n"
        "  - [Number] + [Benefit]: e.g. \"5-Sterne Salon Bellevue\"\n"
        "  STRICT: Every title MUST be 30 characters or less. Count every character including spaces.\n\n"
        "CTA VARIATIONS:\n"
        "  - Conversion CTAs: \"Jetzt Buchen\", \"Book Now\", \"Termin Sichern\", \"Get Your Look\"\n"
        "  - Soft CTAs (awareness): \"Mehr Erfahren\", \"Learn More\"\n"
        "  - Urgency (only if genuine): \"Limited Slots\", \"Nur 3 Platze Frei\"\n\n"
        "CAMPAIGN NAMING CONVENTION (use in campaign_name field):\n"
        "  GOOG_Search_[TargetAudience]_[ServiceFocus]_M1\n"
        "  Example: GOOG_Search_ZurichBellevue_Coiffeur_M1\n\n"
        "BUDGET ALLOCATION FRAMEWORK:\n"
        "  Month 1 (testing phase): 70% to proven/safe keywords, 30% to new audience tests.\n"
        "  State this in budget_split_testing field.\n\n"
        "========================================\n"
        "DELIVERY INSTRUCTIONS -- FOLLOW EXACTLY\n"
        "========================================\n\n"
        "1. RSA ADS -- EXACTLY 3 ads:\n"
        "   - Multilingual markets (Switzerland): 2 ads in German + 1 in English.\n"
        "   - EXACTLY 9 titles per ad, MAXIMUM 30 characters each (spaces count!).\n"
        "   - EXACTLY 4 descriptions per ad, MAXIMUM 90 characters each.\n"
        "   - Titles must cover: primary keyword + brand name + geo zone + CTA + differentiator.\n"
        "   - Include differentiators in titles: \"5-Sterne\", \"Made in Italy\", \"Premium\", \"Zertifiziert\".\n"
        "   - path1 and path2: short, descriptive (e.g. \"coiffeur-zurich\" / \"bellevue\").\n"
        "   - Assign copy_framework field: which framework was used (PAS / BAB / Social Proof).\n\n"
        "2. KEYWORDS -- 14 DE + 14 EN for bilingual markets (or 28 in primary language):\n"
        "   - Include: keyword, language (DE/EN), volume_est, cpc_est in local currency, currency,\n"
        "     competition, match_type, priority, AND intent (Transactional/Commercial/Informational).\n"
        "   - Priorities: Critical (high vol+intent), High (medium vol, low CPC), Opportunity (niche).\n"
        "   - Match types: \"Exact\" for geo-local keywords, \"Phrase\" for high-volume generics.\n"
        "   - NEVER include generic keywords without a location modifier for local businesses.\n"
        "   - Swiss/premium market: add +40% to global average CPC.\n"
        "   - Focus on TRANSACTIONAL and COMMERCIAL intent keywords for Month 1 (bottom of funnel).\n\n"
        "3. NEGATIVE KEYWORDS -- minimum 30:\n"
        "   Categorize by intent: free/price-hunters, employment seekers, wrong product (not service),\n"
        "   wrong zone, competitor platforms, purely informational intent, DIY intent.\n\n"
        "4. EXTENSIONS:\n"
        "   - Sitelinks: 4 with text and specific URL.\n"
        "   - Callouts: 6-8 short value callouts.\n"
        "   - Structured snippets: 1-2 relevant snippets (e.g. \"Services: Hair Extensions, Coiffeur, Braiding\").\n\n"
        "5. TECHNICAL CONFIG:\n"
        "   - Month 1 bidding: \"Maximize Clicks\" (learning phase, no conversion data yet).\n"
        "   - Month 2+ bidding: \"Maximize Conversions\" (once 50+ conversions are tracked).\n"
        "   - Mobile bid adjustment: +20% recommended for local service businesses.\n"
        "   - Schedule: Mon-Sat 08:00-20:00 typical for premium local services.\n"
        "   - budget_split_testing: \"70% proven / 30% testing (Month 1 framework)\".\n"
        "   - conversion_tracking_note: Remind that conversion tracking MUST be installed and tested before launch.\n\n"
        "6. EXECUTIVE SUMMARY:\n"
        "   - Total active keywords, negative keywords count, total monthly estimated volume.\n"
        "   - Estimated CPA (min-max), estimated clients per month, suggested management fee.\n"
        "   - estimated_roas: realistic ROAS range for Month 2+ once optimization kicks in.\n"
        "   - quality_score_target: target Quality Score range to aim for (e.g. \"7-9/10\").\n\n"
        "7. GOOGLE BUSINESS POSTS -- 2 posts:\n"
        "   - Post 1: German (Weeks 1 & 3) -- include hashtags, address, CTA with link.\n"
        "   - Post 2: English (Weeks 2 & 4) -- same structure.\n\n"
        "8. OPPORTUNITY ANALYSIS:\n"
        "   - Compare DE vs EN: volume, CPC, competition, audience type.\n"
        "   - Justify the chosen strategy and budget split between languages.\n"
        "   - Note any seasonal patterns or local market specifics.\n\n"
        "9. TOP 5 ROI KEYWORDS:\n"
        "   - List the 5 best keywords by potential ROI with brief justification.\n\n"
        "10. OPTIMIZATION PLAYBOOK (based on paid_ads best practices):\n"
        "    - if_cpa_too_high: ordered action list (check landing page -> tighten audience -> test new copy -> adjust bid strategy).\n"
        "    - if_ctr_too_low: ordered action list (test new hooks -> check audience match -> refresh creative -> improve offer).\n"
        "    - weekly_checklist: 7-item weekly review checklist (spend pacing, CPA vs target, top/bottom ads, frequency, landing page CVR, disapproved ads, audience insights).\n\n"
        "11. SETUP CHECKLIST:\n"
        "    List the Google Ads launch checklist items (conversion tracking, GA4 link, audience lists, negative keyword lists, ad extensions, brand campaign, location/language targeting, ad schedule).\n\n"
        "RESPOND ONLY WITH VALID JSON. No text outside the JSON block.\n"
    )

    try:
        logger_utils.info(f"Sending Master Plan prompt to Gemini ({model_name}). Size: {len(prompt)} chars")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SEOAnalysisResult,
                temperature=0.1,
                http_options={
                    'headers': {
                        'User-Agent': 'SEO-Ads-Generator-Pro/1.0 (ASCII-Safe)',
                        'x-goog-api-client': 'gl-python/3.14.0' # Force clean ASCII header
                    }
                }
            ),
        )
        logger_utils.info("Gemini response received. Parsing JSON...")
        result = json.loads(response.text)
        logger_utils.info("Master Plan JSON parsed successfully")
        progress_bar.progress(100)
        return result
    except Exception as e:
        logger_utils.error(f"Gemini API or Parsing error: {e}", exc_info=True)
        progress_bar.progress(100)
        st.error(f"Error en la generacion con Gemini: {e}")
        return None
