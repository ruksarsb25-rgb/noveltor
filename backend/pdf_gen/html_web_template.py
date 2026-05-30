"""
JATS Editor-style web HTML template.
Layout: left TOC sidebar | main article content | right tab panels.
"""
import html as _html
import re

NAVY = "#0F3557"
NAVY_LIGHT = "#E8F0FB"


def _e(s) -> str:
    return _html.escape(str(s or ""), quote=False)


_URL_RE      = re.compile(r'(https?://[^\s<>"\')\]]+)', re.IGNORECASE)
_CITE_RE     = re.compile(r'\[([\d,\s–—-]+)\]')
_SUB_SUP_RE  = re.compile(r'&lt;(/?(?:sub|sup))&gt;', re.IGNORECASE)


def _linkify(text: str) -> str:
    parts = _URL_RE.split(str(text or ""))
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            out.append(_e_fmt(part))
        else:
            clean = part.rstrip(".,;")
            tail  = part[len(clean):]
            url   = _html.escape(clean, quote=True)
            out.append(f'<a href="{url}" target="_blank" rel="noreferrer" style="color:{NAVY};">{_html.escape(clean, quote=False)}</a>')
            if tail:
                out.append(_html.escape(tail, quote=False))
    return "".join(out)


def _citify(text: str) -> str:
    def replace_bracket(m):
        inner = m.group(1)
        nums = []
        for part in re.split(r',', inner):
            part = part.strip()
            range_match = re.match(r'(\d+)\s*[–—-]\s*(\d+)', part)
            if range_match:
                nums.extend(range(int(range_match.group(1)), int(range_match.group(2)) + 1))
            elif re.match(r'^\d+$', part):
                nums.append(int(part))
        linked = ','.join(f'<a href="#ref-{n}" style="color:{NAVY};">{n}</a>' for n in nums)
        return f'[{linked}]'
    return _CITE_RE.sub(replace_bracket, text)


def _e_fmt(s) -> str:
    """HTML-escape but restore <sub>/<sup> tags produced by the parser."""
    return _SUB_SUP_RE.sub(r'<\1>', _html.escape(str(s or ""), quote=False))


def _render_content_blocks(content: list) -> str:
    html = ""
    for block in content:
        btype = block.get("type")
        if btype == "paragraph":
            text = (block.get("text") or "").strip()
            if text:
                html += f'<p class="body-text">{_citify(_linkify(text))}</p>'
        elif btype == "equation":
            uri = block.get("data_uri", "")
            if uri:
                html += f'<div class="equation"><img src="{uri}" alt="equation" style="max-height:60px;"/></div>'
        elif btype == "table":
            html += _render_table(block)
        elif btype == "figure":
            html += _render_figure(block)
    return html


def _render_figure(fig: dict) -> str:
    label   = _e_fmt(fig.get("label") or "Figure")
    caption = _e_fmt(fig.get("caption") or "")
    data_uri = fig.get("data_uri") or ""
    fig_id   = _e(fig.get("id") or "")
    img_html = (f'<img src="{data_uri}" alt="{label}" style="max-width:100%;border-radius:4px;"/>'
                if data_uri else f'<div class="fig-placeholder">[{label}]</div>')
    cap_html = f'<div class="fig-caption"><strong>{label}.</strong> {caption}</div>' if caption else \
               f'<div class="fig-caption"><strong>{label}</strong></div>'
    return f'<div class="figure-block" id="{fig_id}">{img_html}{cap_html}</div>'


def _render_table(tbl: dict) -> str:
    label   = _e(tbl.get("caption") or tbl.get("label") or "")
    headers = tbl.get("headers") or []
    rows    = tbl.get("rows") or []
    tbl_id  = _e(tbl.get("id") or "")
    t = f'<div class="table-block" id="{tbl_id}">'
    if label:
        t += f'<div class="table-label">{label}</div>'
    t += '<div class="table-scroll"><table class="data-table">'
    if headers:
        t += "<thead><tr>" + "".join(f"<th>{_citify(_linkify(h))}</th>" for h in headers) + "</tr></thead>"
    if rows:
        t += "<tbody>"
        for ri, row in enumerate(rows):
            cls = ' class="even"' if ri % 2 else ""
            t += f"<tr{cls}>" + "".join(f"<td>{_citify(_linkify(c))}</td>" for c in row) + "</tr>"
        t += "</tbody>"
    t += "</table></div></div>"
    return t


