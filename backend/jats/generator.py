"""
JATS XML generator — NISO Z39.96, Publishing DTD v1.3.
Accepts structured article data dict and returns a valid JATS XML string.
"""
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import re


ARTICLE_TYPE_MAP = {
    "Research Article": "research-article",
    "Review": "review-article",
    "Conference Proceeding": "proceedings-paper",
    "Enhanced Poster Article": "poster",
    "Conference Report": "conference-report",
}


def generate_jats(data: dict) -> str:
    article_type = ARTICLE_TYPE_MAP.get(data.get("article_type", "Conference Proceeding"), "proceedings-paper")

    root = Element("article")
    root.set("xmlns:xlink", "http://www.w3.org/1999/xlink")
    root.set("xmlns:mml", "http://www.w3.org/1998/Math/MathML")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("article-type", article_type)
    root.set("xml:lang", "en")
    root.set("dtd-version", "1.3")

    front = SubElement(root, "front")
    _build_journal_meta(front, data)
    _build_article_meta(front, data)

    body = SubElement(root, "body")
    _build_body(body, data.get("sections", []))

    back = SubElement(root, "back")
    _build_back(back, data)

    raw = tostring(root, encoding="unicode", xml_declaration=False)
    pretty = _prettify(raw)

    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.3 20210610//EN" "https://jats.nlm.nih.gov/publishing/1.3/JATS-journalpublishing1-3.dtd">\n' + pretty


def _build_journal_meta(front: Element, data: dict):
    jm = SubElement(front, "journal-meta")
    _text(SubElement(jm, "journal-id", {"journal-id-type": "publisher-id"}), data.get("journal_id", "nfp"))

    jt = SubElement(jm, "journal-title-group")
    _text(SubElement(jt, "journal-title"), data.get("journal_name", "Novel Future Proceedings"))

    if data.get("issn_print"):
        _text(SubElement(jm, "issn", {"pub-type": "ppub"}), data["issn_print"])
    if data.get("issn_online"):
        _text(SubElement(jm, "issn", {"pub-type": "epub"}), data["issn_online"])

    pub = SubElement(jm, "publisher")
    _text(SubElement(pub, "publisher-name"), data.get("publisher_name", "Novel Future Publishers Inc."))
    _text(SubElement(pub, "publisher-loc"), data.get("publisher_loc", "Canada"))


def _build_article_meta(front: Element, data: dict):
    am = SubElement(front, "article-meta")

    if data.get("doi"):
        ids = SubElement(am, "article-id", {"pub-id-type": "doi"})
        ids.text = data["doi"]

    # Article categories
    cats = SubElement(am, "article-categories")
    subj = SubElement(cats, "subj-group", {"subj-group-type": "heading"})
    _text(SubElement(subj, "subject"), data.get("article_type", "Conference Proceeding"))

    # Title
    tg = SubElement(am, "title-group")
    _text(SubElement(tg, "article-title"), data.get("title", "Untitled"))

    # Authors
    if data.get("authors"):
        cg = SubElement(am, "contrib-group")
        for idx, author in enumerate(data["authors"]):
            contrib = SubElement(cg, "contrib", {"contrib-type": "author"})
            if author.get("corresponding"):
                contrib.set("corresp", "yes")
            name = SubElement(contrib, "name")
            _text(SubElement(name, "surname"), author.get("last_name", ""))
            _text(SubElement(name, "given-names"), author.get("first_name", ""))
            if author.get("orcid"):
                orcid = SubElement(contrib, "contrib-id", {"contrib-id-type": "orcid"})
                orcid.text = author["orcid"]
            if author.get("email"):
                _text(SubElement(contrib, "email"), author["email"])
            if author.get("affiliation"):
                aff = SubElement(contrib, "aff")
                aff.text = author["affiliation"]

    # Publication dates
    if data.get("pub_date_year"):
        pd = SubElement(am, "pub-date", {"pub-type": "epub"})
        if data.get("pub_date_day"):
            _text(SubElement(pd, "day"), str(data["pub_date_day"]))
        if data.get("pub_date_month"):
            _text(SubElement(pd, "month"), str(data["pub_date_month"]))
        _text(SubElement(pd, "year"), str(data["pub_date_year"]))

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

    # Permissions
    perms = SubElement(am, "permissions")
    _text(SubElement(perms, "copyright-statement"), data.get("copyright_statement",
        "© 2026 Novel Future Publishers Inc. Open Access article under CC BY 4.0 license."))
    lic = SubElement(perms, "license", {"license-type": "open-access",
                                         "xlink:href": "https://creativecommons.org/licenses/by/4.0/"})
    lp = SubElement(lic, "license-p")
    lp.text = "This article is distributed under the terms of the Creative Commons Attribution 4.0 International License."

    # Abstract
    if data.get("abstract"):
        abstract = SubElement(am, "abstract")
        _text(SubElement(abstract, "p"), data["abstract"])

    # Keywords
    if data.get("keywords"):
        kwg = SubElement(am, "kwd-group", {"kwd-group-type": "author-keywords"})
        for kw in data["keywords"]:
            _text(SubElement(kwg, "kwd"), kw)


