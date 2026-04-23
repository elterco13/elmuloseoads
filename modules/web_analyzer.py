import requests
import re
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel
import unicodedata
import json


# ─── MODELO DE NEGOCIO EXTRAÍDO ─────────────────────────────────────────────

class BusinessProfile(BaseModel):
    business_name: str
    category: str                    # Tipo de negocio (ej: "Coiffeur / Hair Salon")
    services: list[str]              # Lista de servicios detectados
    location: str                    # Ciudad + Barrio si aplica (ej: "Zürich Bellevue")
    address: str                     # Dirección física si está disponible
    phone: str                       # Teléfono si aparece
    website_language: list[str]      # Idiomas detectados en la web
    market_currency: str             # "CHF" | "EUR" | "GBP" | "USD"
    target_audience: str             # Descripción del público objetivo
    usp: list[str]                   # Unique Selling Points detectados (Made in Italy, 5 estrellas, etc.)
    suggested_description: str       # Descripción lista para usar como brief
    suggested_budget_eur: int        # Estimación de budget mensual en EUR para Google Ads
    detected_competitors_context: str  # Contexto de competencia (mercado local detectado)


# ─── UTILIDADES ─────────────────────────────────────────────────────────────

def sanitize(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    text = unicodedata.normalize('NFKC', text)
    return ''.join(c for c in text if unicodedata.category(c)[0] != 'C')


def _fetch_page(url: str, timeout: int = 10) -> str | None:
    """Descarga el HTML de una URL y lo devuelve como texto limpio."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()
        return resp.content.decode('utf-8', errors='ignore')
    except Exception:
        return None


def _extract_text_from_html(html: str) -> str:
    """Extrae texto útil del HTML: title, metas, headings, párrafos, listas, contacto."""
    if not html:
        return ""

    # Eliminar scripts, estilos, SVG
    html = re.sub(r'<(script|style|svg|noscript)[^>]*>.*?</\1>', '', html, flags=re.S | re.I)

    chunks = []

    # Title
    m = re.search(r'<title[^>]*>([^<]+)', html, re.I)
    if m: chunks.append(f"TITLE: {m.group(1).strip()}")

    # Meta description
    m = re.search(r'<meta\s+name=["\']description["\'][^>]*content=["\']([^"\']*)', html, re.I)
    if m: chunks.append(f"META_DESC: {m.group(1).strip()}")

    # OG tags útiles
    for prop in ['og:title', 'og:description', 'og:site_name']:
        m = re.search(rf'<meta\s+property=["\']{{prop}}["\'][^>]*content=["\']([^"\']*)', html, re.I)
        if m: chunks.append(f"{prop.upper()}: {m.group(1).strip()}")

    # Headings H1-H3
    for tag in ['h1', 'h2', 'h3']:
        for m in re.finditer(rf'<{tag}[^>]*>(.*?)</{tag}>', html, re.I | re.S):
            text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if text: chunks.append(f"{tag.upper()}: {text}")

    # Párrafos (máx. 800 chars por para, primeros 15 párrafos)
    count = 0
    for m in re.finditer(r'<p[^>]*>(.*?)</p>', html, re.I | re.S):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if len(text) > 30:
            chunks.append(f"P: {text[:200]}")
            count += 1
            if count >= 15:
                break

    # Listas (servicios suelen estar en <li>)
    count = 0
    for m in re.finditer(r'<li[^>]*>(.*?)</li>', html, re.I | re.S):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if len(text) > 10:
            chunks.append(f"LI: {text[:100]}")
            count += 1
            if count >= 20:
                break

    # Patrones de contacto en texto plano
    phone_m = re.search(r'(\+[\d\s\-\(\)]{8,20}|\b0[\d\s\-\.]{8,15})', html)
    if phone_m: chunks.append(f"PHONE: {phone_m.group(0).strip()}")

    # Schema.org JSON-LD (datos estructurados — muy ricos)
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            ld = json.loads(m.group(1))
            chunks.append(f"SCHEMA_LD: {json.dumps(ld, ensure_ascii=False)[:500]}")
        except Exception:
            pass

    return sanitize('\n'.join(chunks))[:6000]  # Límite de contexto razonable


def _get_subpages(base_url: str, html: str) -> list[str]:
    """Detecta sub-páginas relevantes (servicios, about, contacto) para enriquecer el análisis."""
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


# ─── ANÁLISIS PRINCIPAL DE WEB ──────────────────────────────────────────────

@st.cache_data(ttl=7200)
def analyze_website(api_key: str, url: str) -> dict | None:
    """
    Análisis completo del sitio web del cliente.
    Usa Gemini Flash para extracción rápida de datos de negocio.
    Devuelve un BusinessProfile dict listo para pre-rellenar el formulario.
    """
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    status = st.status("🔍 Analizando el sitio web del cliente...", expanded=True)

    with status:
        st.write("📄 Descargando página principal...")
        home_html = _fetch_page(url)
        if not home_html:
            st.error(f"No se pudo acceder a {url}. Verifica la URL.")
            return None

        home_text = _extract_text_from_html(home_html)

        # Intentar descargar sub-páginas relevantes
        subpages = _get_subpages(url, home_html)
        extra_text = ""
        for sp_url in subpages:
            st.write(f"📄 Analizando sub-página: {sp_url.replace(url,'')}")
            sp_html = _fetch_page(sp_url, timeout=8)
            if sp_html:
                extra_text += "\n---\n" + _extract_text_from_html(sp_html)

        full_context = home_text + extra_text[:3000]

        st.write("🤖 Extrayendo perfil de negocio con Gemini Flash...")

        client = genai.Client(api_key=api_key)
        prompt = f"""
Eres un experto en análisis de negocios locales y marketing digital.
Analiza el siguiente contenido extraído del sitio web de una empresa y extrae toda la información relevante para una campaña de Google Ads.

URL analizada: {url}

CONTENIDO EXTRAÍDO:
{full_context}

INSTRUCCIONES:
- Detecta el nombre real del negocio.
- Identifica la categoría principal (ej: "Hair Salon / Coiffeur", "Restaurante", "Dentista").
- Lista TODOS los servicios mencionados en el sitio.
- Detecta la ubicación (ciudad, barrio, dirección si aparece).
- Identifica los idiomas de la web para inferir el mercado objetivo.
- Detecta la moneda predominante del mercado (CHF para Suiza, EUR para España/Italia, GBP para UK).
- Identifica los USP (propuestas de valor únicas): premios, certificaciones, "made in X", años de experiencia, etc.
- Escribe una descripción de 2-3 frases del negocio, útil como brief para campañas de Ads.
- Sugiere un presupuesto mensual razonable en EUR para Google Ads según el sector y mercado detectado.
- Añade un contexto breve sobre la competencia en ese mercado local.

Devuelve SOLO JSON siguiendo el schema BusinessProfile. Sin texto fuera del JSON.
"""
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=BusinessProfile,
                    temperature=0.1,
                ),
            )
            import json as _json
            result = _json.loads(response.text)
            status.update(label="✅ Análisis de web completado", state="complete")
            return result
        except Exception as e:
            status.update(label="❌ Error en el análisis", state="error")
            st.error(f"Error en Gemini Flash: {e}")
            return None