def _collect_figures(article: dict) -> list:
    figs = []
    for sec in article.get("sections") or []:
        for block in sec.get("content") or []:
            if block.get("type") == "figure":
                figs.append(block)
        for sub in sec.get("subsections") or []:
            for block in sub.get("content") or []:
                if block.get("type") == "figure":
                    figs.append(block)
    return figs


def _collect_tables(article: dict) -> list:
    tbls = []
    for sec in article.get("sections") or []:
        for block in sec.get("content") or []:
            if block.get("type") == "table":
                tbls.append(block)
        for sub in sec.get("subsections") or []:
            for block in sub.get("content") or []:
                if block.get("type") == "table":
                    tbls.append(block)
    return tbls


def build_web_html(article: dict) -> str:
    title       = _e_fmt(article.get("title") or "Untitled")
    abstract    = article.get("abstract") or ""
    keywords    = article.get("keywords") or []
    sections    = article.get("sections") or []
    references  = article.get("references") or []
    authors     = article.get("authors") or []
    doi         = article.get("doi") or ""
    journal     = _e(article.get("journal_name") or "")
    issn_online = _e(article.get("issn_online") or "")
    issn_print  = _e(article.get("issn_print") or "")
    publisher   = _e(article.get("publisher_name") or "")
    received    = _e(article.get("received_date") or "")
    accepted    = _e(article.get("accepted_date") or "")
    published   = _e(article.get("published_date") or "")
    journal_logo = article.get("journal_logo") or ""
    brand_logo   = article.get("brand_logo") or ""

    # ── Table of Contents ────────────────────────────────────────────────────
    toc_items = []
    toc_items.append('<li><a href="#article-title">Article Title</a></li>')
    toc_items.append('<li><a href="#authors">Authors</a></li>')
    toc_items.append('<li><a href="#abstract">Abstract</a></li>')
    for sec in sections:
        heading = sec.get("heading") or ""
        sec_id  = re.sub(r'\W+', '-', heading).strip('-').lower()
        toc_items.append(f'<li class="toc-sec"><a href="#{sec_id}">{_e_fmt(heading)}</a></li>')
        for sub in sec.get("subsections") or []:
            sub_heading = sub.get("heading") or ""
            sub_id = re.sub(r'\W+', '-', sub_heading).strip('-').lower()
            toc_items.append(f'<li class="toc-sub"><a href="#{sub_id}">{_e_fmt(sub_heading)}</a></li>')
    toc_html = "<ul>" + "".join(toc_items) + "</ul>"

    # ── Authors block ────────────────────────────────────────────────────────
    # Build affiliation index
    affil_list = []
    affil_map  = {}
    for a in authors:
        aff = (a.get("affiliation") or "").strip()
        if aff and aff not in affil_map:
            affil_map[aff] = len(affil_list) + 1
            affil_list.append(aff)

    author_names = []
    for a in authors:
        name = f"{a.get('first_name','')} {a.get('last_name','')}".strip()
        aff  = (a.get("affiliation") or "").strip()
        sup  = f"<sup>{affil_map[aff]}</sup>" if aff and aff in affil_map else ""
        corr = '<sup>✉</sup>' if a.get("corresponding") else ""
        orcid_html = ""
        if a.get("orcid"):
            orcid_html = f' <a href="https://orcid.org/{_e(a["orcid"])}" target="_blank" class="orcid-link">0000-…</a>'
        author_names.append(f'{_e(name)}{corr}{sup}{orcid_html}')

    authors_line = ", ".join(author_names)
    affils_html  = "".join(
        f'<div class="affil"><sup>{i+1}</sup> {_e(aff)}</div>'
        for i, aff in enumerate(affil_list)
    )

    # ── Dates row ────────────────────────────────────────────────────────────
    dates_parts = []
    if received:  dates_parts.append(f'<span><strong>Received Date</strong>: {received}</span>')
    if accepted:  dates_parts.append(f'<span><strong>Accepted Date</strong>: {accepted}</span>')
    if published: dates_parts.append(f'<span><strong>Published Date</strong>: {published}</span>')
    dates_html = '<div class="dates-row">' + "&nbsp;&nbsp;&nbsp;".join(dates_parts) + '</div>' if dates_parts else ""

    # ── DOI / URL row ────────────────────────────────────────────────────────
    doi_html = ""
    if doi:
        doi_url  = f"https://doi.org/{doi}"
        doi_html = f'<div class="doi-row"><a href="{doi_url}" target="_blank" style="color:{NAVY};">{doi_url}</a></div>'

    # ── Keywords ─────────────────────────────────────────────────────────────
    kw_html = ""
    if keywords:
        kw_html = '<div class="keywords"><strong>Keywords</strong>: ' + "; ".join(_e(k) for k in keywords) + "</div>"

    # ── Main article body ─────────────────────────────────────────────────────
    body_html = ""
    for sec in sections:
        heading = sec.get("heading") or ""
        sec_id  = re.sub(r'\W+', '-', heading).strip('-').lower()
        body_html += f'<h2 id="{sec_id}" class="sec-heading">{_e_fmt(heading)}</h2>'
        body_html += _render_content_blocks(sec.get("content") or [])
        for sub in sec.get("subsections") or []:
            sub_heading = sub.get("heading") or ""
            sub_id = re.sub(r'\W+', '-', sub_heading).strip('-').lower()
            body_html += f'<h3 id="{sub_id}" class="subsec-heading">{_e_fmt(sub_heading)}</h3>'
            body_html += _render_content_blocks(sub.get("content") or [])

    # ── References ───────────────────────────────────────────────────────────
    from urllib.parse import quote as _quote
    ref_items_html = ""
    for i, ref in enumerate(references, 1):
        raw   = (ref.get("raw_text") or str(ref) if isinstance(ref, dict) else str(ref)).rstrip(".")
        doi_r = (ref.get("doi") or "") if isinstance(ref, dict) else ""
        if doi_r:
            raw = re.sub(r'\bhttps?://doi\.org/\S+', '', raw, flags=re.IGNORECASE)
            raw = re.sub(r'\bdoi:\s*10\.\S+', '', raw, flags=re.IGNORECASE)
            raw = ' '.join(raw.split())
        badge_style = f'color:{NAVY}; font-weight:600; text-decoration:none;'
        gs_q    = _quote(raw[:300])
        gs_url  = f"https://scholar.google.com/scholar?q={gs_q}"
        gs_link = f' [<a href="{gs_url}" target="_blank" style="{badge_style}">Google Scholar</a>]'
        cr_link = (f' [<a href="https://doi.org/{_e(doi_r)}" target="_blank" style="{badge_style}">CrossRef</a>]'
                   if doi_r else "")
        ref_items_html += f'<div class="ref-item" id="ref-{i}">[{i}] {_linkify(raw)}{gs_link}{cr_link}</div>'

    # ── Right panel content ───────────────────────────────────────────────────
    # Metrics panel
    metrics_rows = []
    if doi:           metrics_rows.append(("DOI", f'<a href="https://doi.org/{_e(doi)}" target="_blank">{_e(doi)}</a>'))
    if journal:       metrics_rows.append(("Journal", journal))
    if issn_online:   metrics_rows.append(("ISSN (Online)", issn_online))
    if issn_print:    metrics_rows.append(("ISSN (Print)", issn_print))
    if publisher:     metrics_rows.append(("Publisher", publisher))
    if received:      metrics_rows.append(("Received", received))
    if accepted:      metrics_rows.append(("Accepted", accepted))
    if published:     metrics_rows.append(("Published", published))
    metrics_html = "".join(f'<div class="meta-row"><span class="meta-label">{k}</span><span class="meta-val">{v}</span></div>'
                           for k, v in metrics_rows)

    # Media panel
    all_figs  = _collect_figures(article)
    media_html = "".join(
        f'<div class="panel-fig"><a href="#{_e(f.get("id",""))}">'
        + (f'<img src="{f["data_uri"]}" alt="{_e(f.get("label",""))}" style="max-width:100%;border-radius:3px;margin-bottom:4px;"/>'
           if f.get("data_uri") else f'<div class="fig-placeholder">[{_e(f.get("label","Figure"))}]</div>')
        + f'</a><div class="panel-fig-label">{_e_fmt(f.get("label",""))}</div>'
        + (f'<div class="panel-fig-caption">{_e_fmt(f.get("caption",""))}</div>' if f.get("caption") else "")
        + '</div>'
        for f in all_figs
    ) or "<p class='empty-panel'>No figures</p>"

    # Tables panel
    all_tbls   = _collect_tables(article)
    tables_html = "".join(
        f'<div class="panel-tbl-entry"><a href="#{_e(t.get("id",""))}" style="color:{NAVY};font-weight:600;">'
        + _e(t.get("caption") or t.get("label") or "Table") + "</a></div>"
        for t in all_tbls
    ) or "<p class='empty-panel'>No tables</p>"

    # Contributors panel
    contributors_html = ""
    for a in authors:
        name = f"{a.get('first_name','')} {a.get('last_name','')}".strip()
        aff  = a.get("affiliation") or ""
        email = a.get("email") or ""
        orcid = a.get("orcid") or ""
        contributors_html += f'<div class="contributor">'
        contributors_html += f'<div class="contrib-name">{_e(name)}'
        if a.get("corresponding"):
            contributors_html += ' <span class="corr-badge">Corresponding</span>'
        contributors_html += '</div>'
        if aff:   contributors_html += f'<div class="contrib-detail">{_e(aff)}</div>'
        if email: contributors_html += f'<div class="contrib-detail"><a href="mailto:{_e(email)}">{_e(email)}</a></div>'
        if orcid: contributors_html += f'<div class="contrib-detail"><a href="https://orcid.org/{_e(orcid)}" target="_blank">ORCID: {_e(orcid)}</a></div>'
        contributors_html += '</div>'

    # ── Journal header logo ────────────────────────────────────────────────
    if journal_logo:
        logo_html = f'<img src="{journal_logo}" alt="Journal logo" style="height:40px;object-fit:contain;margin-bottom:4px;"/>'
    else:
        initials = "".join(w[0].upper() for w in (journal or "NP").split()[:2])
        logo_html = f'<div class="journal-initials">{initials}</div>'

    if brand_logo:
        brand_html = f'<img src="{brand_logo}" alt="Publisher" style="height:32px;object-fit:contain;"/>'
    else:
        brand_html = f'<div style="font-size:13px;font-weight:bold;color:{NAVY};">NovelTOR</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title}</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: Arial, Helvetica, sans-serif; font-size: 14px; color: #222;
       display: flex; height: 100vh; overflow: hidden; background: #f4f6f9; }}

