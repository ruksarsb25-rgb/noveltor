"""
JATS XML generator — NISO Z39.96, Publishing DTD v1.3.
Structure matched to the Data.xml reference used by the NFP website renderer.
"""
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring
from xml.dom import minidom
import re


ARTICLE_TYPE_MAP = {
    "Research Article":        "research-article",
    "Review":                  "review-article",
    "Conference Proceeding":   "proceedings-paper",
    "Enhanced Poster Article": "poster",
    "Conference Report":       "conference-report",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_jats(data: dict) -> str:
    article_type = ARTICLE_TYPE_MAP.get(
        data.get("article_type", "Research Article"), "research-article"
    )

    root = Element("article")
    root.set("xml:lang", "en")
    root.set("xmlns:xlink", "http://www.w3.org/1999/xlink")
    root.set("xmlns:ali",   "http://www.niso.org/schemas/ali/1.0/")
    root.set("xmlns:mml",   "http://www.w3.org/1998/Math/MathML")
    root.set("article-type", article_type)
    root.set("dtd-version",  "1.3")

    front = SubElement(root, "front")
    _build_journal_meta(front, data)
    _build_article_meta(front, data)

    body = SubElement(root, "body")
    _build_body(body, data)

    back = SubElement(root, "back")
    _build_back(back, data)

    raw    = tostring(root, encoding="unicode", xml_declaration=False)
    pretty = _prettify(raw)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.3 20210610//EN"'
        ' "https://jats.nlm.nih.gov/publishing/1.3/JATS-journalpublishing1-3.dtd">\n'
        + pretty
    )


# ---------------------------------------------------------------------------
# Figure filename helper (used by both XML generator and ZIP exporter)
# ---------------------------------------------------------------------------

def fig_filename(data: dict, fig_num: int) -> str:
    """
    Return the canonical filename for figure N, e.g. 'Novel_Energy-1-1-g3.jpeg'.
    Pattern mirrors Data.xml: {journal_slug}-{vol}-{issue}-g{N}.jpeg
    """
    journal  = re.sub(r"[^\w]", "_", data.get("journal_name", "NFP")).strip("_")
    vol      = str(data.get("volume")  or "1")
    issue    = str(data.get("issue")   or "1")
    return f"{journal}-{vol}-{issue}-g{fig_num}.jpeg"


def eq_filename(data: dict, eq_num: int) -> str:
    """Return the canonical filename for equation image N, e.g. 'Novel_Energy-1-1-e1.png'."""
    journal = re.sub(r"[^\w]", "_", data.get("journal_name", "NFP")).strip("_")
    vol     = str(data.get("volume") or "1")
    issue   = str(data.get("issue")  or "1")
    return f"{journal}-{vol}-{issue}-e{eq_num}.png"


# ---------------------------------------------------------------------------
# journal-meta
# ---------------------------------------------------------------------------

def _build_journal_meta(front: Element, data: dict):
    jm = SubElement(front, "journal-meta")

    jid = data.get("journal_name", "Novel Future Proceedings")
    _text(SubElement(jm, "journal-id", {"journal-id-type": "issn"}),
          data.get("issn_online") or data.get("issn_print") or "")

    jt = SubElement(jm, "journal-title-group")
    _text(SubElement(jt, "journal-title"), jid)
    _text(SubElement(jt, "abbrev-journal-title"), jid)   # mirrors Data.xml

    if data.get("issn_online"):
        _text(SubElement(jm, "issn", {"pub-type": "epub"}), data["issn_online"])
    if data.get("issn_print"):
        _text(SubElement(jm, "issn", {"pub-type": "ppub"}), data["issn_print"])

    pub = SubElement(jm, "publisher")
    _text(SubElement(pub, "publisher-name"), data.get("publisher_name", "Novel Future Publishers Inc."))
    _text(SubElement(pub, "publisher-loc"),  data.get("publisher_loc", "Canada"))


# ---------------------------------------------------------------------------
# article-meta
# ---------------------------------------------------------------------------

