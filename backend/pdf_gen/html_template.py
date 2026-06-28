"""
Builds the HTML string for WeasyPrint → PDF rendering.
Matches the NFP academic article layout spec.
"""
import html as _html
import re

NAVY  = "#0F3557"
RED   = "#C0452A"
LB    = "#E8F0FB"   # light blue badge bg
GRN   = "#E8F5E9"   # green badge bg

_MONTHS = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December",
]

_TYPE_LABELS = {
    "Research Article":        "RESEARCH ARTICLE",
    "Review":                  "REVIEW ARTICLE",
    "Conference Proceeding":   "CONFERENCE PROCEEDING",
    "Enhanced Poster Abstract": "ENHANCED POSTER ABSTRACT",
    "Conference Report":       "CONFERENCE REPORT",
}


def _e(s) -> str:
    return _html.escape(str(s or ""), quote=False)

_SUB_SUP_RE = re.compile(r'&lt;(/?(?:sub|sup))&gt;', re.IGNORECASE)

def _e_fmt(s) -> str:
    """Like _e but restores <sub>/<sup> tags from parser-produced text."""
    return _SUB_SUP_RE.sub(r'<\1>', _html.escape(str(s or ""), quote=False))


_URL_RE  = re.compile(r'(https?://[^\s<>"\')\]]+)', re.IGNORECASE)
_CITE_RE = re.compile(r'\[([\d,\s–—-]+)\]')
def _linkify(text: str) -> str:
    """Escape text for HTML (preserving sub/sup) and wrap bare URLs in <a> tags."""
    parts = _URL_RE.split(str(text or ""))
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            out.append(_e_fmt(part))
        else:
            clean = part.rstrip(".,;")
            tail  = part[len(clean):]
            url   = _html.escape(clean, quote=True)
            out.append(f'<a href="{url}" style="color:{NAVY};">{_html.escape(clean, quote=False)}</a>')
            if tail:
                out.append(_html.escape(tail, quote=False))
    return "".join(out)


def _citify(text: str) -> str:
    """Wrap bracket citations [N], [N–M], [N, M] with internal anchor links, expanding ranges."""
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


def _date_fmt(d) -> str:
    if not d:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", str(d).strip())
    if m:
        y, mo, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        mon = _MONTHS[mo - 1] if 1 <= mo <= 12 else str(mo)
        return f"{day} {mon} {y}"
    return _e(d)


