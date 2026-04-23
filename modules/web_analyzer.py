import os
import sys
import requests
import re
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel
import unicodedata
import json


# --- MODELOS PYDANTIC --------------------------------------------------------

class SeoIssue(BaseModel):
    priority: str   # "Critical" | "High" | "Medium" | "Low"
    element: str    # "Title Tag" | "Meta Description" | "H1" | "Canonical" etc.
    issue: str      # Descripcion del problema
    recommendation: str  # Accion concreta a tomar

class PageScoreCard(BaseModel):
    overall: int          # 0-100
    on_page_seo: int      # 0-100
    content_quality: int  # 0-100
    technical: int        # 0-100
    schema: int           # 0-100
    images: int           # 0-100

class BusinessProfile(BaseModel):
    business_name: str
    category: str                    # Tipo de negocio (ej: "Coiffeur / Hair Salon")
    services: list[str]              # Lista de servicios detectados
    location: str                    # Ciudad + Barrio si aplica
    address: str                     # Direccion fisica si esta disponible
    phone: str                       # Telefono si aparece
    website_language: list[str]      # Idiomas detectados en la web
    market_currency: str             # "CHF" | "EUR" | "GBP" | "USD"
    target_audience: str             # Descripcion del publico objetivo
    usp: list[str]                   # Unique Selling Points
    suggested_description: str       # Descripcion lista para usar como brief
    suggested_budget_eur: int        # Estimacion de budget mensual en EUR
    detected_competitors_context: str

    # -- SEO AUDIT -------------------------------------------------------------
    seo_score: PageScoreCard         # Puntuaciones desglosadas
    seo_issues: list[SeoIssue]       # Problemas detectados ordenados por prioridad
    title_tag: str                   # Title tag actual
    title_tag_length: int            # Caracteres del title
    meta_description: str            # Meta description actual
    meta_description_length: int     # Caracteres de la meta description
    h1_tags: list[str]               # H1 encontrados
    canonical_url: str               # Canonical si existe
    og_tags_present: bool            # OG tags detectados
    schema_types_detected: list[str] # Tipos de Schema.org encontrados
    schema_suggestions: list[str]    # Oportunidades de Schema adicionales
    images_without_alt: int          # Numero de imagenes sin alt text


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
    # NFKD decomposes: u-umlaut -> u + combining-diaeresis
    text = unicodedata.normalize('NFKD', text)
    # Drop combining marks (category M) and control chars (category C)
    text = ''.join(
        c for c in text
        if unicodedata.category(c)[0] not in ('M', 'C')
    )
    # Final ASCII encode: anything still non-ASCII becomes '?'
    return text.encode('ascii', errors='replace').decode('ascii')