def _build_article_meta(front: Element, data: dict):
    am = SubElement(front, "article-meta")

    # DOI
    if data.get("doi"):
        _text(SubElement(am, "article-id", {"pub-id-type": "doi"}), data["doi"])

    # Categories
    cats = SubElement(am, "article-categories")
    sg   = SubElement(cats, "subj-group")
    _text(SubElement(sg, "subject"), data.get("article_type", "Research Article"))

    # Title
    tg = SubElement(am, "title-group")
    _mixed(SubElement(tg, "article-title"), data.get("title", "Untitled"))

    # Authors + affiliations
    authors = data.get("authors") or []
    if authors:
        _build_contribs(am, authors)

    # author-notes (corresponding authors)
    corresp_authors = [a for a in authors if a.get("corresponding")]
    if corresp_authors:
        an = SubElement(am, "author-notes")
        for i, a in enumerate(corresp_authors):
            full = f"{a.get('first_name','')} {a.get('last_name','')}".strip()
            aff  = a.get("affiliation", "")
            email = a.get("email", "")
            parts = ", ".join(filter(None, [full, aff, email]))
            _text(SubElement(an, "corresp", {"id": f"cor-{i}"}),
                  f"Corresponding author: {parts}")

    # Pub dates – matches Data.xml: one "pub" + one "collection"
    pub_year  = str(data.get("pub_date_year") or "")
    pub_month = str(data.get("pub_date_month") or "")
    pub_day   = str(data.get("pub_date_day")   or "")
    rec_date  = data.get("published_date") or data.get("received_date") or ""

    if pub_year:
        iso = f"{pub_year}"
        if pub_month: iso += f"-{pub_month}"
        if pub_day:   iso += f"-{pub_day}"
        pd = SubElement(am, "pub-date", {
            "publication-format": "electronic",
            "date-type": "pub",
            "iso-8601-date": iso,
        })
        if pub_day:   _text(SubElement(pd, "day"),   pub_day)
        if pub_month: _text(SubElement(pd, "month"), pub_month)
        _text(SubElement(pd, "year"), pub_year)

        # collection date = received/published (use same year if nothing else)
        col_iso = rec_date or pub_year
        col_pd  = SubElement(am, "pub-date", {
            "publication-format": "electronic",
            "date-type": "collection",
            "iso-8601-date": col_iso,
        })
        _text(SubElement(col_pd, "year"), col_iso[:4] if len(col_iso) >= 4 else col_iso)

    if data.get("volume"):
        _text(SubElement(am, "volume"), str(data["volume"]))
    if data.get("issue"):
        _text(SubElement(am, "issue"), str(data["issue"]))

    # History dates
    if data.get("received_date") or data.get("accepted_date"):
        hist = SubElement(am, "history")
        if data.get("received_date"):
            _date_element(hist, "received", data["received_date"])
        if data.get("accepted_date"):
            _date_element(hist, "accepted", data["accepted_date"])

    # Permissions — matches Data.xml structure exactly
    year_str = pub_year or "2026"
    perms = SubElement(am, "permissions")
    _text(SubElement(perms, "copyright-statement"), data.get("copyright_statement",
        f"© {year_str} The Author(s). Published by Novel Future Publishers Inc. "
        "This article is licensed under CC BY 4.0."))
    _text(SubElement(perms, "copyright-year"),   year_str)
    _text(SubElement(perms, "copyright-holder"), f"© {year_str} by the Author(s)")
    lic = SubElement(perms, "license", {
        "license-type": "open-access",
        "href": "https://creativecommons.org/licenses/by/4.0/",   # no xlink: prefix — matches Data.xml
    })
    _text(SubElement(lic, "license_ref"), "https://creativecommons.org/licenses/by/4.0/")
    _text(SubElement(lic, "license-p"),
          "This work is licensed under a Creative Commons Attribution 4.0 International License.")

    # Abstract
    if data.get("abstract"):
        abstract = SubElement(am, "abstract")
        _mixed(SubElement(abstract, "p"), data["abstract"])

    # Keywords
    if data.get("keywords"):
        kwg = SubElement(am, "kwd-group", {"kwd-group-type": "author-keywords"})
        for kw in data["keywords"]:
            _text(SubElement(kwg, "kwd"), kw)