def _css(journal_name: str) -> str:
    # Escape journal name for CSS content string
    jn = journal_name.replace("\\", "\\\\").replace('"', '\\"')
    return f"""
@page {{
    size: A4;
    margin: 20mm 18mm 24mm 18mm;
    @bottom-left {{
        content: "{jn}";
        font-family: Arial, Helvetica, sans-serif;
        font-size: 7pt;
        color: #888;
        border-top: 0.5pt solid #ccc;
        padding-top: 3pt;
        vertical-align: top;
    }}
    @bottom-right {{
        content: counter(page);
        font-family: Arial, Helvetica, sans-serif;
        font-size: 7pt;
        color: #888;
        border-top: 0.5pt solid #ccc;
        padding-top: 3pt;
        text-align: right;
        vertical-align: top;
    }}
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #222;
}}

/* ── 3-column header ── */
.page-header {{ display: table; width: 100%; border-collapse: collapse; margin-bottom: 5pt; }}
.hdr-left, .hdr-center, .hdr-right {{ display: table-cell; vertical-align: middle; }}
.hdr-left   {{ width: 20%; }}
.hdr-center {{ width: 55%; padding: 0 10pt; }}
.hdr-right  {{ width: 25%; text-align: right; }}

.journal-thumb {{
    width: 46pt; height: 46pt;
    background: {LB};
    border: 1.5pt solid {NAVY};
    border-radius: 3pt;
    text-align: center;
    padding-top: 12pt;
    font-size: 13pt;
    font-weight: bold;
    color: {NAVY};
}}
.hdr-publisher-label {{ font-size: 7.5pt; color: #888; margin-top: 2pt; }}
.from-label          {{ font-size: 8pt; color: #aaa; }}
.hdr-journal-name    {{ font-size: 11pt; font-weight: bold; color: {NAVY}; }}

.header-rule {{ border: none; border-top: 2pt solid {NAVY}; margin: 5pt 0 6pt; }}

/* ── Article header ── */
.badge-row {{ margin-bottom: 3pt; }}
.badge {{
    display: inline-block;
    padding: 2pt 8pt;
    border-radius: 10pt;
    font-size: 7pt;
    font-weight: bold;
    letter-spacing: 0.5pt;
    margin-right: 4pt;
}}
.badge-blue  {{ background: {LB};  color: {NAVY};    }}
.badge-green {{ background: {GRN}; color: #2E7D32; }}

.article-title {{
    font-size: 16pt; font-weight: bold;
    color: {NAVY}; line-height: 1.25; margin: 3pt 0 2pt;
}}
.authors-line {{ font-size: 10pt; color: #222; margin-bottom: 1pt; }}
.author-sup   {{ font-size: 6.5pt; color: {NAVY}; vertical-align: super; line-height: 0; }}
.affiliations {{ font-size: 8pt; color: #666; line-height: 1.5; margin-bottom: 1pt; }}
.affil-sup    {{ font-size: 6pt; vertical-align: super; line-height: 0; }}
.corresp-line {{ font-size: 8pt; color: #555; margin-bottom: 1pt; }}
.dates-row    {{ font-size: 8.5pt; color: #555; margin-bottom: 2pt; }}
.date-label   {{ font-weight: bold; color: #333; }}

.section-rule {{ border: none; border-top: 1pt solid #ddd; margin: 3pt 0; }}

/* ── Abstract ── */
.abstract-heading {{
    font-size: 10pt; font-weight: bold; color: {NAVY};
    text-transform: uppercase; letter-spacing: 0.6pt; margin-bottom: 2pt;
}}
.abstract-text {{ font-size: 10pt; line-height: 1.6; text-align: justify; }}
.keywords-line {{ font-size: 10pt; margin-top: 2pt; line-height: 1.5; }}

/* ── Body (single column) ── */
.two-col {{
    margin-top: 2pt;
}}

/* ── Body ── */
.body-section       {{ margin-top: 12pt; break-inside: avoid-column; }}
.section-heading    {{ font-size: 10pt; font-weight: bold; color: {NAVY}; margin-bottom: 3pt; margin-top: 0pt; }}
.section-body       {{ font-size: 9.5pt; line-height: 1.6; text-align: justify; margin-bottom: 2pt; }}
.subsection         {{ margin-top: 8pt; }}
.subsection-heading {{ font-size: 9.5pt; font-weight: bold; margin-bottom: 2pt; margin-top: 0pt; }}

/* ── Tables (full width) ── */
.table-wrap  {{ margin: 3pt 0; page-break-inside: avoid; width: 100%; }}
.table-label {{ font-size: 9pt; font-weight: bold; margin-bottom: 2pt; }}
.data-table  {{ width: 100%; border-collapse: collapse; font-size: 9pt; }}
.data-table th {{
    background: {NAVY}; color: white;
    padding: 4pt 6pt; text-align: left; font-size: 8.5pt;
}}
.data-table td  {{ padding: 3pt 6pt; border-bottom: 0.5pt solid #e0e0e0; vertical-align: top; }}
.data-table .even td {{ background: #F5F7FA; }}

/* ── Figures (full width) ── */
.figure-wrap {{ margin: 3pt 0; width: 100%; }}
.figure-img  {{ max-width: 100%; max-height: 140mm; display: block; margin: 0 auto; }}

/* ── Equations (selectable text/MathML) ── */
.equation {{ text-align: center; margin: 4pt 0; padding: 6pt; background: #f9f9f9; border-radius: 2pt; font-size: 10pt; }}
.equation math {{ display: block; text-align: center; }}
/* Poster: images fill the full page width, no height cap */
body.poster .figure-img {{ width: 100%; max-height: none; }}
.figure-box  {{
    background: #F5F7FA; border: 1pt solid #ddd;
    height: 70pt; text-align: center; padding-top: 28pt;
    font-size: 9pt; color: #bbb; border-radius: 2pt; margin-bottom: 3pt;
}}
.figure-caption {{ font-size: 8.5pt; font-style: italic; text-align: center; color: #555;
                   page-break-before: avoid; margin-top: 1pt; }}

/* ── References (rendered outside the two-col div — naturally full-width) ── */
.references-section {{ margin-top: 3pt; }}
.references-heading {{
    font-size: 10pt; font-weight: bold; color: {NAVY};
    margin-bottom: 2pt; border-top: 1pt solid #ddd; padding-top: 2pt;
}}
.ref-item {{
    font-size: 8.5pt; line-height: 1.5; margin-bottom: 1pt;
    padding-left: 18pt; text-indent: -18pt;
}}
.ref-doi {{ color: {NAVY}; text-decoration: none; }}
.ref-doi:hover {{ text-decoration: underline; }}
.ref-badge {{ color: {NAVY}; text-decoration: none; font-weight: 600; }}
.ref-badge:hover {{ text-decoration: underline; }}
a {{ color: {NAVY}; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
"""