/* ── Left TOC sidebar ── */
#toc-sidebar {{
  width: 280px; min-width: 220px; background: #fff;
  border-right: 1px solid #dde3ea;
  display: flex; flex-direction: column; overflow: hidden;
}}
#toc-sidebar h2 {{
  font-size: 15px; font-weight: 700; padding: 18px 20px 12px;
  border-bottom: 1px solid #dde3ea; color: #111; letter-spacing: 0.02em;
}}
#toc-inner {{ overflow-y: auto; flex: 1; padding: 10px 0; }}
#toc-inner ul {{ list-style: none; }}
#toc-inner li {{ padding: 0; }}
#toc-inner li a {{
  display: block; padding: 5px 20px; font-size: 13px; color: #333;
  text-decoration: none; line-height: 1.4;
  border-left: 3px solid transparent;
  transition: background 0.15s, color 0.15s;
}}
#toc-inner li a:hover, #toc-inner li a.active {{
  background: {NAVY_LIGHT}; color: {NAVY}; border-left-color: {NAVY};
}}
#toc-inner li.toc-sub a {{ padding-left: 36px; font-size: 12px; color: #555; }}

/* ── Main content area ── */
#main-content {{
  flex: 1; overflow-y: auto; background: #fff;
  padding: 0; position: relative;
}}
.article-inner {{ max-width: 860px; margin: 0 auto; padding: 32px 40px 60px; }}