def _build_contribs(am: Element, authors: list):
    """
    Build contrib-group with xref→aff links, then aff elements at article-meta
    level — matching Data.xml's structure exactly.
    """
    cg = SubElement(am, "contrib-group")

    # Build a unique-affiliation index (same text → same AFF-N id)
    aff_index: dict[str, int] = {}
    aff_counter = [0]

    def aff_id(text: str) -> str:
        if text not in aff_index:
            aff_counter[0] += 1
            aff_index[text] = aff_counter[0]
        return f"AFF-{aff_index[text]}"

    corresp_idx: dict[int, int] = {}  # author index → cor-N id
    corresp_counter = [0]

    for author_i, author in enumerate(authors):
        contrib = SubElement(cg, "contrib", {"contrib-type": "author"})

        name = SubElement(contrib, "name")
        _text(SubElement(name, "surname"),     author.get("last_name",  ""))
        _text(SubElement(name, "given-names"), author.get("first_name", ""))

        if author.get("orcid"):
            _text(SubElement(contrib, "contrib-id", {"contrib-id-type": "orcid"}),
                  author["orcid"])

        # address (country + email) — mirrors Data.xml
        addr = SubElement(contrib, "address")
        if author.get("affiliation"):
            # Try to extract country from affiliation string (last comma-separated part)
            parts = [p.strip() for p in author["affiliation"].split(",")]
            _text(SubElement(addr, "country"), parts[-1] if parts else "")
        if author.get("email"):
            _text(SubElement(addr, "email"), author["email"])

        # xref → affiliation
        if author.get("affiliation"):
            aid = aff_id(author["affiliation"])
            SubElement(contrib, "xref", {"rid": aid, "ref-type": "aff"})

        # xref → corresp (for corresponding authors)
        if author.get("corresponding"):
            cor_n = corresp_counter[0]
            corresp_idx[author_i] = cor_n
            corresp_counter[0] += 1
            SubElement(contrib, "xref", {"ref-type": "corresp", "rid": f"cor-{cor_n}"})

    # Emit <aff> elements at article-meta level (after contrib-group)
    # sorted by their AFF-N id
    for aff_text, n in sorted(aff_index.items(), key=lambda x: x[1]):
        aff_el = SubElement(am, "aff", {"id": f"AFF-{n}"})
        # Try to parse "Department, Institution, City, Country"
        parts = [p.strip() for p in aff_text.split(",")]
        if len(parts) >= 2:
            _text(SubElement(aff_el, "institution"), parts[0])
            SubElement(aff_el, "institution-wrap")   # empty placeholder — mirrors Data.xml
            if len(parts) >= 3:
                _text(SubElement(aff_el, "addr-line"), ", ".join(parts[1:-1]))
            _text(SubElement(aff_el, "country"), parts[-1])
        else:
            aff_el.text = aff_text   # fallback: plain text


# ---------------------------------------------------------------------------
# body
# ---------------------------------------------------------------------------

def _build_body(body: Element, data: dict):
    sections    = data.get("sections", [])
    fig_counter = [0]   # globally consistent figure numbering
    eq_counter  = [0]   # globally consistent equation numbering

    for section in sections:
        sec = SubElement(body, "sec")
        sec_type = section.get("type", "Other")
        if sec_type and sec_type != "Other":
            sec.set("sec-type", sec_type.lower())

        if section.get("heading"):
            _mixed(SubElement(sec, "title"), section["heading"])

        _append_content_blocks(sec, section, data, fig_counter, eq_counter)

        for sub in section.get("subsections", []):
            subsec = SubElement(sec, "sec")
            if sub.get("heading"):
                _mixed(SubElement(subsec, "title"), sub["heading"])
            _append_content_blocks(subsec, sub, data, fig_counter, eq_counter)


def _append_content_blocks(parent: Element, sec: dict, data: dict,
                           fig_counter: list, eq_counter: list):
    """Write paragraphs, figures, equations, and tables from content-array or legacy body string."""
    content = sec.get("content")
    if content:
        for block in content:
            btype = block.get("type")
            if btype == "paragraph":
                text = (block.get("text") or "").strip()
                if text:
                    _mixed(SubElement(parent, "p"), text)
            elif btype == "figure":
                fig_counter[0] += 1
                _inline_fig(parent, block, data, fig_counter[0])
            elif btype == "equation":
                eq_counter[0] += 1
                _inline_eq(parent, block, data, eq_counter[0])
            elif btype == "table":
                _inline_table(parent, block)
    elif sec.get("body"):
        for para_text in _split_paragraphs(sec["body"]):
            _mixed(SubElement(parent, "p"), para_text)


def _inline_fig(parent: Element, block: dict, data: dict, n: int):
    """
    Emit a JATS <fig> element.
    - id:      figure-N   (matches Data.xml pattern)
    - graphic: href = canonical filename (e.g. Novel_Energy-1-1-g3.jpeg)
               mimetype / mime-subtype attributes (no data URI in XML)
    The actual image bytes live in block['data_uri'] and are exported
    separately via the ZIP endpoint.
    """
    label   = block.get("label") or f"Figure {n}"
    caption = block.get("caption", "")
    fname   = fig_filename(data, n)

    fig_el = SubElement(parent, "fig", {"id": f"figure-{n}"})
    _mixed(SubElement(fig_el, "label"), label)
    if caption:
        cap = SubElement(fig_el, "caption")
        _mixed(SubElement(cap, "p"), caption)
    SubElement(fig_el, "graphic", {
        "href":         fname,
        "mimetype":     "image",
        "mime-subtype": "jpeg",
    })


def _inline_eq(parent: Element, block: dict, data: dict, n: int):
    """
    Emit a JATS <disp-formula> for a display equation.
    The image file is named using eq_filename() and exported in the XML ZIP.
    """
    fname = eq_filename(data, n)
    eq_el = SubElement(parent, "disp-formula", {"id": f"E{n}"})
    SubElement(eq_el, "graphic", {
        "href":         fname,
        "mimetype":     "image",
        "mime-subtype": "png",
    })


