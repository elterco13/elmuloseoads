"""
modules/html_report.py
Generador de informes HTML nativo de estilo "Agencia Premium".
Construye HTML directamente desde los datos JSON, sin pasar por Markdown.
"""

import datetime
import html as html_lib


def _e(text) -> str:
    """Escapa texto para HTML de forma segura."""
    return html_lib.escape(str(text)) if text else ""


def _css() -> str:
    return """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

      :root {
        --blue:    #1a73e8;
        --blue-dk: #1557b0;
        --green:   #137333;
        --red:     #c5221f;
        --orange:  #e37400;
        --gray-50: #f8f9fa;
        --gray-100:#f1f3f4;
        --gray-200:#e8eaed;
        --gray-500:#80868b;
        --gray-800:#202124;
        --white:   #ffffff;
        --radius:  10px;
        --shadow:  0 2px 12px rgba(0,0,0,.08);
      }

      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

      body {
        font-family: 'Inter', 'Segoe UI', sans-serif;
        background: var(--gray-50);
        color: var(--gray-800);
        font-size: 14px;
        line-height: 1.6;
      }

      /* ── COVER ────────────────────────────────── */
      .cover {
        background: linear-gradient(135deg, #0d47a1 0%, #1a73e8 60%, #42a5f5 100%);
        color: #fff;
        padding: 60px 48px 48px;
      }
      .cover-badge {
        display: inline-block;
        background: rgba(255,255,255,.18);
        border: 1px solid rgba(255,255,255,.35);
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: .08em;
        text-transform: uppercase;
        padding: 4px 14px;
        margin-bottom: 20px;
      }
      .cover h1 { font-size: 36px; font-weight: 700; line-height: 1.2; margin-bottom: 10px; }
      .cover-meta { font-size: 13px; opacity: .85; margin-top: 20px; }
      .cover-meta span { margin-right: 28px; }

      /* ── LAYOUT ───────────────────────────────── */
      .container { max-width: 960px; margin: 0 auto; padding: 40px 24px 80px; }

      /* ── SECTION TITLES ───────────────────────── */
      .section-title {
        font-size: 18px; font-weight: 700;
        color: var(--blue-dk);
        padding-bottom: 8px;
        border-bottom: 3px solid var(--blue);
        margin: 40px 0 20px;
      }
      .subsection-title {
        font-size: 14px; font-weight: 600;
        color: var(--gray-800);
        margin: 24px 0 10px;
      }

      /* ── CARDS ────────────────────────────────── */
      .card {
        background: var(--white);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        padding: 24px;
        margin-bottom: 20px;
      }

      /* ── KPI STRIP ────────────────────────────── */
      .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 16px;
        margin-bottom: 20px;
      }
      .kpi {
        background: var(--white);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        padding: 20px 16px;
        text-align: center;
      }
      .kpi-value { font-size: 28px; font-weight: 700; color: var(--blue); line-height: 1; }
      .kpi-label { font-size: 11px; color: var(--gray-500); margin-top: 6px; text-transform: uppercase; letter-spacing: .06em; }

      /* ── TABLES ───────────────────────────────── */
      table { width: 100%; border-collapse: collapse; font-size: 13px; }
      thead th {
        background: var(--gray-100);
        color: var(--gray-500);
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: .06em;
        padding: 10px 12px;
        text-align: left;
        border-bottom: 2px solid var(--gray-200);
      }
      tbody tr { border-bottom: 1px solid var(--gray-200); }
      tbody tr:last-child { border-bottom: none; }
      tbody td { padding: 10px 12px; vertical-align: top; }
      tbody tr:hover { background: var(--gray-50); }

      /* ── BADGES ───────────────────────────────── */
      .badge {
        display: inline-block;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 8px;
        white-space: nowrap;
      }
      .badge-blue   { background:#e8f0fe; color:#1a73e8; }
      .badge-green  { background:#e6f4ea; color:#137333; }
      .badge-orange { background:#fef7e0; color:#b06000; }
      .badge-red    { background:#fce8e6; color:#c5221f; }
      .badge-gray   { background:#f1f3f4; color:#5f6368; }

      /* ── AD PREVIEW ───────────────────────────── */
      .ad-card { border: 1px solid var(--gray-200); border-radius: var(--radius); padding: 20px; margin-bottom: 16px; }
      .ad-card-header {
        display: flex; align-items: center; gap: 10px;
        font-size: 12px; color: var(--gray-500);
        margin-bottom: 14px;
      }
      .ad-url { color: var(--gray-800); font-size: 13px; margin-bottom: 6px; }
      .ad-title { color: #1a0dab; font-size: 19px; font-weight: 400; margin-bottom: 4px; line-height: 1.3; }
      .ad-desc  { color: #4d5156; font-size: 14px; }
      .title-row { display: flex; justify-content: space-between; align-items: center; padding: 5px 0; border-bottom: 1px solid var(--gray-200); font-size: 13px; }
      .char-ok   { font-size: 11px; color: var(--green); font-weight: 600; }
      .char-warn { font-size: 11px; color: var(--red);   font-weight: 600; }

      /* ── NEGATIVE KWS ─────────────────────────── */
      .neg-grid { display: flex; flex-wrap: wrap; gap: 6px; }
      .neg-tag {
        background: var(--gray-100);
        border: 1px solid var(--gray-200);
        border-radius: 4px;
        font-size: 12px;
        font-family: monospace;
        padding: 2px 8px;
        color: var(--gray-800);
      }

      /* ── PRIORITY TABLE COLORS ────────────────── */
      td.p-critical { color: var(--red);    font-weight: 600; }
      td.p-high     { color: var(--orange); font-weight: 600; }
      td.p-opp      { color: var(--blue);   font-weight: 600; }

      /* ── CHECKLIST ────────────────────────────── */
      .checklist { list-style: none; }
      .checklist li { padding: 7px 0; border-bottom: 1px solid var(--gray-200); font-size: 13px; display: flex; align-items: center; gap: 10px; }
      .checklist li::before { content: '☐'; font-size: 16px; color: var(--blue); flex-shrink: 0; }
      .checklist li:last-child { border-bottom: none; }

      /* ── POST BLOCK ───────────────────────────── */
      .post-block {
        background: var(--gray-100);
        border-radius: 8px;
        padding: 16px;
        font-family: monospace;
        font-size: 13px;
        white-space: pre-wrap;
        margin-bottom: 12px;
      }

      /* ── PLAYBOOK ─────────────────────────────── */
      .playbook-col { padding: 16px 0; }
      .playbook-step { padding: 7px 0; border-bottom: 1px solid var(--gray-200); font-size: 13px; display: flex; gap: 10px; }
      .playbook-num { background: var(--blue); color: #fff; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; flex-shrink: 0; margin-top: 2px; }

      /* ── FOOTER ───────────────────────────────── */
      .footer {
        text-align: center;
        font-size: 12px;
        color: var(--gray-500);
        border-top: 1px solid var(--gray-200);
        padding-top: 20px;
        margin-top: 60px;
      }
      .footer strong { color: var(--blue); }
    </style>
    """