def _fetch_page(url: str, timeout: int = 10) -> str | None:
    """Descarga el HTML de una URL y lo devuelve como texto."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()
        return resp.content.decode('utf-8', errors='ignore')
    except Exception:
        return None


def _extract_text_from_html(html: str) -> str:
    """Extrae texto util del HTML: title, metas, headings, parrafos, listas, contacto."""
    if not html:
        return ""

    html = re.sub(r'<(script|style|svg|noscript)[^>]*>.*?</\1>', '', html, flags=re.S | re.I)

    chunks = []

    m = re.search(r'<title[^>]*>([^<]+)', html, re.I)
    if m: chunks.append(f"TITLE: {m.group(1).strip()}")

    m = re.search(r'<meta\s+name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.I)
    if m: chunks.append(f"META_DESC: {m.group(1).strip()}")

    for prop in ['og:title', 'og:description', 'og:site_name']:
        m = re.search(rf'<meta\s+property=["\'{prop}["\'][^>]*content=["\']([^"\']*)', html, re.I)
        if m: chunks.append(f"{prop.upper()}: {m.group(1).strip()}")

    for tag in ['h1', 'h2', 'h3']:
        for m in re.finditer(rf'<{tag}[^>]*>(.*?)</{tag}>', html, re.I | re.S):
            text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if text: chunks.append(f"{tag.upper()}: {text}")

    count = 0
    for m in re.finditer(r'<p[^>]*>(.*?)</p>', html, re.I | re.S):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if len(text) > 30:
            chunks.append(f"P: {text[:200]}")
            count += 1
            if count >= 15:
                break

    count = 0
    for m in re.finditer(r'<li[^>]*>(.*?)</li>', html, re.I | re.S):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if len(text) > 10:
            chunks.append(f"LI: {text[:100]}")
            count += 1
            if count >= 20:
                break

    phone_m = re.search(r'(\+[\d\s\-\(\)]{8,20}|\b0[\d\s\-\.]{8,15})', html)
    if phone_m: chunks.append(f"PHONE: {phone_m.group(0).strip()}")

    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            ld = json.loads(m.group(1))
            # ensure_ascii=True keeps everything safe
            chunks.append(f"SCHEMA_LD: {json.dumps(ld, ensure_ascii=True)[:500]}")
        except Exception:
            pass

    # Sanitize everything to pure ASCII before returning
    return sanitize('\n'.join(chunks))[:6000]


def _extract_seo_signals(html: str) -> dict:
    """Extrae senales SEO crudas para alimentar el analisis de la skill seo_page."""
    signals = {}

    # Title tag
    m = re.search(r'<title[^>]*>([^<]+)', html, re.I)
    signals['title'] = sanitize(m.group(1).strip()) if m else ''
    signals['title_length'] = len(signals['title'])

    # Meta description
    m = re.search(r'<meta\s+name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.I)
    if not m:
        m = re.search(r'<meta\s+property=["\']og:description["\'][^>]*content=["\']([^"\']*)', html, re.I)
    signals['meta_desc'] = sanitize(m.group(1).strip()) if m else ''
    signals['meta_desc_length'] = len(signals['meta_desc'])

    # H1 tags
    h1s = []
    for m in re.finditer(r'<h1[^>]*>(.*?)</h1>', html, re.I | re.S):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if text:
            h1s.append(sanitize(text))
    signals['h1_tags'] = h1s

    # Canonical
    m = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']*)', html, re.I)
    signals['canonical'] = sanitize(m.group(1).strip()) if m else ''

    # OG tags
    og_present = bool(re.search(r'<meta\s+property=["\']og:', html, re.I))
    signals['og_tags_present'] = og_present

    # Twitter Card
    tc_present = bool(re.search(r'<meta\s+name=["\']twitter:card["\']', html, re.I))
    signals['twitter_card_present'] = tc_present

    # Schema types
    schema_types = []
    for m in re.finditer(r'"@type"\s*:\s*"([^"]+)"', html):
        t = sanitize(m.group(1))
        if t and t not in schema_types:
            schema_types.append(t)
    signals['schema_types'] = schema_types

    # Images without alt
    all_imgs = re.findall(r'<img\b[^>]*>', html, re.I)
    no_alt = sum(1 for img in all_imgs if not re.search(r'\balt\s*=\s*["\'][^"\']+["\']', img, re.I))
    signals['images_total'] = len(all_imgs)
    signals['images_no_alt'] = no_alt

    # hreflang
    signals['hreflang_present'] = bool(re.search(r'<link[^>]*hreflang', html, re.I))

    return signals


def _get_subpages(base_url: str, html: str) -> list[str]:
    """Detecta sub-paginas relevantes para enriquecer el analisis."""
    if not html:
        return []

    candidates = re.findall(r'href=["\']([^"\'#?]+)["\']', html, re.I)
    keywords = ['service', 'servic', 'about', 'uber-uns', 'nosotros', 'contact',
                'prix', 'preise', 'price', 'extension', 'braiding', 'coiffeur',
                'haircut', 'colour', 'trattament', 'menu', 'angebot']

    relevant = []
    base = base_url.rstrip('/')
    seen = set()
    for href in candidates:
        href = href.strip()
        if href.startswith('/'):
            full = base + href
        elif href.startswith('http'):
            full = href
        else:
            continue

        if full not in seen and any(k in href.lower() for k in keywords):
            relevant.append(full)
            seen.add(full)
            if len(relevant) >= 3:
                break

    return relevant


# --- ANALISIS PRINCIPAL DE WEB ------------------------------------------------

@st.cache_data(ttl=7200)
def analyze_website(api_key: str, url: str) -> dict | None:
    """
    Analisis completo del sitio web del cliente.
    - Extrae perfil de negocio (servicios, ubicacion, USPs, presupuesto)
    - Realiza auditoria SEO on-page siguiendo la metodologia seo_page skill
    Devuelve un BusinessProfile dict listo para pre-rellenar el formulario.
    """
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    status = st.status("Analizando el sitio web del cliente...", expanded=True)

    with status:
        st.write("Descargando pagina principal...")
        home_html = _fetch_page(url)
        if not home_html:
            st.error(f"No se pudo acceder a {url}. Verifica la URL.")
            return None

        home_text = _extract_text_from_html(home_html)
        seo_signals = _extract_seo_signals(home_html)

        # Intentar descargar sub-paginas relevantes
        subpages = _get_subpages(url, home_html)
        extra_text = ""
        for sp_url in subpages:
            st.write(f"Analizando sub-pagina: {sp_url.replace(url,'')}")
            sp_html = _fetch_page(sp_url, timeout=8)
            if sp_html:
                extra_text += "\n---\n" + _extract_text_from_html(sp_html)

        full_context = home_text + extra_text[:3000]

        st.write("Extrayendo perfil de negocio y auditoria SEO con Gemini Flash...")

        client = genai.Client(api_key=api_key)

        # Evaluate SEO signal status (pure ASCII labels)
        title_len = seo_signals.get('title_length', 0)
        if title_len < 30:
            title_status = '[WARNING] Too short'
        elif title_len > 60:
            title_status = '[WARNING] Too long'
        else:
            title_status = '[OK]'

        meta_desc = seo_signals.get('meta_desc', '')
        meta_len = seo_signals.get('meta_desc_length', 0)
        if not meta_desc:
            meta_status = '[WARNING] Missing'
        elif meta_len < 100:
            meta_status = '[WARNING] Too short'
        elif meta_len > 165:
            meta_status = '[WARNING] Too long'
        else:
            meta_status = '[OK]'

        # Build SEO context block (pure ASCII)
        seo_context = (
            "SEO SIGNALS DETECTED (raw extraction):\n"
            f"- Title tag: \"{seo_signals.get('title', 'NOT FOUND')}\" ({title_len} chars)\n"
            f"  Optimal range: 50-60 chars. {title_status}\n"
            f"- Meta description: \"{seo_signals.get('meta_desc', 'NOT FOUND')[:120]}\" ({meta_len} chars)\n"
            f"  Optimal range: 150-160 chars. {meta_status}\n"
            f"- H1 tags found: {seo_signals.get('h1_tags', [])} (should be exactly 1)\n"
            f"- Canonical URL: \"{seo_signals.get('canonical', 'NOT SET')}\"\n"
            f"- Open Graph tags present: {seo_signals.get('og_tags_present', False)}\n"
            f"- Twitter Card present: {seo_signals.get('twitter_card_present', False)}\n"
            f"- Schema.org types detected: {seo_signals.get('schema_types', [])}\n"
            f"- hreflang present: {seo_signals.get('hreflang_present', False)}\n"
            f"- Total images: {seo_signals.get('images_total', 0)} | Images WITHOUT alt text: {seo_signals.get('images_no_alt', 0)}\n"
        )

        prompt = (
            "You are a dual expert: (1) a business analyst for local marketing and Google Ads, and "
            "(2) a Senior SEO auditor specializing in on-page and technical SEO following Google E-E-A-T principles.\n\n"
            "Analyze the content and SEO signals extracted from this website and return a complete JSON response.\n\n"
            f"URL analyzed: {sanitize(url)}\n\n"
            "WEBSITE CONTENT:\n"
            f"{full_context}\n\n"
            f"{seo_context}\n\n"
            "YOUR TASKS:\n"
            "=== PART 1: BUSINESS PROFILE ===\n"
            "- Detect the real business name, category, all services mentioned, location, address, phone.\n"
            "- Detect website languages to infer target market.\n"
            "- Detect the market currency (CHF for Switzerland, EUR for Spain/Italy, GBP for UK).\n"
            "- Identify USPs (unique selling points): awards, certifications, made in X, years of experience.\n"
            "- Write a 2-3 sentence business description useful as an Ads brief.\n"
            "- Suggest a realistic monthly Google Ads budget in EUR for the sector and market.\n"
            "- Add brief context about local competition.\n"
            "- Set target_audience to a specific description of who this business serves.\n\n"
            "=== PART 2: SEO AUDIT (following seo_page methodology) ===\n"
            "SCORING (0-100 each):\n"
            "- on_page_seo: evaluate title tag length (50-60 ideal), meta description (150-160 ideal), H1 (exactly 1), URL structure, heading hierarchy.\n"
            "- content_quality: assess E-E-A-T signals, keyword usage, content depth from what is visible, readability.\n"
            "- technical: canonical tag, meta robots, OG tags (og:title, og:description, og:image, og:url), Twitter Card, hreflang if multilingual.\n"
            "- schema: evaluate detected schema types, required properties, missing opportunities. NEVER recommend HowTo or FAQ schemas.\n"
            "- images: alt text coverage, flag if images_no_alt > 0.\n"
            "- overall: weighted average of the above.\n\n"
            "SEO ISSUES: List all detected issues ordered by priority (Critical > High > Medium > Low):\n"
            "- Critical: missing H1, no title tag, no meta description, blocking canonical issue\n"
            "- High: title too short/long, meta desc too short/long, missing OG tags, no schema, images without alt\n"
            "- Medium: missing Twitter Card, missing hreflang (if multilingual site), weak E-E-A-T signals\n"
            "- Low: minor optimizations\n\n"
            "SCHEMA SUGGESTIONS: Recommend 2-3 relevant schema types NOT yet present (e.g. LocalBusiness, Service, Review, BreadcrumbList).\n\n"
            "Return ALL fields in the BusinessProfile schema. Use the raw SEO signals provided above as your primary data source for the SEO audit section.\n"
            "Return ONLY valid JSON matching the schema. No text outside the JSON.\n"
        )

        try:
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite-preview',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=BusinessProfile,
                    temperature=0.1,
                ),
            )
            result = json.loads(response.text)
            status.update(label="Analisis web y auditoria SEO completados", state="complete")
            return result
        except Exception as e:
            status.update(label="Error en el analisis", state="error")
            st.error(f"Error en Gemini Flash: {e}")
            return None
