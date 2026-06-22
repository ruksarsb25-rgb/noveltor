"""
Abstract Collection Parser — Abstract-label-centric, backward-scan approach.

Each "Abstract" label paragraph is used as the primary boundary anchor.

For each label:
  1. Scan BACKWARD up to BACK_LIMIT paragraphs to find the title
     (last bold or 14pt+ paragraph that isn't an author/affiliation line).
  2. Everything between that title paragraph and the label = author/affil block.
  3. Scan FORWARD from the label to collect the abstract body and keywords,
     stopping at the next "Abstract" label.
"""

import re
from docx import Document

_KEYWORDS_RE        = re.compile(r'^key\s*words?\s*[:\-]?\s*', re.IGNORECASE)
_ABSTRACT_LABEL_RE  = re.compile(r'^abstract\s*[:\-]?\s*$', re.IGNORECASE)
_ABSTRACT_PACKED_RE = re.compile(r'^abstract\s*[:\-]?\s*\n', re.IGNORECASE)
_EMAIL_RE           = re.compile(r'[\w.+-]+@[\w.-]+\.\w+')
_CORRESP_RE         = re.compile(r'(corresponding\s+author|e[\-\s]?mail\s*:)', re.IGNORECASE)
_AFFIL_NUM_RE       = re.compile(r'^[\d¹²³⁴⁵⁶⁷⁸⁹⁰*†‡§abcde]+(?=\s|[A-Z]|\.|\)|,|$)')

BACK_LIMIT = 20   # paragraphs to scan backward from an Abstract label


def _max_font_pt(p) -> float:
    sizes = [r.font.size.pt for r in p.runs if r.font.size and r.text.strip()]
    return max(sizes) if sizes else 0.0


def _any_bold(p) -> bool:
    return any(r.bold for r in p.runs if r.text.strip())


def _split_packed(p) -> list:
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


def _is_abstract_label(text: str, raw: str = "") -> bool:
    return bool(_ABSTRACT_LABEL_RE.match(text)) or bool(_ABSTRACT_PACKED_RE.match(raw))


def _is_keywords(text: str) -> bool:
    return bool(_KEYWORDS_RE.match(text))


def _is_author_affil_line(text: str) -> bool:
    if not text:
        return False
    if _CORRESP_RE.search(text):
        return True
    if _EMAIL_RE.search(text) and len(text) < 120:
        return True
    if _AFFIL_NUM_RE.match(text):
        return True
    return False


def _looks_like_title(text: str, p) -> bool:
    if _is_author_affil_line(text):
        return False
    if _max_font_pt(p) >= 13.5:
        return True
    if _any_bold(p) and len(text) >= 10:
        return True
    return False


_INST_RE = re.compile(
    r'\b(Department|Dept|University|College|Institute|School|Laboratory|'
    r'Centre|Center|Division|Faculty|Hospital|Academy|Foundation)\b',
    re.IGNORECASE,
)


def _parse_author_block(raw_lines: list) -> dict:
    authors, affiliations, email = [], [], ""
    authors_str = ""

    print(f"DEBUG: raw_lines count = {len(raw_lines)}")
    for i, l in enumerate(raw_lines):
        print(f"DEBUG: raw_lines[{i}] = {l[:80]}...")

    for line in raw_lines:
        if _CORRESP_RE.search(line):
            m = _EMAIL_RE.search(line)
            if m:
                email = m.group(0)
        elif _EMAIL_RE.match(line.lstrip('* ')):
            m = _EMAIL_RE.search(line)
            if m:
                email = m.group(0)
        elif _AFFIL_NUM_RE.match(line):
            affiliations.append(line)
        elif not authors_str:
            authors_str = line
        else:
            # Check if line looks like continuation of author names or an affiliation
            # If line contains commas/and and doesn't start with institution keyword, treat as author line
            if (',' in line or ' and ' in line.lower() or ' & ' in line) and not _INST_RE.search(line.split(',')[0]):
                authors_str = authors_str + " " + line
            else:
                # Affiliation line
                affiliations.append(line)

    # ── Strip institution text appended after the last author ─────────────────
    # e.g. "Smith J, Jones A* Department of Chemistry, Univ of X, India"
    # Split at first institution keyword that follows an author-name pattern.
    inst_split = _INST_RE.search(authors_str)
    if inst_split:
        aff_part = authors_str[inst_split.start():].strip()
        authors_str = authors_str[:inst_split.start()].strip().rstrip('*†‡,')
        if aff_part:
            affiliations.insert(0, aff_part)

    print(f"DEBUG: authors_str before normalize = {authors_str[:100]}...")
    # ── Normalise "2*and" / "2and" → "2* and " so the split below works ────────
    authors_str = re.sub(r'([\d¹²³⁴⁵⁶⁷⁸⁹⁰*†‡§]+)\s*and\b', r'\1 and ', authors_str)

    # ── Split on commas AND "and" / "&" ──────────────────────────────────────
    raw_names = re.split(r',\s*|\s+and\s+|\s*&\s*', authors_str)
    print(f"DEBUG: split resulted in {len(raw_names)} names")

    for name in raw_names:
        # Strip leading "and" artifacts from split, trailing superscripts/punctuation
        name_clean = re.sub(r'^and\s+', '', name, flags=re.IGNORECASE)
        name_clean = re.sub(r'[\d¹²³⁴⁵⁶⁷⁸⁹⁰*†‡§\[\]\(\),]+$', '', name_clean)
        # Strip trailing single-letter affiliation markers (a, b, c, etc.)
        name_clean = re.sub(r'\s+[a-d]\s*$', '', name_clean)
        name_clean = re.sub(r'\s+', ' ', name_clean).strip()

        if not name_clean or len(name_clean) < 2:
            continue

        # Skip lines that are actually institution names
        if _INST_RE.search(name_clean):
            affiliations.append(name_clean)
            continue

        # Split "FirstName/Initials LastName"
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