def _logo_svg() -> str:
    return (
        '<svg width="110" height="36" viewBox="0 0 110 36"'
        ' xmlns="http://www.w3.org/2000/svg" style="display:block;margin-left:auto;">'
        # N mark — navy rect
        f'<rect x="0" y="3" width="30" height="30" rx="2" fill="{NAVY}"/>'
        # white N
        '<text x="15" y="23" font-family="Arial,Helvetica,sans-serif"'
        ' font-size="17" font-weight="bold" fill="white" text-anchor="middle">N</text>'
        # red diagonal slash
        f'<line x1="21" y1="3" x2="9" y2="33" stroke="{RED}" stroke-width="3.2"'
        ' stroke-linecap="round"/>'
        # OVEL text
        f'<text x="36" y="17" font-family="Arial,Helvetica,sans-serif"'
        f' font-size="12" font-weight="bold" fill="{NAVY}">OVEL</text>'
        # Publisher text
        '<text x="36" y="30" font-family="Arial,Helvetica,sans-serif"'
        ' font-size="9.5" fill="#555">Publisher</text>'
        '</svg>'
    )


def _build_affils(authors: list) -> list:
    seen: list[str] = []
    for a in authors:
        aff = (a.get("affiliation") or "").strip()
        if aff and aff not in seen:
            seen.append(aff)
    return seen


def _pub_date_str(article: dict) -> str:
    if article.get("published_date"):
        return _date_fmt(article["published_date"])
    if article.get("pub_date_year"):
        parts = []
        if article.get("pub_date_day"):
            parts.append(str(article["pub_date_day"]))
        if article.get("pub_date_month"):
            try:
                parts.append(_MONTHS[int(article["pub_date_month"]) - 1])
            except (ValueError, IndexError):
                parts.append(str(article["pub_date_month"]))
        parts.append(str(article["pub_date_year"]))
        return " ".join(parts)
    return ""


def _render_figure_block(fig: dict) -> str:
    label   = _e_fmt(fig.get("label") or "Figure")
    caption = _e_fmt(fig.get("caption") or "")
    data_uri = fig.get("data_uri") or ""
    if data_uri:
        img_html = f'<img src="{data_uri}" class="figure-img" />'
    else:
        img_html = f'<div class="figure-box">[{label}]</div>'
    cap_html = f'<div class="figure-caption"><strong>{label}.</strong> {caption}</div>' if caption else \
               f'<div class="figure-caption"><strong>{label}</strong></div>'
    return f'<div class="figure-wrap">{img_html}{cap_html}</div>'


def _render_table_block(tbl: dict) -> str:
    caption = _e(tbl.get("caption") or tbl.get("label") or "")
    headers = tbl.get("headers") or []
    rows    = tbl.get("rows") or []
    t = f'<div class="table-wrap"><div class="table-label">{caption}</div>'
    t += '<table class="data-table">'
    if headers:
        t += "<thead><tr>" + "".join(f"<th>{_citify(_linkify(h))}</th>" for h in headers) + "</tr></thead>"
    if rows:
        t += "<tbody>"
        for ri, row in enumerate(rows):
            cls = "even" if ri % 2 == 1 else ""
            t += f'<tr class="{cls}">' + "".join(f"<td>{_citify(_linkify(c))}</td>" for c in row) + "</tr>"
        t += "</tbody>"
    t += "</table></div>"
    return t


def _render_content_blocks(sec: dict) -> str:
    """Render a section or subsection's content array as HTML (legacy, mixed layout).

    Handles both the new content-array format and the legacy body-string format
    so that hand-edited article dicts still render correctly.
    """
    html = ""
    content = sec.get("content")
    if content:
        for block in content:
            btype = block.get("type")
            if btype == "paragraph":
                text = (block.get("text") or "").strip()
                if text:
                    html += f'<div class="section-body">{_citify(_linkify(text))}</div>'
            elif btype == "table":
                html += _render_table_block(block)
            elif btype == "figure":
                html += _render_figure_block(block)
            elif btype == "equation":
                # Render equation as MathML (selectable text) instead of image
                mathml = block.get("mathml", "")
                text = block.get("text", "")

                if mathml:
                    # Use MathML for proper rendering and selectability
                    html += f'<div style="text-align:center;margin:3pt 0;padding:4pt;background:#f9f9f9;border-radius:2pt;font-family:serif;">{mathml}</div>'
                elif text:
                    # Fallback to text representation
                    html += f'<div style="text-align:center;margin:3pt 0;padding:4pt;background:#f9f9f9;border-radius:2pt;font-family:monospace;font-size:9pt;">{_e(text)}</div>'
                else:
                    uri = block.get("data_uri", "")
                    if uri:
                        # Last resort: use image
                        html += f'<div style="text-align:center;margin:3pt 0;"><img src="{uri}" style="max-height:60pt;max-width:100%;" alt="equation"/></div>'
    else:
        # Fallback: legacy plain body string
        body_text = (sec.get("body") or "").strip()
        for para in re.split(r"\n{2,}", body_text):
            para = para.strip()
            if para:
                html += f'<div class="section-body">{_citify(_linkify(para))}</div>'
    return html


