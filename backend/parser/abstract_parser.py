"""
Abstract Collection Parser
Parses a single DOCX containing multiple conference abstracts.

Detection strategy:
  - New abstract starts at a paragraph containing a 14pt (or larger) bold run
    that is NOT the word "Abstract" / "Abstract:" (that is the section label).
  - Handles both split layouts (title / authors / abstract in separate paragraphs)
    and packed layouts (all in one paragraph with embedded \\n line-breaks).
  - Keywords line: starts with "Keywords:" or "Key words:" (case-insensitive).
  - Abstract body: follows the "Abstract" label paragraph.
"""

import re
from docx import Document

_KEYWORDS_RE = re.compile(r'^key\s*words?\s*[:\-]?\s*', re.IGNORECASE)
_ABSTRACT_LABEL_RE = re.compile(r'^abstract\s*[:\-]?\s*', re.IGNORECASE)
_EMAIL_RE = re.compile(r'[\w.+-]+@[\w.-]+\.\w+')
_CORRESP_RE = re.compile(r'corresponding\s+author', re.IGNORECASE)


def _max_font_pt(p) -> float:
    """Return the largest font size (in pt) among all non-empty runs in paragraph."""
    sizes = [r.font.size.pt for r in p.runs if r.font.size and r.text.strip()]
    return max(sizes) if sizes else 0.0


def _all_bold(p) -> bool:
    """True if every non-empty run in the paragraph is bold."""
    runs = [r for r in p.runs if r.text.strip()]
    return bool(runs) and all(r.bold for r in runs)


def _is_title_para(p) -> bool:
    """A paragraph is a title if it has ≥13.5pt bold text and is not the Abstract label."""
    text = p.text.strip()
    if not text:
        return False
    if _ABSTRACT_LABEL_RE.match(text):
        return False
    return _max_font_pt(p) >= 13.5 and _all_bold(p)


def _split_packed(p):
    """
    Some paragraphs pack title + authors + affiliations into one paragraph
    using soft line-breaks (\\n in run text). Split them into logical lines.
    """
    # Rebuild text line-by-line preserving run order
    lines = []
    current_line = []
    for run in p.runs:
        parts = run.text.split('\n')
        for k, part in enumerate(parts):
            if k > 0:
                lines.append("".join(current_line).strip())
                current_line = []
            if part:
                current_line.append(part)
    if current_line:
        lines.append("".join(current_line).strip())
    return [l for l in lines if l]


def _guess_authors_affiliations(raw_lines: list) -> dict:
    """
    From the lines that follow the title, extract authors, affiliations,
    and corresponding email as best-effort.
    """
    authors_str = ""
    affiliations = []
    email = ""
    corresp = ""

    for line in raw_lines:
        if _CORRESP_RE.search(line) or _EMAIL_RE.search(line):
            m = _EMAIL_RE.search(line)
            if m:
                email = m.group(0)
            corresp = line
        elif re.match(r'^[\¹²³⁴⁵⁶⁷⁸⁹⁰\d*†‡§]+\s', line) or \
             re.match(r'^[a-z][\.\)]\s', line):
            # Looks like a numbered affiliation line
            affiliations.append(line)
        elif not authors_str:
            authors_str = line
        else:
            # Could be more affiliations or continuation
            affiliations.append(line)

    # Build simple author list from comma-separated names
    authors = []
    if authors_str:
        # Strip trailing superscripts from names
        for name in re.split(r',\s*', authors_str):
            name_clean = re.sub(r'[\d¹²³⁴⁵⁶⁷⁸⁹⁰*†‡§,]+$', '', name).strip()
            if name_clean and len(name_clean.split()) >= 1:
                parts = name_clean.rsplit(' ', 1)
                authors.append({
                    "first_name": parts[0] if len(parts) > 1 else name_clean,
                    "last_name":  parts[-1] if len(parts) > 1 else "",
                    "affiliation": affiliations[0].strip() if affiliations else "",
                    "email": email if not authors else "",
                    "orcid": "",
                    "corresponding": not bool(authors),
                })

    return {
        "authors": authors,
        "affiliations": affiliations,
        "email": email,
        "corresp_line": corresp,
    }


def parse_abstract_collection(path: str) -> dict:
    """
    Parse a DOCX containing multiple conference abstracts.
    Returns {"type": "abstract_collection", "abstracts": [...], "doc_title": "..."}.
    """
    doc = Document(path)

    abstracts = []
    current = None          # dict being built
    in_abstract_body = False
    in_authors_block = True

    def _save_current():
        if current:
            parsed = _guess_authors_affiliations(current.get("_author_lines", []))
            current["authors"]      = parsed["authors"]
            current["affiliations"] = parsed["affiliations"]
            current["email"]        = parsed.get("email", "")
            current.pop("_author_lines", None)
            abstracts.append(current)

    for p in doc.paragraphs:
        text = p.text.strip()

        # ── New abstract boundary ────────────────────────────────────────────
        if _is_title_para(p):
            _save_current()
            in_abstract_body = False
            in_authors_block = True

            lines = _split_packed(p)
            title = lines[0] if lines else text

            # If the packed paragraph has multiple lines, rest may be authors
            rest_lines = lines[1:] if len(lines) > 1 else []

            current = {
                "title":         title,
                "_author_lines": rest_lines,
                "abstract":      "",
                "keywords":      [],
            }
            continue

        if current is None:
            continue

        if not text:
            continue

        # ── Keywords ─────────────────────────────────────────────────────────
        if _KEYWORDS_RE.match(text):
            kw_raw = _KEYWORDS_RE.sub("", text)
            current["keywords"] = [k.strip() for k in re.split(r'[,;]', kw_raw) if k.strip()]
            in_abstract_body = False
            continue

        # ── Abstract label / body ─────────────────────────────────────────────
        if _ABSTRACT_LABEL_RE.match(text):
            # The label line may also carry abstract text after it
            after_label = _ABSTRACT_LABEL_RE.sub("", text).strip()
            # Handle packed: "Abstract \nText here..."
            if '\n' in p.text:
                packed_lines = _split_packed(p)
                # First line is the label, rest is abstract text
                body_lines = packed_lines[1:] if len(packed_lines) > 1 else []
                after_label = " ".join(body_lines).strip() or after_label
            if after_label:
                current["abstract"] = after_label
            in_abstract_body = True
            in_authors_block = False
            continue

        # ── Abstract body continuation ────────────────────────────────────────
        if in_abstract_body:
            current["abstract"] = (current["abstract"] + " " + text).strip()
            continue

        # ── Authors / affiliations block ──────────────────────────────────────
        if in_authors_block:
            current["_author_lines"].append(text)

    _save_current()

    # Try to derive a document title from the first non-blank paragraph
    doc_title = ""
    for p in doc.paragraphs:
        t = p.text.strip()
        if t:
            doc_title = t
            break

    return {
        "type":      "abstract_collection",
        "doc_title": doc_title,
        "abstracts": abstracts,
    }