def _inline_table(parent: Element, block: dict):
    """Emit a JATS <table-wrap> element inline in the body section."""
    label   = block.get("label", "")
    caption = block.get("caption", label)
    headers = block.get("headers", [])
    rows    = block.get("rows", [])

    tw = SubElement(parent, "table-wrap")
    if label:
        _mixed(SubElement(tw, "label"), label)
    if caption and caption != label:
        cap = SubElement(tw, "caption")
        _mixed(SubElement(cap, "p"), caption)
    if headers or rows:
        tbl = SubElement(tw, "table")
        if headers:
            thead = SubElement(tbl, "thead")
            tr = SubElement(thead, "tr")
            for h in headers:
                _mixed(SubElement(tr, "th"), h or "")
        if rows:
            tbody = SubElement(tbl, "tbody")
            for row in rows:
                tr = SubElement(tbody, "tr")
                for cell in row:
                    _mixed(SubElement(tr, "td"), cell or "")


# ---------------------------------------------------------------------------
# back (references only — figures are inline in body)
# ---------------------------------------------------------------------------

def _build_back(back: Element, data: dict):
    refs = data.get("references", [])
    if not refs:
        return

    rl = SubElement(back, "ref-list")
    _text(SubElement(rl, "title"), "References")

    for i, ref in enumerate(refs, 1):
        if isinstance(ref, dict):
            ref_text = ref.get("raw_text", "")
            doi      = ref.get("doi", "")
        else:
            ref_text, doi = ref, ""

        # Use BIBR-N id format to match Data.xml
        ref_el = SubElement(rl, "ref", {"id": f"BIBR-{i}"})
        mc = SubElement(ref_el, "mixed-citation", {"publication-type": "article-journal"})
        _mixed(mc, ref_text)
        if doi:
            _text(SubElement(mc, "pub-id", {"pub-id-type": "doi"}), doi)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _date_element(parent: Element, date_type: str, date_str: str):
    el    = SubElement(parent, "date", {"date-type": date_type})
    parts = str(date_str).split("-")
    if len(parts) == 3:
        _text(SubElement(el, "day"),   parts[2])
        _text(SubElement(el, "month"), parts[1])
        _text(SubElement(el, "year"),  parts[0])
    else:
        _text(SubElement(el, "year"), str(date_str))


def _split_paragraphs(text: str) -> list:
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    return paras if paras else [text]


def _text(el: Element, value: str) -> Element:
    el.text = str(value) if value else ""
    return el


# Citation marker pattern: [1], [1,2], [1, 2, 3], [1-3], [1–5]
_CITE_RE = re.compile(r'\[(\d[\d,;\s–—\-]*\d|\d)\]')


def _mixed(el: Element, text: str) -> Element:
    """
    Set element content as proper JATS XML mixed content:
      - <sub>…</sub> / <sup>…</sup> HTML tags from the parser
        → real XML <sub>/<sup> child elements
      - [N] / [N,M] / [N-M] citation markers
        → <xref ref-type="bibr" rid="BIBR-N"><sup>N</sup></xref>

    Falls back to plain text if the XML fragment cannot be parsed.
    """
    if not text:
        el.text = ""
        return el

    # 1. Convert [N] / [N,M] citation markers to xref XML markup
    def _cite_to_xref(m):
        nums = re.findall(r'\d+', m.group(1))
        # Handle ranges like [1-3] → expand to 1,2,3
        raw = m.group(1)
        if re.search(r'[\-–—]', raw) and len(nums) == 2:
            try:
                nums = [str(n) for n in range(int(nums[0]), int(nums[1]) + 1)]
            except ValueError:
                pass
        return ''.join(
            f'<xref ref-type="bibr" rid="BIBR-{n}"><sup>{n}</sup></xref>'
            for n in nums
        )

    marked = _CITE_RE.sub(_cite_to_xref, text)

    # 2. Ensure any bare & not already an entity is escaped for XML parsing
    safe = re.sub(r'&(?!(?:amp|lt|gt|quot|apos);)', '&amp;', marked)

    # 3. Parse as an XML fragment and copy children into el
    try:
        frag = fromstring(f'<r>{safe}</r>')
        el.text = frag.text
        for child in frag:
            el.append(child)
    except Exception:
        # Fallback: strip all markup and store as plain text
        el.text = re.sub(r'<[^>]+>', '', text)

    return el


def _prettify(xml_str: str) -> str:
    try:
        dom   = minidom.parseString(f"<root>{xml_str}</root>")
        inner = dom.documentElement
        lines = [child.toprettyxml(indent="  ") for child in inner.childNodes]
        pretty = "\n".join(lines)
        pretty = re.sub(r"\n\s*\n", "\n", pretty)
        return pretty
    except Exception:
        return xml_str
