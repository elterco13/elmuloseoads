import unicodedata

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
    return text.encode('ascii', errors='replace').decode('ascii').strip()