def _build_body(body: Element, sections: list):
    for section in sections:
        sec = SubElement(body, "sec")
        sec_type = section.get("type", "Other")
        if sec_type and sec_type != "Other":
            sec.set("sec-type", sec_type.lower())

        if section.get("heading"):
            _text(SubElement(sec, "title"), section["heading"])

        _append_content_blocks(sec, section)

        for sub in section.get("subsections", []):
            subsec = SubElement(sec, "sec")
            if sub.get("heading"):
                _text(SubElement(subsec, "title"), sub["heading"])
            _append_content_blocks(subsec, sub)


def _append_content_blocks(parent: Element, sec: dict):
    """Write paragraphs (and skip tables) from either content-array or legacy body string."""
    content = sec.get("content")
    if content:
        for block in content:
            if block.get("type") == "paragraph":
                text = (block.get("text") or "").strip()
                if text:
                    _text(SubElement(parent, "p"), text)
            # Tables are represented inline in JATS via <table-wrap>; skipped here for now
    elif sec.get("body"):
        for para_text in _split_paragraphs(sec["body"]):
            _text(SubElement(parent, "p"), para_text)


def _build_back(back: Element, data: dict):
    refs = data.get("references", [])
    figs = data.get("figures", [])

    if figs:
        for fig in figs:
            fig_el = SubElement(back, "fig", {"id": fig.get("id", "fig1")})
            _text(SubElement(fig_el, "label"), fig.get("label", "Figure"))
            cap = SubElement(fig_el, "caption")
            _text(SubElement(cap, "p"), fig.get("caption", ""))
            SubElement(fig_el, "graphic", {"xlink:href": fig.get("href", "figure.png")})

    if refs:
        rl = SubElement(back, "ref-list")
        _text(SubElement(rl, "title"), "References")
        for i, ref in enumerate(refs, 1):
            # Support both legacy string refs and new {number, raw_text, doi} dicts
            if isinstance(ref, dict):
                ref_id  = f"ref{ref.get('number', i)}"
                ref_text = ref.get("raw_text", "")
                doi     = ref.get("doi", "")
            else:
                ref_id, ref_text, doi = f"ref{i}", ref, ""

            ref_el = SubElement(rl, "ref", {"id": ref_id})
            mc = SubElement(ref_el, "mixed-citation")
            mc.text = ref_text
            if doi:
                pub_id = SubElement(ref_el, "pub-id", {"pub-id-type": "doi"})
                pub_id.text = doi


def _date_element(parent: Element, date_type: str, date_str: str):
    el = SubElement(parent, "date", {"date-type": date_type})
    parts = str(date_str).split("-")
    if len(parts) == 3:
        _text(SubElement(el, "day"), parts[2])
        _text(SubElement(el, "month"), parts[1])
        _text(SubElement(el, "year"), parts[0])
    else:
        _text(SubElement(el, "year"), str(date_str))


def _split_paragraphs(text: str) -> list:
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    return paras if paras else [text]


def _text(el: Element, value: str) -> Element:
    el.text = str(value) if value else ""
    return el


def _prettify(xml_str: str) -> str:
    try:
        dom = minidom.parseString(f"<root>{xml_str}</root>")
        inner = dom.documentElement
        result_lines = []
        for child in inner.childNodes:
            result_lines.append(child.toprettyxml(indent="  "))
        pretty = "\n".join(result_lines)
        # Remove extra blank lines minidom introduces
        pretty = re.sub(r"\n\s*\n", "\n", pretty)
        return pretty
    except Exception:
        return xml_str
