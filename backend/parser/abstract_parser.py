"""
Abstract Collection Parser
Parses a single DOCX containing multiple conference abstracts.

Detection strategy:
  • Every paragraph whose maximum run font size is ≥ 13.5 pt is treated as
    a title paragraph (regardless of bold).  Many authors set the font to 14 pt
    but leave individual runs non-bold.
  • Consecutive 14 pt paragraphs with no intervening content are merged into
    a single title (handles split titles like "Very Long Title:" / "Subtitle").
  • If the current abstract has not yet received an "Abstract" label and a new
    14 pt paragraph is encountered, the new paragraph is appended to the
    existing title (continuation handling).
  • Packed paragraphs (title + authors in one paragraph via soft \\n line-breaks)
    are split on \\n to extract author/affiliation lines from the title paragraph.
  • De-duplication: if the same normalised title appears twice (duplicate
    abstracts copied in the document), only the first occurrence is kept.
"""

import re
from docx import Document

_KEYWORDS_RE        = re.compile(r'^key\s*words?\s*[:\-]?\s*', re.IGNORECASE)
_ABSTRACT_LABEL_RE  = re.compile(r'^abstract\s*[:\-]?\s*$', re.IGNORECASE)
_ABSTRACT_PACKED_RE = re.compile(r'^abstract\s*[:\-]?\s*\n', re.IGNORECASE)
_EMAIL_RE           = re.compile(r'[\w.+-]+@[\w.-]+\.\w+')
_CORRESP_RE         = re.compile(r'(corresponding\s+author|e[\-\s]?mail\s*:)', re.IGNORECASE)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _max_font_pt(p) -> float:
    sizes = [r.font.size.pt for r in p.runs if r.font.size and r.text.strip()]
    return max(sizes) if sizes else 0.0


def _split_packed(p) -> list:
    """Split a paragraph that uses soft \\n line-breaks into logical lines."""
    lines, current = [], []
    for run in p.runs:
        for k, part in enumerate(run.text.split('\n')):
            if k > 0:
                lines.append("".join(current).strip())
                current = []
            if part:
                current.append(part)
    if current:
        lines.append("".join(current).strip())
    return [l for l in lines if l]


def _is_abstract_label(text: str) -> bool:
    return bool(_ABSTRACT_LABEL_RE.match(text.strip()))


def _is_abstract_packed(raw: str) -> bool:
    return bool(_ABSTRACT_PACKED_RE.match(raw))


def _is_keywords(text: str) -> bool:
    return bool(_KEYWORDS_RE.match(text.strip()))


def _is_title_size(p) -> bool:
    """True if any run in this paragraph has font ≥ 13.5 pt."""
    return _max_font_pt(p) >= 13.5


# ── Author / affiliation parsing ──────────────────────────────────────────────

def _parse_author_block(raw_lines: list) -> dict:
    authors, affiliations, email = [], [], ""
    authors_str = ""

    for line in raw_lines:
        if _CORRESP_RE.search(line):
            m = _EMAIL_RE.search(line)
            if m:
                email = m.group(0)
        elif _EMAIL_RE.match(line.lstrip('*')):
            m = _EMAIL_RE.search(line)
            if m:
                email = m.group(0)
        elif re.match(r'^[\d¹²³⁴⁵⁶⁷⁸⁹⁰*†‡§]+[\s\.\)]', line):
            affiliations.append(line)
        elif not authors_str:
            authors_str = line
        else:
            affiliations.append(line)

    for name in re.split(r',\s*', authors_str):
        name_clean = re.sub(r'[\d¹²³⁴⁵⁶⁷⁸⁹⁰*†‡§,\s]+$', '', name).strip()
        if not name_clean or len(name_clean) < 2:
            continue
        parts = name_clean.rsplit(' ', 1)
        authors.append({
            "first_name":    parts[0] if len(parts) > 1 else name_clean,
            "last_name":     parts[-1] if len(parts) > 1 else "",
            "affiliation":   affiliations[0].strip() if affiliations else "",
            "email":         email if not authors else "",
            "orcid":         "",
            "corresponding": not bool(authors),
        })

    return {"authors": authors, "affiliations": affiliations, "email": email}


# ── Main parser ───────────────────────────────────────────────────────────────

def parse_abstract_collection(path: str) -> dict:
    doc = Document(path)
    paragraphs = doc.paragraphs

    abstracts        = []
    seen_titles      = set()   # de-duplicate
    current          = None    # abstract dict being built
    in_abstract      = False   # currently inside abstract body
    in_authors       = False   # currently inside author/affil block
    last_title_idx   = -99     # paragraph index of last title paragraph

    def _flush():
        nonlocal current
        if not current:
            return
        parsed = _parse_author_block(current.pop("_author_lines", []))
        current["authors"]      = parsed["authors"]
        current["affiliations"] = parsed["affiliations"]
        current["email"]        = parsed.get("email", "")

        title_key = re.sub(r'\W+', '', current.get("title", "")).lower()
        # Keep only entries that have abstract text and a non-trivial title,
        # and that are not exact duplicates.
        if (current.get("abstract", "").strip()
                and len(current.get("title", "")) >= 10
                and title_key not in seen_titles):
            seen_titles.add(title_key)
            abstracts.append(current)
        current = None

    for i, p in enumerate(paragraphs):
        text = p.text.strip()
        raw  = p.text          # keep embedded \n for packed detection

        # ── 14 pt title paragraph ────────────────────────────────────────────
        if _is_title_size(p) and text:
            # Skip obvious non-title 14pt lines
            if _is_abstract_label(text) or _is_keywords(text):
                pass
            else:
                # If this 14pt paragraph is immediately consecutive with the
                # previous one (gap ≤ 2 paragraphs), treat as title continuation.
                if current is not None and (i - last_title_idx) <= 2:
                    lines = _split_packed(p)
                    current["title"] = (current["title"] + " " + lines[0]).strip()
                    if len(lines) > 1:
                        current["_author_lines"].extend(lines[1:])
                    last_title_idx = i
                    continue

                # Otherwise start a new abstract
                _flush()
                in_abstract  = False
                in_authors   = True
                last_title_idx = i

                lines = _split_packed(p)
                title = lines[0] if lines else text
                rest  = lines[1:] if len(lines) > 1 else []

                current = {
                    "title":         title,
                    "_author_lines": rest,
                    "abstract":      "",
                    "keywords":      [],
                }
                continue

        if current is None:
            continue
        if not text:
            continue

        # ── Keywords ─────────────────────────────────────────────────────────
        if _is_keywords(text):
            kw_raw = _KEYWORDS_RE.sub("", text)
            current["keywords"] = [k.strip() for k in re.split(r'[,;]', kw_raw) if k.strip()]
            in_abstract = False
            continue

        # ── Abstract label (standalone or packed) ────────────────────────────
        if _is_abstract_label(text) or _is_abstract_packed(raw):
            in_abstract = True
            in_authors  = False
            lines = _split_packed(p)
            # First line is the label; remaining lines are body text
            body_lines = lines[1:] if len(lines) > 1 else []
            if body_lines:
                current["abstract"] = " ".join(body_lines)
            continue

        # ── Abstract body continuation ────────────────────────────────────────
        if in_abstract:
            current["abstract"] = (current["abstract"] + " " + text).strip()
            continue

        # ── Author / affiliation block ────────────────────────────────────────
        if in_authors:
            current["_author_lines"].append(text)

    _flush()

    doc_title = next((p.text.strip() for p in paragraphs if p.text.strip()), "")

    return {
        "type":      "abstract_collection",
        "doc_title": doc_title,
        "abstracts": abstracts,
    }