/* ── Journal header ── */
.journal-header {{
  display: flex; align-items: center; justify-content: space-between;
  border-bottom: 2px solid {NAVY}; padding-bottom: 12px; margin-bottom: 20px;
}}
.journal-left {{ display: flex; align-items: center; gap: 12px; }}
.journal-initials {{
  width: 44px; height: 44px; background: {NAVY_LIGHT}; border: 2px solid {NAVY};
  border-radius: 4px; display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 14px; color: {NAVY};
}}
.journal-name {{ font-size: 13px; font-weight: 700; color: {NAVY}; }}
.journal-from {{ font-size: 11px; color: #aaa; }}

/* ── Metadata strip ── */
.meta-strip {{ font-size: 12px; color: #555; margin-bottom: 16px; line-height: 1.8; }}
.meta-strip a {{ color: {NAVY}; }}

/* ── Article title ── */
h1.article-title {{ font-size: 22px; font-weight: 700; color: #111; line-height: 1.35; margin-bottom: 12px; }}
.doi-row {{ font-size: 12px; margin-bottom: 10px; }}
.dates-row {{ font-size: 12px; color: #444; margin-bottom: 14px; display: flex; gap: 24px; flex-wrap: wrap; }}
.dates-row strong {{ color: #111; }}

/* ── Authors ── */
.authors-line {{ font-size: 14px; margin-bottom: 8px; line-height: 1.6; }}
.orcid-link {{ color: #a6ce39; font-size: 11px; }}
.affil {{ font-size: 12px; color: #555; margin-bottom: 2px; }}
.keywords {{ font-size: 13px; margin: 14px 0; }}

/* ── Abstract ── */
.abstract-box {{
  background: {NAVY_LIGHT}; border-left: 4px solid {NAVY};
  padding: 16px 20px; border-radius: 4px; margin: 20px 0;
}}
.abstract-box h3 {{ font-size: 13px; font-weight: 700; color: {NAVY}; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em; }}
.abstract-box p {{ font-size: 13px; line-height: 1.7; color: #333; }}

/* ── Section headings ── */
h2.sec-heading {{
  font-size: 16px; font-weight: 700; color: {NAVY};
  margin: 28px 0 10px; padding-bottom: 4px; border-bottom: 1px solid #dde3ea;
}}
h3.subsec-heading {{ font-size: 14px; font-weight: 700; color: #333; margin: 18px 0 8px; }}
p.body-text {{ font-size: 13px; line-height: 1.8; color: #333; margin-bottom: 12px; }}
.equation {{ text-align: center; margin: 16px 0; }}

/* ── Figures ── */
.figure-block {{ margin: 20px 0; text-align: center; }}
.figure-block img {{ max-width: 100%; max-height: 70vh; border-radius: 4px; }}
.fig-caption {{ font-size: 12px; font-style: italic; color: #555; margin-top: 6px; text-align: center; }}
.fig-placeholder {{ background: #f0f2f5; border: 1px solid #dde; padding: 40px; color: #aaa; border-radius: 4px; }}

/* ── Tables ── */
.table-block {{ margin: 20px 0; }}
.table-label {{ font-size: 13px; font-weight: 700; color: #333; margin-bottom: 6px; }}
.table-scroll {{ overflow-x: auto; }}
table.data-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
table.data-table th {{ background: {NAVY}; color: #fff; padding: 6px 10px; text-align: left; font-weight: 600; }}
table.data-table td {{ padding: 5px 10px; border-bottom: 1px solid #e8ecf0; vertical-align: top; }}
table.data-table tr.even td {{ background: #f7f9fc; }}

/* ── References ── */
.references-section {{ margin: 28px 0; }}
.references-section h2 {{ font-size: 16px; font-weight: 700; color: {NAVY}; margin-bottom: 14px; }}
.ref-item {{ font-size: 12px; line-height: 1.6; color: #333; margin-bottom: 8px; padding-left: 8px; }}

/* ── RIGHT TAB SIDEBAR ── */
#tab-sidebar {{
  width: 44px; background: #fff; border-left: 1px solid #dde3ea;
  display: flex; flex-direction: column; align-items: center;
  padding-top: 16px; gap: 2px; z-index: 10; position: relative;
}}
.tab-btn {{
  writing-mode: vertical-rl; text-orientation: mixed;
  transform: rotate(180deg);
  background: none; border: none; cursor: pointer;
  font-size: 11px; font-weight: 600; color: #666;
  padding: 14px 8px; border-radius: 4px;
  transition: background 0.15s, color 0.15s;
  white-space: nowrap; letter-spacing: 0.04em;
  width: 40px;
}}
.tab-btn:hover {{ background: {NAVY_LIGHT}; color: {NAVY}; }}
.tab-btn.active {{ background: {NAVY}; color: #fff; }}

/* ── Right slide panel ── */
#right-panel {{
  position: fixed; top: 0; right: 44px; width: 340px; height: 100vh;
  background: #fff; border-left: 1px solid #dde3ea;
  box-shadow: -4px 0 16px rgba(0,0,0,0.08);
  transform: translateX(100%); transition: transform 0.25s ease;
  z-index: 9; display: flex; flex-direction: column; overflow: hidden;
}}
#right-panel.open {{ transform: translateX(0); }}
.panel-header {{
  padding: 16px 20px; border-bottom: 1px solid #dde3ea;
  display: flex; align-items: center; justify-content: space-between;
}}
.panel-header h3 {{ font-size: 14px; font-weight: 700; color: {NAVY}; }}
.panel-close {{ background: none; border: none; cursor: pointer; font-size: 18px; color: #888; }}
.panel-body {{ flex: 1; overflow-y: auto; padding: 16px 20px; }}
.panel-section {{ display: none; }}
.panel-section.active {{ display: block; }}

.meta-row {{ display: flex; gap: 8px; margin-bottom: 10px; font-size: 13px; flex-wrap: wrap; }}
.meta-label {{ font-weight: 600; color: #555; min-width: 110px; }}
.meta-val {{ color: #333; flex: 1; }}

.panel-fig {{ margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 16px; }}
.panel-fig-label {{ font-size: 12px; font-weight: 700; color: #333; margin-top: 6px; }}
.panel-fig-caption {{ font-size: 11px; color: #666; margin-top: 2px; font-style: italic; }}
.panel-tbl-entry {{ margin-bottom: 12px; font-size: 13px; }}

.contributor {{ margin-bottom: 16px; padding-bottom: 14px; border-bottom: 1px solid #eee; }}
.contrib-name {{ font-size: 13px; font-weight: 700; color: #111; margin-bottom: 4px; }}
.contrib-detail {{ font-size: 12px; color: #555; margin-bottom: 2px; }}
.corr-badge {{
  font-size: 10px; background: {NAVY_LIGHT}; color: {NAVY};
  padding: 1px 6px; border-radius: 10px; font-weight: 600; margin-left: 6px;
}}
.empty-panel {{ color: #aaa; font-size: 13px; font-style: italic; }}
</style>
</head>
<body>

<!-- LEFT: Table of Contents -->
<aside id="toc-sidebar">
  <h2>Table of Contents</h2>
  <nav id="toc-inner">
    {toc_html}
  </nav>
</aside>

<!-- CENTRE: Article content -->
<main id="main-content">
  <div class="article-inner">

    <!-- Journal header -->
    <div class="journal-header">
      <div class="journal-left">
        {logo_html}
        <div>
          <div class="journal-from">From the journal:</div>
          <div class="journal-name">{journal}</div>
        </div>
      </div>
      {brand_html}
    </div>

    <!-- Metadata strip -->
    <div class="meta-strip">
      {f"ISSN (Online): {issn_online}<br/>" if issn_online else ""}
      {f"ISSN (Print): {issn_print}<br/>" if issn_print else ""}
      {f"Publisher: {publisher}" if publisher else ""}
    </div>

    <!-- Title -->
    <h1 class="article-title" id="article-title">{title}</h1>
    {doi_html}

    <!-- Authors -->
    <div id="authors">
      <div class="authors-line">{authors_line}</div>
      <div class="affils">{affils_html}</div>
    </div>
    {dates_html}

    <!-- Abstract -->
    {f'<div class="abstract-box" id="abstract"><h3>Abstract</h3><p>{_e_fmt(abstract)}</p></div>' if abstract else ""}
    {kw_html}

    <!-- Body sections -->
    {body_html}

    <!-- References -->
    {f'<div class="references-section" id="references"><h2>References</h2>{ref_items_html}</div>' if ref_items_html else ""}

  </div>
</main>

<!-- RIGHT: Tab sidebar -->
<aside id="tab-sidebar">
  <button class="tab-btn" data-panel="metrics"      onclick="openPanel('metrics')">Metrics</button>
  <button class="tab-btn" data-panel="media"        onclick="openPanel('media')">Media</button>
  <button class="tab-btn" data-panel="tables"       onclick="openPanel('tables')">Tables</button>
  <button class="tab-btn" data-panel="references"   onclick="openPanel('references')">References</button>
  <button class="tab-btn" data-panel="contributors" onclick="openPanel('contributors')">Contributors</button>
</aside>

<!-- RIGHT: Slide-out panel -->
<div id="right-panel">
  <div class="panel-header">
    <h3 id="panel-title">Panel</h3>
    <button class="panel-close" onclick="closePanel()">✕</button>
  </div>
  <div class="panel-body">
    <div class="panel-section" id="panel-metrics">
      {metrics_html or "<p class='empty-panel'>No metadata available</p>"}
    </div>
    <div class="panel-section" id="panel-media">
      {media_html}
    </div>
    <div class="panel-section" id="panel-tables">
      {tables_html}
    </div>
    <div class="panel-section" id="panel-references">
      {ref_items_html or "<p class='empty-panel'>No references</p>"}
    </div>
    <div class="panel-section" id="panel-contributors">
      {contributors_html or "<p class='empty-panel'>No contributors</p>"}
    </div>
  </div>
</div>

<script>
let currentPanel = null;

function openPanel(name) {{
  const panel = document.getElementById('right-panel');
  const title = document.getElementById('panel-title');
  const names = {{'metrics':'Metrics','media':'Media','tables':'Tables','references':'References','contributors':'Contributors'}};

  if (currentPanel === name) {{ closePanel(); return; }}

  document.querySelectorAll('.panel-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

  document.getElementById('panel-' + name).classList.add('active');
  document.querySelector('[data-panel="' + name + '"]').classList.add('active');
  title.textContent = names[name] || name;
  panel.classList.add('open');
  currentPanel = name;
}}

function closePanel() {{
  document.getElementById('right-panel').classList.remove('open');
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  currentPanel = null;
}}

// Active TOC highlighting on scroll
const headings = document.querySelectorAll('h1,h2,h3,[id]');
const tocLinks = document.querySelectorAll('#toc-inner a');

const observer = new IntersectionObserver((entries) => {{
  entries.forEach(e => {{
    if (e.isIntersecting) {{
      tocLinks.forEach(l => l.classList.remove('active'));
      const link = document.querySelector('#toc-inner a[href="#' + e.target.id + '"]');
      if (link) link.classList.add('active');
    }}
  }});
}}, {{ rootMargin: '-20% 0px -70% 0px' }});

document.querySelectorAll('[id]').forEach(el => observer.observe(el));
</script>
</body>
</html>"""