def build_html(article: dict, two_col: bool = False) -> str:
    authors      = article.get("authors") or []
    journal_name = (article.get("journal_name") or "Novel Future Proceedings").strip()
    article_type = article.get("article_type") or "Research Article"
    title        = article.get("title") or "Untitled"
    abstract     = (article.get("abstract") or "").strip()
    keywords     = article.get("keywords") or []
    sections     = article.get("sections") or []
    references   = article.get("references") or []
    figures      = article.get("figures") or []
    journal_logo = (article.get("journal_logo") or "").strip()
    brand_logo   = (article.get("brand_logo") or "").strip()

    affils      = _build_affils(authors)
    multi_affil = len(affils) > 1

    # ── Journal header ──────────────────────────────────────────────
    initials = "".join(w[0].upper() for w in journal_name.split()[:2]) or "NP"
    if journal_logo:
        left_logo = (
            f'<div class="journal-thumb" style="padding:0;background:none;border:none;">'
            f'<img src="{journal_logo}" style="width:46pt;height:46pt;object-fit:contain;" /></div>'
        )
    else:
        left_logo = f'<div class="journal-thumb">{_e(initials)}</div>'

    right_logo = (
        f'<img src="{brand_logo}" style="display:block;margin-left:auto;max-width:110pt;max-height:36pt;object-fit:contain;" />'
        if brand_logo else _logo_svg()
    )

    header = f"""
<div class="page-header">
  <div class="hdr-left">
    {left_logo}
  </div>
  <div class="hdr-center">
    <div class="from-label">From the journal:</div>
    <div class="hdr-journal-name">{_e(journal_name)}</div>
  </div>
  <div class="hdr-right">{right_logo}</div>
</div>
<hr class="header-rule">
"""

    # ── Badges ──────────────────────────────────────────────────────
    type_label = _TYPE_LABELS.get(article_type, article_type.upper())
    badges = (
        f'<div class="badge-row">'
        f'<span class="badge badge-blue">{_e(type_label)}</span>'
        f'<span class="badge badge-green">OPEN ACCESS</span>'
        f'</div>'
    )

    # ── Title ────────────────────────────────────────────────────────
    title_html = f'<div class="article-title">{_e_fmt(title)}</div>'

    # ── Authors ──────────────────────────────────────────────────────
    author_parts = []
    for a in authors:
        name = f"{(a.get('first_name') or '').strip()} {(a.get('last_name') or '').strip()}".strip()
        sups = []
        if multi_affil:
            aff = (a.get("affiliation") or "").strip()
            if aff in affils:
                sups.append(str(affils.index(aff) + 1))
        if a.get("corresponding"):
            sups.append("*")
        sup_str = ",".join(sups)
        chunk = _e(name)
        if sup_str:
            chunk += f'<sup class="author-sup">{_e(sup_str)}</sup>'
        author_parts.append(chunk)
    authors_html = f'<div class="authors-line">{", ".join(author_parts)}</div>'

    # ── Affiliations ─────────────────────────────────────────────────
    affil_lines = []
    for i, aff in enumerate(affils, 1):
        num = f'<sup class="affil-sup">{i}</sup>&nbsp;' if multi_affil else ""
        affil_lines.append(f"<div>{num}{_e(aff)}</div>")
    affiliations_html = (
        f'<div class="affiliations">{"".join(affil_lines)}</div>'
        if affil_lines else ""
    )

    # ── Corresponding email ──────────────────────────────────────────
    corresp_html = ""
    for a in authors:
        if a.get("corresponding") and a.get("email"):
            corresp_html = f'<div class="corresp-line">*Corresponding author: {_e(a["email"])}</div>'
            break

    # ── Dates ────────────────────────────────────────────────────────
    date_parts = []
    if article.get("received_date"):
        date_parts.append(
            f'<span class="date-label">Received:</span>&nbsp;{_date_fmt(article["received_date"])}'
        )
    if article.get("accepted_date"):
        date_parts.append(
            f'<span class="date-label">Accepted:</span>&nbsp;{_date_fmt(article["accepted_date"])}'
        )
    pub = _pub_date_str(article)
    if pub:
        date_parts.append(f'<span class="date-label">Published:</span>&nbsp;{_e(pub)}')
    dates_html = (
        f'<div class="dates-row">{"&emsp;".join(date_parts)}</div>'
        if date_parts else ""
    )

    # ── DOI ──────────────────────────────────────────────────────────
    doi_val = (article.get("doi") or "").strip()
    if doi_val:
        doi_url = _html.escape(f"https://doi.org/{doi_val}", quote=True)
        doi_html = (
            f'<div class="dates-row">'
            f'<span class="date-label">DOI:</span>&nbsp;'
            f'<a class="ref-doi" href="{doi_url}">{_e(doi_val)}</a>'
            f'</div>'
        )
    else:
        doi_html = ""

    # ── Abstract + Keywords ──────────────────────────────────────────
    abstract_html = ""
    keywords_html = ""
    if abstract:
        abstract_html = f"""
<hr class="section-rule">
<div class="abstract-heading">Abstract</div>
<div class="abstract-text">{_linkify(abstract)}</div>
"""
    if keywords:
        keywords_html = (
            f'<div class="keywords-line">'
            f'<strong>Keywords:</strong> {_e("; ".join(keywords))}</div>'
        )

    # ── Body sections ────────────────────────────────────────────────
    body_parts = []
    for sec in sections:
        heading = (sec.get("heading") or "").strip()
        subsecs = sec.get("subsections") or []

        sec_html = '<div class="body-section">'
        if heading:
            sec_html += f'<div class="section-heading">{_e_fmt(heading)}</div>'
        sec_html += _render_content_blocks(sec)
        for sub in subsecs:
            sh = (sub.get("heading") or "").strip()
            sec_html += '<div class="subsection">'
            if sh:
                sec_html += f'<div class="subsection-heading">{_e_fmt(sh)}</div>'
            sec_html += _render_content_blocks(sub)
            sec_html += "</div>"
        sec_html += "</div>"
        body_parts.append(sec_html)
    body_html = "\n".join(body_parts)

    # ── References ───────────────────────────────────────────────────
    refs_html = ""
    if references:
        ref_items = []
        for i, ref in enumerate(references, 1):
            if isinstance(ref, dict):
                num = ref.get("number", i)
                raw = (ref.get("raw_text") or "").rstrip(".")
                doi = ref.get("doi") or ""
                if doi:
                    raw = re.sub(r'\bhttps?://doi\.org/\S+', '', raw, flags=re.IGNORECASE)
                    raw = re.sub(r'\bdoi:\s*10\.\S+', '', raw, flags=re.IGNORECASE)
                    raw = ' '.join(raw.split())
                text = _linkify(raw)
            else:
                num, text, doi = i, _linkify(str(ref or "").rstrip(".")), ""
            from urllib.parse import quote as _quote
            gs_q    = _quote(raw[:300])
            gs_url  = f"https://scholar.google.com/scholar?q={gs_q}"
            gs_link = f' [<a class="ref-badge" href="{_html.escape(gs_url, quote=True)}" target="_blank">Google Scholar</a>]'
            if doi:
                doi_url  = _html.escape(f"https://doi.org/{doi}", quote=True)
                cr_link  = f' [<a class="ref-badge" href="{doi_url}" target="_blank">CrossRef</a>]'
            else:
                cr_link = ""
            ref_items.append(f'<div class="ref-item" id="ref-{num}">[{num}]&nbsp;{text}{gs_link}{cr_link}</div>')
        refs_html = (
            '<div class="references-section">'
            '<div class="references-heading">References</div>'
            + "".join(ref_items)
            + "</div>"
        )

    css = _css(journal_name)
    body_wrapper_open  = '<div class="two-col">' if two_col else "<div>"
    body_wrapper_close = "</div>"
    is_poster  = (article_type == "Enhanced Poster Abstract")
    body_class = ' class="poster"' if is_poster else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>{css}</style>
<!-- Support for MathML rendering -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/mathml/2.7.0/mathml.min.js"></script>
</head>
<body{body_class}>
{header}
{badges}
{title_html}
{authors_html}
{affiliations_html}
{corresp_html}
{dates_html}
{doi_html}
{abstract_html}
{keywords_html}
{body_wrapper_open}
{body_html}
{body_wrapper_close}
{refs_html}
</body>
</html>"""