def parse_abstract_collection(path: str) -> dict:
    doc = Document(path)
    paras = doc.paragraphs

    # ── Locate all Abstract label positions ──────────────────────────────────
    label_positions = []
    for i, p in enumerate(paras):
        text = p.text.strip()
        if _is_abstract_label(text, p.text):
            label_positions.append(i)

    label_set = set(label_positions)   # for quick lookup

    abstracts   = []
    seen_titles = set()

    for k, ab_idx in enumerate(label_positions):

        # ── Backward scan: find the title paragraph ───────────────────────────
        scan_start = max(0, ab_idx - BACK_LIMIT)
        # Don't cross a previous abstract label
        if k > 0:
            scan_start = max(scan_start, label_positions[k - 1] + 1)

        # Collect non-empty paras in the backward window
        block = []
        for j in range(scan_start, ab_idx):
            text = paras[j].text.strip()
            if text and j not in label_set:
                block.append((j, text, paras[j]))

        # Find the title: last bold/14pt paragraph that is not a keywords line
        title_block_idx = None
        for bi in range(len(block) - 1, -1, -1):
            j, text, p = block[bi]
            if not _is_keywords(text) and _looks_like_title(text, p):
                title_block_idx = bi
                break

        # Fallback: first paragraph that isn't an author/affil/corresp/keywords line
        if title_block_idx is None:
            for bi, (j, text, p) in enumerate(block):
                if not _is_author_affil_line(text) and not _is_keywords(text):
                    title_block_idx = bi
                    break

        if title_block_idx is None:
            continue   # can't determine a title — skip

        # ── Extract title (handle packed paragraphs) ─────────────────────────
        title_j, title_text, title_p = block[title_block_idx]
        packed_lines = _split_packed(title_p)
        title = packed_lines[0] if packed_lines else title_text

        # ── Build author block (everything after title para up to label) ──────
        author_lines = list(packed_lines[1:]) if len(packed_lines) > 1 else []
        for bi in range(title_block_idx + 1, len(block)):
            author_lines.append(block[bi][1])

        # ── Forward scan: collect abstract body and keywords ─────────────────
        abstract_text = ""
        keywords      = []

        # Handle packed label ("Abstract\nBody text…")
        ab_packed = _split_packed(paras[ab_idx])
        if len(ab_packed) > 1:
            abstract_text = " ".join(ab_packed[1:])

        next_label = label_positions[k + 1] if k + 1 < len(label_positions) else len(paras)
        for j in range(ab_idx + 1, next_label):
            text = paras[j].text.strip()
            if not text:
                continue
            if _is_keywords(text):
                kw_raw   = _KEYWORDS_RE.sub("", text)
                keywords = [w.strip() for w in re.split(r'[,;]', kw_raw) if w.strip()]
                break
            if j in label_set:
                break
            abstract_text = (abstract_text + " " + text).strip()

        # ── Quality filter & deduplication ───────────────────────────────────
        title_key = re.sub(r'\W+', '', title).lower()
        if (abstract_text.strip()
                and len(title) >= 10
                and title_key not in seen_titles):
            seen_titles.add(title_key)
            parsed = _parse_author_block(author_lines)
            abstracts.append({
                "title":        title,
                "authors":      parsed["authors"],
                "affiliations": parsed["affiliations"],
                "email":        parsed.get("email", ""),
                "abstract":     abstract_text.strip(),
                "keywords":     keywords,
            })

    doc_title = next((p.text.strip() for p in paras if p.text.strip()), "")
    return {
        "type":      "abstract_collection",
        "doc_title": doc_title,
        "abstracts": abstracts,
    }