def generate_html_report(company_data: dict, results: dict) -> str:
    """
    Genera un informe HTML completo de estilo agencia premium.
    Construido 100% en Python nativo, sin Markdown como intermediario.
    """
    name        = _e(company_data.get("name", "Cliente"))
    url         = _e(company_data.get("url", ""))
    location    = _e(company_data.get("location", ""))
    budget      = _e(company_data.get("budget", ""))
    date_str    = datetime.datetime.now().strftime("%Y-%m-%d")

    es = results.get("executive_summary", {})
    tc = results.get("technical_config", {})
    currency = _e(tc.get("currency", "EUR"))

    # ── COVER ─────────────────────────────────────────────────────────────
    cover = f"""
    <div class="cover">
      <div class="cover-badge">Plan Maestro Google Ads</div>
      <h1>{name}</h1>
      <div style="font-size:15px;opacity:.9;margin-top:8px;">{location}</div>
      <div class="cover-meta">
        <span>📅 {date_str}</span>
        <span>💰 Budget: {budget} {currency}/mes</span>
        <span>🌐 {url}</span>
      </div>
    </div>
    """

    # ── KPIs ───────────────────────────────────────────────────────────────
    kpis_html = f"""
    <h2 class="section-title">Resumen Ejecutivo</h2>
    <div class="kpi-grid">
      <div class="kpi"><div class="kpi-value">{_e(es.get('total_keywords','-'))}</div><div class="kpi-label">Keywords Activas</div></div>
      <div class="kpi"><div class="kpi-value">~{_e(es.get('total_monthly_volume','-'))}</div><div class="kpi-label">Búsquedas / Mes</div></div>
      <div class="kpi"><div class="kpi-value">{currency} {_e(es.get('estimated_cpa_min','-'))}-{_e(es.get('estimated_cpa_max','-'))}</div><div class="kpi-label">CPA Estimado</div></div>
      <div class="kpi"><div class="kpi-value">{_e(es.get('estimated_clients_per_month','-'))}</div><div class="kpi-label">Clientes Est./Mes</div></div>
      <div class="kpi"><div class="kpi-value">{_e(es.get('estimated_roas','-'))}</div><div class="kpi-label">ROAS Est. (Mes 2+)</div></div>
      <div class="kpi"><div class="kpi-value">{_e(es.get('management_fee','-'))}</div><div class="kpi-label">Fee Gestión / Mes</div></div>
    </div>
    """

    # ── CONFIG TÉCNICA ─────────────────────────────────────────────────────
    config_rows = [
        ("Zona Geográfica",   tc.get("geo_zone", "-")),
        ("Radio",             f"{tc.get('radius_km', '-')} km"),
        ("Idiomas",           ", ".join(tc.get("languages", []))),
        ("Puja Mes 1",        tc.get("bidding_strategy_month1", "-")),
        ("Puja Mes 2+",       tc.get("bidding_strategy_month2", "-")),
        ("Ajuste Móvil",      tc.get("mobile_bid_adjustment", "-")),
        ("Horario",           tc.get("schedule", "-")),
        ("Budget Diario Est.",f"{tc.get('daily_budget_est', '-')} {currency}"),
        ("Split Testing",     tc.get("budget_split_testing", "-")),
        ("Conv. Tracking",    tc.get("conversion_tracking_note", "-")),
    ]
    config_rows_html = "".join(
        f"<tr><td style='font-weight:600;width:220px'>{_e(k)}</td><td>{_e(v)}</td></tr>"
        for k, v in config_rows
    )
    config_section = f"""
    <h2 class="section-title">Estrategia &amp; Configuración Técnica</h2>
    <div class="card">
      <table><tbody>{config_rows_html}</tbody></table>
    </div>
    """

    # ── ADS RSA ────────────────────────────────────────────────────────────
    ads_html = "<h2 class=\"section-title\">Copywriting de Anuncios RSA</h2>"
    for i, ad in enumerate(results.get("ads", [])):
        lang   = _e(ad.get("language", ""))
        focus  = _e(ad.get("focus", ""))
        fw     = _e(ad.get("copy_framework", ""))
        cname  = _e(ad.get("campaign_name", ""))
        path1  = _e(ad.get("path1", ""))
        path2  = _e(ad.get("path2", ""))
        cta    = _e(ad.get("cta", ""))

        titles_rows = ""
        for t in ad.get("titles", []):
            n = len(t)
            cls = "char-ok" if n <= 30 else "char-warn"
            titles_rows += f'<div class="title-row"><span>{_e(t)}</span><span class="{cls}">[{n}/30]</span></div>'

        desc_rows = ""
        for d in ad.get("descriptions", []):
            n = len(d)
            cls = "char-ok" if n <= 90 else "char-warn"
            desc_rows += f'<div class="title-row"><span>{_e(d)}</span><span class="{cls}">[{n}/90]</span></div>'

        title_preview = " | ".join(ad.get("titles", [])[:3])
        desc_preview  = ad.get("descriptions", [""])[0]

        ads_html += f"""
        <div class="ad-card">
          <div class="ad-card-header">
            <span class="badge badge-blue">Anuncio {i+1}</span>
            <span class="badge badge-gray">{lang}</span>
            <span class="badge badge-green">{fw}</span>
            <span style="margin-left:auto;font-size:11px;">{cname}</span>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
            <div>
              <div class="subsection-title">Títulos</div>
              {titles_rows}
              <div class="subsection-title" style="margin-top:16px;">Descripciones</div>
              {desc_rows}
              <div style="margin-top:12px;font-size:12px;color:#5f6368;">
                <strong>URL:</strong> {url}/{path1}/{path2} &nbsp;&nbsp; <strong>CTA:</strong> {cta}
              </div>
            </div>
            <div>
              <div class="subsection-title">Vista Previa Google</div>
              <div style="border:1px solid #dfe1e5;border-radius:8px;padding:16px;background:#fff;">
                <div class="ad-url">
                  <span class="badge badge-gray" style="font-size:10px;margin-right:4px;">Anuncio</span>
                  {url}/{path1}
                </div>
                <div class="ad-title">{_e(title_preview)}</div>
                <div class="ad-desc">{_e(desc_preview)}</div>
              </div>
              <div style="margin-top:10px;font-size:12px;">
                <strong>Focus:</strong> {focus}<br>
                <strong>Framework:</strong> {fw}
              </div>
            </div>
          </div>
        </div>
        """

    # ── KEYWORDS ───────────────────────────────────────────────────────────
    priority_class = {"Critical": "p-critical", "High": "p-high", "Opportunity": "p-opp"}
    kw_rows = ""
    for j, kw in enumerate(results.get("keywords", []), 1):
        pcls = priority_class.get(kw.get("priority", ""), "")
        kw_rows += f"""
        <tr>
          <td style="color:#5f6368">{j}</td>
          <td style="font-weight:500">{_e(kw.get('keyword',''))}</td>
          <td><span class="badge badge-gray">{_e(kw.get('language',''))}</span></td>
          <td>{_e(kw.get('volume_est',''))}</td>
          <td>{_e(kw.get('cpc_est',''))} {_e(kw.get('currency',''))}</td>
          <td>{_e(kw.get('competition',''))}</td>
          <td><span class="badge badge-blue">{_e(kw.get('match_type',''))}</span></td>
          <td><span class="badge badge-gray">{_e(kw.get('intent',''))}</span></td>
          <td class="{pcls}">{_e(kw.get('priority',''))}</td>
        </tr>
        """

    kw_section = f"""
    <h2 class="section-title">Informe de Keywords</h2>
    <div class="card" style="overflow-x:auto;">
      <table>
        <thead><tr>
          <th>#</th><th>Keyword</th><th>Idioma</th>
          <th>Vol/Mes</th><th>CPC Est.</th><th>Competencia</th>
          <th>Match</th><th>Intent</th><th>Prioridad</th>
        </tr></thead>
        <tbody>{kw_rows}</tbody>
      </table>
    </div>
    """

    # ── NEGATIVAS ──────────────────────────────────────────────────────────
    negs = results.get("negative_keywords", [])
    neg_tags = "".join(f'<span class="neg-tag">{_e(n)}</span>' for n in negs)
    neg_section = f"""
    <h2 class="section-title">Keywords Negativas ({len(negs)})</h2>
    <div class="card"><div class="neg-grid">{neg_tags}</div></div>
    """

    # ── EXTENSIONES ────────────────────────────────────────────────────────
    ext = results.get("extensions", {})
    sitelinks_rows = "".join(
        f"<tr><td style='font-weight:600'>{_e(sl.get('text',''))}</td><td>{_e(sl.get('url',''))}</td></tr>"
        for sl in ext.get("sitelinks", [])
    )
    callouts_html = "".join(
        f'<span class="badge badge-blue" style="margin:3px;">{_e(co)}</span>'
        for co in ext.get("callouts", [])
    )
    snippets_html = "".join(
        f'<span class="badge badge-green" style="margin:3px;">{_e(ss)}</span>'
        for ss in ext.get("structured_snippets", [])
    )
    ext_section = f"""
    <h2 class="section-title">Extensiones</h2>
    <div class="card">
      <div class="subsection-title">Sitelinks</div>
      <table><tbody>{sitelinks_rows}</tbody></table>
      <div class="subsection-title" style="margin-top:20px;">Callouts</div>
      <div>{callouts_html}</div>
      <div class="subsection-title" style="margin-top:16px;">Structured Snippets</div>
      <div>{snippets_html}</div>
    </div>
    """

    # ── TOP 5 ROI ──────────────────────────────────────────────────────────
    top5 = results.get("top5_roi_keywords", [])
    top5_rows = "".join(
        f'<div class="playbook-step"><div class="playbook-num">{i+1}</div><div>{_e(item)}</div></div>'
        for i, item in enumerate(top5)
    )
    top5_section = f"""
    <h2 class="section-title">Top 5 Keywords por ROI</h2>
    <div class="card">{top5_rows}</div>
    """

    # ── OPORTUNIDAD ────────────────────────────────────────────────────────
    opp_section = f"""
    <h2 class="section-title">Análisis de Oportunidad</h2>
    <div class="card" style="font-size:13px;line-height:1.8;">{_e(results.get('opportunity_analysis',''))}</div>
    """

    # ── PLAYBOOK ───────────────────────────────────────────────────────────
    pb = results.get("optimization_playbook", {})
    def _pb_steps(items):
        return "".join(
            f'<div class="playbook-step"><div class="playbook-num">{i+1}</div><div>{_e(s)}</div></div>'
            for i, s in enumerate(items)
        )
    playbook_section = f"""
    <h2 class="section-title">Optimization Playbook</h2>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
      <div class="card">
        <div class="subsection-title" style="margin-top:0">Si el CPA es muy alto</div>
        {_pb_steps(pb.get('if_cpa_too_high', []))}
      </div>
      <div class="card">
        <div class="subsection-title" style="margin-top:0">Si el CTR es bajo</div>
        {_pb_steps(pb.get('if_ctr_too_low', []))}
      </div>
    </div>
    <div class="card">
      <div class="subsection-title" style="margin-top:0">Checklist Semanal</div>
      <ul class="checklist">
        {''.join(f'<li>{_e(item)}</li>' for item in pb.get('weekly_checklist', []))}
      </ul>
    </div>
    """

    # ── SETUP CHECKLIST ────────────────────────────────────────────────────
    setup = results.get("setup_checklist", [])
    setup_section = f"""
    <h2 class="section-title">Setup Checklist Google Ads</h2>
    <div class="card">
      <ul class="checklist">
        {''.join(f'<li>{_e(item)}</li>' for item in setup)}
      </ul>
    </div>
    """

    # ── GOOGLE BUSINESS POSTS ──────────────────────────────────────────────
    posts = results.get("google_business_posts", [])
    labels = ["Semanas 1 y 3 (Alemán)", "Semanas 2 y 4 (Inglés)"]
    posts_html = ""
    for i, post in enumerate(posts):
        lbl = labels[i] if i < len(labels) else f"Post {i+1}"
        posts_html += f"""
        <div class="subsection-title">{_e(lbl)}</div>
        <div class="post-block">{_e(post)}</div>
        """
    posts_section = f"""
    <h2 class="section-title">Posts Google Business</h2>
    <div class="card">{posts_html}</div>
    """

    # ── FOOTER ─────────────────────────────────────────────────────────────
    footer = f"""
    <div class="footer">
      Generado por <strong>SEO Ads Generator PRO</strong> &mdash; Powered by Gemini &mdash; {date_str}
    </div>
    """

    # ── ENSAMBLAJE FINAL ───────────────────────────────────────────────────
    body = (
        kpis_html
        + config_section
        + ads_html
        + kw_section
        + neg_section
        + ext_section
        + top5_section
        + opp_section
        + playbook_section
        + setup_section
        + posts_section
        + footer
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Plan Maestro Google Ads - {name}</title>
  {_css()}
</head>
<body>
  {cover}
  <div class="container">
    {body}
  </div>
</body>
</html>"""
