"""
DOCX parsing logic using python-docx.
Extracts structured metadata and content from academic manuscripts.
"""
import re
from docx import Document
from docx.oxml.ns import qn as _qn

# Translate Unicode superscript digits → ASCII digits
_SUP_TO_NUM = str.maketrans('¹²³⁴⁵⁶⁷⁸⁹⁰', '1234567890')

_EMAIL_RE = re.compile(r'[\w.+-]+@[\w.-]+\.\w+')
_CORRESP_LINE_RE = re.compile(r'\*?\s*corresponding\s+authors?\s*[:\-]', re.IGNORECASE)

# Matches Unicode superscript runs OR digits glued directly to a letter (regular superscripts)
_AUTHOR_MARKER_RE = re.compile(r'([¹²³⁴⁵⁶⁷⁸⁹⁰]+,?\*?|(?<=[A-Za-z])\d+,?\*?)')

# Heading / structure detection
# Numbered heading: "1. Introduction", "2.1 Chemicals", "3.2.1 Sub" — must start capital after number
_NUMBERED_HEADING_RE = re.compile(r'^(\d+)([\.\d]*?)\.?\s+([A-Z])')
_ABSTRACT_RE = re.compile(r'^abstract\b', re.IGNORECASE)
_KEYWORDS_RE = re.compile(r'^key\s*words?\s*[:\-]', re.IGNORECASE)
# "References", "5. References", "5 References" — at end of heading
_REFS_HEADING_RE = re.compile(r'^(?:\d+[\.\d]*\.?\s+)?references?\s*$', re.IGNORECASE)
# Reference list entry: "[1] ..." or "1. ..." — numbered formats
_REF_ENTRY_RE = re.compile(r'^\[?\d+[\]\.]\s+\S')
# Bullet characters that start a reference item
_REF_BULLET_RE = re.compile(r'^[•\-\*●◆▪]\s+')
# DOI in any format: "doi: 10.xxx" or "https://doi.org/10.xxx"
_DOI_RE = re.compile(r'(?:doi:\s*|https?://doi\.org/)([^\s,;<>\)]+)', re.IGNORECASE)

_W_TBL = _qn('w:tbl')
_W_P   = _qn('w:p')
_W_T   = _qn('w:t')

# Drawing XML namespaces for inline/anchor image detection
_DRAWING_NS = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
_DRAW_A_NS  = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_REL_NS     = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
# VML namespace (older DOCX files use v:imagedata instead of DrawingML)
_VML_NS     = "{urn:schemas-microsoft-com:vml}"
_O_NS       = "{urn:schemas-microsoft-com:office:office}"
# OMML namespace for Word equations
_MATH_NS    = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"

# Figure label: Fig/Figure, optional dot, then space/hyphen/nothing, optional parens around number
_FIG_CAPTION_RE    = re.compile(r'^fig(?:ure)?\.?[\s\-]?\s*\(?\d', re.IGNORECASE)
_FIG_CAPTION_FULL  = re.compile(r'^fig(?:ure)?\.?[\s\-]?\s*\(?(\d+)\)?', re.IGNORECASE)
# Table label: same separator rules as figures
_TABLE_CAPTION_RE  = re.compile(r'^table\.?[\s\-]?\s*\(?\d', re.IGNORECASE)
_TABLE_CAPTION_FULL = re.compile(r'^table\.?[\s\-]?\s*\(?(\d+)\)?', re.IGNORECASE)
# Non-numbered items that should never get a Fig-N tag
_SKIP_FIG_RE       = re.compile(r'^(?:graphical\s+abstract|sch(?:ema|eme)(?:[-\s]\d*)?)\b', re.IGNORECASE)
# Body-text figure references: "Fig. 2 presents/shows/illustrates/is/demonstrates..."
_FIG_REF_VERB_RE   = re.compile(
    r'^fig(?:ure)?\.?[\s\-]?\s*\(?(\d+)\)?[a-z]?\s+(?:present|show|illustrat|depict|display|is\b|are\b|demonstrat)',
    re.IGNORECASE
)


def _collect_fig_captions(doc) -> dict:
    """Pre-scan entire document and return {fig_number (int): caption_text}.

    Prefers true caption lines (e.g. 'Fig. 2. SEM micrographs...') over
    body-text references (e.g. 'Fig. 2 presents the SEM...').
    """
    captions: dict[int, tuple[int, str]] = {}  # num → (priority, text); priority 0=caption,1=ref

    for p in doc.paragraphs:
        text = p.text.strip()
        m = _FIG_CAPTION_FULL.match(text)
        if not m:
            continue
        num = int(m.group(1))
        is_ref = bool(_FIG_REF_VERB_RE.match(text))
        priority = 1 if is_ref else 0  # 0 = true caption (preferred)

        existing = captions.get(num)
        if existing is None:
            captions[num] = (priority, text)
        else:
            ex_pri, ex_text = existing
            # Prefer lower priority (real caption over body ref); break ties by length
            if priority < ex_pri or (priority == ex_pri and len(text) > len(ex_text)):
                captions[num] = (priority, text)

    return {num: text for num, (_, text) in captions.items()}


def parse_docx(file_path: str) -> dict:
    doc = Document(file_path)

    fig_captions = _collect_fig_captions(doc)

    state = {
        "title": "",
        "authors_raw": "",
        "abstract": "",
        "keywords": [],
        "sections": [],
        "references": [],
        "figures": [],
    }

    _extract_structure(doc, state, fig_captions)

    return {
        "title": state["title"],
        "authors": _parse_authors(state["authors_raw"]),
        "abstract": state["abstract"],
        "keywords": state["keywords"],
        "sections": state["sections"],
        "references": _parse_references(state["references"]),
        "figures": state["figures"],
        # Journal identity is set by the editor, never inferred from manuscript content
        "journal_name": None,
        "publisher_name": None,
        "publisher_loc": None,
    }


def _classify_heading(text: str, style: str, is_bold: bool = False) -> str | None:
    """
    Return 'h1', 'h2', 'h3', or None.

    Priority order:
    1. Numbered heading regex — most reliable for NFP manuscripts:
       "1. Introduction" → h2, "2.1 Chemicals" → h3
    2. DOCX style name — used when no number prefix is present.
    """
    m = _NUMBERED_HEADING_RE.match(text)
    if m:
        sub_part = m.group(2)  # everything between first digit and the space
        # If there are digits after the first number (e.g. ".1", ".2.3"), it's a subsection
        has_sub = bool(re.search(r'\d', sub_part))
        return "h3" if has_sub else "h2"

    if style == "Heading 1":
        return "h1"
    if style == "Heading 2":
        return "h2"
    if style == "Heading 3":
        return "h3"

    return None


def _extract_structure(doc, state: dict, fig_captions: dict = None):
    """
    State-machine pass over body elements in document order (paragraphs and tables).
    Phases: pre_title → authors → abstract → body → refs

    Sections use a content array of blocks instead of a plain body string, so that
    tables can be inserted inline at their exact position in the flow.
    """
    if fig_captions is None:
        fig_captions = {}
    phase = "pre_title"
    current_section = None
    authors_raw_lines = []

    body_children = list(doc.element.body)
    body_len  = len(body_children)
    para_idx  = 0
    tbl_idx   = 0
    fig_counter = 0
    last_nonempty_text = ""
    idx = 0

    while idx < body_len:
        el = body_children[idx]
        idx += 1
        # ── Table element ─────────────────────────────────────────────────────
        if el.tag == _W_TBL:
            tbl = doc.tables[tbl_idx]
            tbl_idx += 1
            if phase == "body":
                tbl_block = _table_to_block(tbl, tbl_idx)
                if tbl_block:
                    if current_section is None:
                        current_section = _new_section("", "Other")
                    if current_section["subsections"]:
                        current_section["subsections"][-1]["content"].append(tbl_block)
                    else:
                        current_section["content"].append(tbl_block)
            continue

        # ── Paragraph element ─────────────────────────────────────────────────
        if el.tag != _W_P:
            continue

        p = doc.paragraphs[para_idx]
        para_idx += 1

        style_name = p.style.name if p.style else ""
        text = p.text.strip()
        if text:
            last_nonempty_text = text
        is_bold = all(run.bold for run in p.runs if run.text.strip()) and bool(p.runs)
        is_list = "list" in style_name.lower()
        font_size = None
        for run in p.runs:
            if run.font.size:
                font_size = run.font.size.pt
                break

        # ── OMML equation detection (before blank-text skip) ─────────────────
        if phase == "body" and _has_math(p._element):
            data_uri = _math_para_to_image(p)
            if current_section is None:
                current_section = _new_section("", "Other")
            target = (current_section["subsections"][-1]["content"]
                      if current_section["subsections"] else current_section["content"])
            if data_uri:
                target.append({"type": "equation", "data_uri": data_uri})
            else:
                # Fallback: plain text from math runs
                runs = p._element.findall(f".//{_MATH_NS}t")
                eq_text = " ".join(r.text for r in runs if r.text).strip()
                if eq_text:
                    target.append({"type": "paragraph", "text": eq_text})
            continue

        # ── Inline image detection (before blank-text skip) ──────────────────
        if phase == "body" and _has_image(p._element):
            caption = ""
            idx_delta = para_delta = 0
            # Look back: preceding non-empty paragraph was a skip label
            is_skip = bool(_SKIP_FIG_RE.match(last_nonempty_text)) if last_nonempty_text else False

            # Check if the image paragraph itself carries caption/skip text
            # (Word sometimes places the caption in the same <w:p> as the image)
            if text:
                if _SKIP_FIG_RE.match(text):
                    is_skip = True
                elif _FIG_CAPTION_RE.match(text):
                    caption = text

            if not caption and not is_skip:
                # Look ahead for a caption or skip label (skip up to 2 blanks)
                lookahead = 0
                for _la in range(3):
                    if idx + lookahead < body_len and body_children[idx + lookahead].tag == _W_P:
                        next_text = _para_el_text(body_children[idx + lookahead])
                        if next_text:
                            if _SKIP_FIG_RE.match(next_text):
                                is_skip = True
                                idx_delta = lookahead + 1
                                para_delta = lookahead + 1
                            elif _FIG_CAPTION_RE.match(next_text):
                                caption = next_text
                                idx_delta = lookahead + 1
                                para_delta = lookahead + 1
                            break
                        lookahead += 1

            idx      += idx_delta
            para_idx += para_delta

            if is_skip:
                continue  # Graphical Abstract / Schema — skip Fig-N numbering

            fig_counter += 1
            # Fall back to the pre-scanned caption map if still no caption found
            if not caption and fig_counter in fig_captions:
                caption = fig_captions[fig_counter]
            fig_block = _build_figure_block(p, doc, fig_counter, caption)
            state["figures"].append({k: fig_block[k] for k in ("id", "label", "caption", "href")})
            if current_section is None:
                current_section = _new_section("", "Other")
            target = (current_section["subsections"][-1]["content"]
                      if current_section["subsections"] else current_section["content"])
            target.append(fig_block)
            continue

        if not text:
            continue

        heading_level = _classify_heading(text, style_name, is_bold=is_bold)
        # Strict (no bold heuristic) — used for pre-body phase transitions so that
        # bold decorative lines like "Graphical Abstract" don't skip the real abstract.
        heading_explicit = _classify_heading(text, style_name)
        is_abstract  = bool(_ABSTRACT_RE.match(text))
        is_keywords  = bool(_KEYWORDS_RE.match(text))
        is_refs      = bool(_REFS_HEADING_RE.match(text)) and (heading_level is not None or is_bold)

        # ── pre_title ────────────────────────────────────────────────────────
        if phase == "pre_title":
            if heading_explicit == "h1" or (is_bold and font_size and font_size >= 14):
                state["title"] = text
                phase = "authors"
                continue
            if para_idx <= 5:
                state["title"] = text
                phase = "authors"
                continue

        # ── authors ──────────────────────────────────────────────────────────
        if phase == "authors":
            if is_abstract:
                state["authors_raw"] = "\n".join(authors_raw_lines)
                phase = "abstract"
                continue
            # Use strict detection only — bold decorative headings (e.g. "Graphical
            # Abstract") must not prematurely end author collection before the
            # real Abstract heading is encountered.
            if heading_explicit:
                state["authors_raw"] = "\n".join(authors_raw_lines)
                phase = "body"
                # intentional fall-through to body processing below
            else:
                authors_raw_lines.append(text)
                continue

        # ── abstract ─────────────────────────────────────────────────────────
        if phase == "abstract":
            if is_keywords:
                kw_part = re.split(r"[:\-]\s*", text, maxsplit=1)[-1]
                state["keywords"] = [k.strip() for k in re.split(r"[,;]", kw_part) if k.strip()]
                phase = "body"
                continue
            if heading_level and not is_abstract:
                phase = "body"
                # intentional fall-through — this heading starts the body
            else:
                state["abstract"] = (state["abstract"] + " " + text).strip()
                continue

        # ── body — keyword line after abstract ───────────────────────────────
        if phase == "body" and is_keywords and not state["keywords"]:
            kw_part = re.split(r"[:\-]\s*", text, maxsplit=1)[-1]
            state["keywords"] = [k.strip() for k in re.split(r"[,;]", kw_part) if k.strip()]
            continue

        # ── body → refs transition ───────────────────────────────────────────
        if phase == "body" and is_refs:
            if current_section:
                state["sections"].append(current_section)
                current_section = None
            phase = "refs"
            continue

        # ── refs ─────────────────────────────────────────────────────────────
        if phase == "refs":
            is_list_item = is_list
            is_bullet    = bool(_REF_BULLET_RE.match(text))
            is_numbered  = bool(_REF_ENTRY_RE.match(text))
            starts_lower = bool(text) and text[0].islower()

            if is_list_item or is_bullet or is_numbered or not state["references"]:
                state["references"].append(text)
            elif starts_lower and state["references"]:
                state["references"][-1] += " " + text
            else:
                state["references"].append(text)
            continue

        # ── body sections ────────────────────────────────────────────────────
        if phase == "body":
            if heading_level in ("h1", "h2"):
                if current_section:
                    state["sections"].append(current_section)
                current_section = _new_section(text, _guess_section_type(text))
            elif heading_level == "h3":
                if current_section is None:
                    current_section = _new_section("", "Other")
                current_section["subsections"].append({"heading": text, "content": []})
            else:
                if current_section is None:
                    current_section = _new_section("", "Other")
                block = {"type": "paragraph", "text": text}
                if current_section["subsections"]:
                    current_section["subsections"][-1]["content"].append(block)
                else:
                    current_section["content"].append(block)

    if current_section:
        state["sections"].append(current_section)


def _new_section(heading: str, sec_type: str) -> dict:
    return {"heading": heading, "type": sec_type, "content": [], "subsections": []}


def _table_to_block(tbl, tbl_number: int) -> dict | None:
    """Convert a python-docx Table object to a content block dict."""
    if not tbl.rows:
        return None
    headers = _row_cells(tbl.rows[0])
    data_rows = [
        _row_cells(r) for r in tbl.rows[1:]
        if any(c.strip() for c in _row_cells(r))
    ]
    label = f"Table {tbl_number}"
    return {
        "type": "table",
        "label": label,
        "caption": label,
        "headers": headers,
        "rows": data_rows,
    }


def _para_el_text(el) -> str:
    """Concatenate all w:t text nodes inside a raw paragraph XML element."""
    return "".join(t.text or "" for t in el.findall(".//" + _W_T)).strip()


def _has_image(p_element) -> bool:
    return bool(
        p_element.findall(f".//{_DRAWING_NS}inline") or
        p_element.findall(f".//{_DRAWING_NS}anchor") or
        p_element.findall(f".//{_VML_NS}imagedata")  # older VML-based images
    )


def _has_math(p_element) -> bool:
    return bool(p_element.findall(f".//{_MATH_NS}oMath"))


def _math_para_to_image(p) -> str:
    """Render an OMML equation paragraph to a base64 PNG via LibreOffice."""
    import subprocess, tempfile, os, glob, shutil, base64 as _b64, io
    from docx import Document as _Doc
    from copy import deepcopy
    from PIL import Image

    tmp_doc = _Doc()
    # Remove the default blank paragraph so only the equation appears
    for existing in tmp_doc.paragraphs:
        existing._element.getparent().remove(existing._element)
    tmp_doc.element.body.insert(0, deepcopy(p._element))

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        tmp_doc.save(f.name)
        src = f.name

    out_dir = tempfile.mkdtemp()
    try:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "png", src, "--outdir", out_dir],
            check=True, capture_output=True, timeout=30
        )
        pngs = glob.glob(os.path.join(out_dir, "*.png"))
        if pngs:
            img = Image.open(pngs[0]).convert("RGB")
            img = _smart_crop(img)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return f"data:image/png;base64,{_b64.b64encode(buf.getvalue()).decode()}"
    except Exception:
        pass
    finally:
        os.unlink(src)
        shutil.rmtree(out_dir, ignore_errors=True)
    return ""


def _smart_crop(img, pad: int = 8):
    """
    Crop to actual content area, skipping thin border-only rows/columns.

    Word EMF drawing canvases often have a 1–3 px border around a large blank
    area with the chart content in one corner.  A simple bounding-box crop
    keeps the border (and the blank interior it encloses) because the border
    pixels extend to all four edges of the canvas.

    This function finds rows/columns whose non-white pixel count exceeds a
    threshold sized relative to the image dimensions.  A 1–3 px border line
    contributes only 2–6 non-white pixels per row, well below the threshold,
    so it is excluded and only the chart-content rows/columns survive.
    """
    try:
        import numpy as np
        arr = np.array(img.convert("RGB"))
        h, w = arr.shape[:2]
        non_white = (arr < 250).any(axis=2)          # True where pixel ≠ white
        row_density = non_white.sum(axis=1).astype(int)
        col_density = non_white.sum(axis=0).astype(int)

        # Minimum pixels per row/col to be counted as real content.
        # A 1-3 px border contributes ≤ 6 px; chart content contributes much more.
        min_px = max(6, min(w, h) // 30)

        cr = np.where(row_density >= min_px)[0]
        cc = np.where(col_density >= min_px)[0]
        if not len(cr) or not len(cc):
            # Fallback: any non-white pixel
            cr = np.where(row_density > 0)[0]
            cc = np.where(col_density > 0)[0]
        if not len(cr) or not len(cc):
            return img

        return img.crop((
            max(0, int(cc[0])  - pad),
            max(0, int(cr[0])  - pad),
            min(w, int(cc[-1]) + pad + 1),
            min(h, int(cr[-1]) + pad + 1),
        ))
    except ImportError:
        # numpy unavailable — fall back to simple bounding-box crop
        from PIL import ImageChops
        bg = img._new(img.mode, img.size)
        bg.paste((255, 255, 255), (0, 0, img.width, img.height))
        bbox = ImageChops.difference(img.convert("RGB"),
                                     img.convert("RGB").point(lambda _: 255)).getbbox()
        if not bbox:
            return img
        l, t, r, b = bbox
        return img.crop((max(0, l - pad), max(0, t - pad),
                         min(img.width, r + pad), min(img.height, b + pad)))


_WEASYPRINT_OK_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/gif",
                        "image/svg+xml", "image/webp", "image/bmp"}


def _blob_to_data_uri(blob: bytes, content_type: str) -> str:
    """Return a base64 data URI, converting WMF/EMF to PNG via LibreOffice or Pillow."""
    import base64 as _b64
    ct = (content_type or "").lower()
    if ct in _WEASYPRINT_OK_TYPES:
        b64 = _b64.b64encode(blob).decode()
        return f"data:{content_type};base64,{b64}"
    # Use LibreOffice headless for EMF/WMF (most reliable cross-platform renderer)
    try:
        import subprocess, tempfile, os, glob, shutil
        from PIL import Image
        suffix = ".emf" if "emf" in ct else ".wmf"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as src:
            src.write(blob)
            src_path = src.name
        out_dir = tempfile.mkdtemp()
        try:
            subprocess.run(
                ["soffice", "--headless", "--convert-to", "png", src_path, "--outdir", out_dir],
                check=True, capture_output=True, timeout=30
            )
            pngs = glob.glob(os.path.join(out_dir, "*.png"))
            if pngs:
                img = Image.open(pngs[0]).convert("RGB")
                img = _smart_crop(img)
                import io
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                b64 = _b64.b64encode(buf.getvalue()).decode()
                return f"data:image/png;base64,{b64}"
        finally:
            os.unlink(src_path)
            shutil.rmtree(out_dir, ignore_errors=True)
    except Exception:
        pass
    # Pillow fallback (works for some formats on Windows)
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(blob))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = _b64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""


def _build_figure_block(p, doc, fig_number: int, caption: str) -> dict:
    """Extract image bytes (base64 data URI) and return a figure content block."""
    data_uri = ""

    # 1) DrawingML (modern DOCX: wp:inline / wp:anchor)
    for tag in (f"{_DRAWING_NS}inline", f"{_DRAWING_NS}anchor"):
        for drawing in p._element.findall(f".//{tag}"):
            blip = drawing.find(f".//{_DRAW_A_NS}blip")
            if blip is None:
                continue
            r_embed = blip.get(f"{_REL_NS}embed")
            if not r_embed:
                continue
            try:
                img_part = doc.part.related_parts[r_embed]
                data_uri = _blob_to_data_uri(img_part.blob, img_part.content_type)
            except Exception:
                pass
            if data_uri:
                break
        if data_uri:
            break

    # 2) VML fallback (older DOCX: v:imagedata r:id="rId...")
    if not data_uri:
        for imgdata in p._element.findall(f".//{_VML_NS}imagedata"):
            r_id = imgdata.get(f"{_REL_NS}id") or imgdata.get(f"{_O_NS}relid")
            if not r_id:
                continue
            try:
                img_part = doc.part.related_parts[r_id]
                data_uri = _blob_to_data_uri(img_part.blob, img_part.content_type)
            except Exception:
                pass
            if data_uri:
                break

    return {
        "type":     "figure",
        "id":       f"fig{fig_number}",
        "label":    f"Figure {fig_number}",
        "caption":  caption,
        "href":     f"figure{fig_number}.png",
        "data_uri": data_uri,
    }


def _guess_section_type(heading: str) -> str:
    """Map heading text to one of the JATS section type labels."""
    h = heading.lower()
    mapping = [
        ("introduction",   "Introduction"),
        ("background",     "Introduction"),
        ("literature",     "Introduction"),
        ("material",       "Methods"),
        ("method",         "Methods"),
        ("experiment",     "Methods"),
        ("result",         "Results"),
        ("finding",        "Results"),
        ("discussion",     "Discussion"),
        ("conclusion",     "Conclusion"),
        ("summary",        "Conclusion"),
        ("acknowledg",     "Acknowledgements"),
        ("funding",        "Acknowledgements"),
    ]
    for key, val in mapping:
        if key in h:
            return val
    return "Other"


def _parse_references(raw_refs: list) -> list:
    """
    Convert raw collected reference strings into structured dicts.

    Handles three input formats (stripped / cleaned here):
      • Bullet/dash list:  "- Ibrahim Khan, Khalid Saeed... doi: 10.1016/..."
      • Numbered [1]:      "[1] Smith J et al. J Chem. 2020..."
      • Plain paragraph:   "Patel R. Green chemistry. Org Lett. 2021..."

    Returns: [{number, raw_text, doi}]
    """
    result = []
    for i, raw in enumerate(raw_refs, 1):
        # Strip leading bullet character or number marker
        text = _REF_BULLET_RE.sub("", raw)
        text = re.sub(r"^\[?\d+[\]\.]\s+", "", text).strip()

        # Extract DOI
        doi = ""
        m = _DOI_RE.search(raw)
        if m:
            doi = m.group(1).rstrip(".,;)>").strip()

        if text:
            result.append({"number": i, "raw_text": text, "doi": doi})

    return result


def _parse_authors(raw: str) -> list:
    """
    Parse the author block captured between the title and abstract.

    Handles the NFP manuscript format:
      Line 0:  Mylarappa M¹*, N Raghavendra²*, Shravan Kumar K N³, Chandruavasan S⁴
      Line 1+: ¹Department of Studies in Chemistry, Bangalore University…
               ²Research Centre, Department of Chemistry…
               Corresponding authors: email1@x.com, email2@x.com
    """
    if not raw:
        return [_empty_author()]

    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    if not lines:
        return [_empty_author()]

    affil_map = _build_affil_map(lines[1:])
    corresp_emails = _find_corresp_emails(lines)

    authors = _split_author_line(lines[0])
    if not authors:
        return [_empty_author()]

    # Assign affiliations and emails
    email_idx = 0
    for author in authors:
        sup = author.pop("_sup", "")
        author["affiliation"] = affil_map.get(sup, "")
        if author["corresponding"]:
            author["email"] = corresp_emails[email_idx] if email_idx < len(corresp_emails) else ""
            email_idx += 1

    return authors


def _empty_author() -> dict:
    return {
        "first_name": "", "last_name": "", "affiliation": "",
        "email": "", "orcid": "", "corresponding": True,
    }


def _split_author_line(line: str) -> list:
    """
    Split an author name line on superscript markers (Unicode ¹²³⁴ or
    digits glued directly to a letter like M1*).

    Returns a list of author dicts with a temporary '_sup' key holding
    the normalised affiliation number string.
    """
    parts = _AUTHOR_MARKER_RE.split(line)

    # No markers found — fall back to simple comma split
    if len(parts) == 1:
        return _fallback_comma_split(line)

    authors = []
    for i in range(0, len(parts), 2):
        name_raw = parts[i].strip().lstrip(',').strip()
        marker = parts[i + 1] if i + 1 < len(parts) else ""

        if not name_raw:
            continue

        sup_num = marker.replace('*', '').replace(',', '').translate(_SUP_TO_NUM)
        is_corresp = '*' in marker

        first, last = _split_name(name_raw)
        authors.append({
            "first_name": first,
            "last_name": last,
            "affiliation": "",
            "email": "",
            "orcid": "",
            "corresponding": is_corresp,
            "_sup": sup_num,
        })

    return authors or _fallback_comma_split(line)


def _split_name(name: str) -> tuple:
    """
    Return (first_name, last_name).

    Trailing single-letter initials become the last name so that South-Indian /
    abbreviated suffix formats are handled correctly:
      'Shankar S'          → ('Shankar',       'S')
      'Ravi K N'           → ('Ravi',           'K N')
      'Manju Kumar S N'    → ('Manju Kumar',    'S N')
      'Mylarappa M'        → ('Mylarappa',      'M')
      'Shravan Kumar K N'  → ('Shravan Kumar',  'K N')

    If the final token is a full word it is the last name as normal:
      'S.K RaviKumar'      → ('S.K',            'RaviKumar')
      'John Smith'         → ('John',            'Smith')

    A single-word name has no last name:
      'Ravi'               → ('Ravi',            '')
    """
    parts = name.strip().split()
    if not parts:
        return ("", "")
    if len(parts) == 1:
        return (parts[0], "")

    def _is_initial(token: str) -> bool:
        """True for single-letter tokens like 'K', 'N', 'S', 'M.' (period optional)."""
        return len(token.rstrip(".")) == 1 and token.rstrip(".").isalpha()

    # Walk backwards collecting consecutive single-letter initials into last_name
    tail_start = len(parts)
    while tail_start > 0 and _is_initial(parts[tail_start - 1]):
        tail_start -= 1

    if 0 < tail_start < len(parts):
        # Non-initial first-name part(s) + trailing initials
        return (" ".join(parts[:tail_start]), " ".join(parts[tail_start:]))

    # No trailing initials (or every token is an initial) — last token is last name
    return (" ".join(parts[:-1]), parts[-1])


def _build_affil_map(lines: list) -> dict:
    """Build {number_str: affiliation_text} from lines like '¹Department of…'"""
    affil_map = {}
    for line in lines:
        m = re.match(r'^([¹²³⁴⁵⁶⁷⁸⁹⁰]+|\d+)\s*(.+)$', line)
        if m:
            num = m.group(1).translate(_SUP_TO_NUM)
            affil_map[num] = m.group(2).strip()
    return affil_map


def _find_corresp_emails(lines: list) -> list:
    """Extract emails from a 'Corresponding author(s): …' line if present,
    otherwise collect all emails in the block."""
    for line in lines:
        if _CORRESP_LINE_RE.search(line):
            return _EMAIL_RE.findall(line)
    # Fallback: any email anywhere in the author block
    emails = []
    for line in lines:
        emails.extend(_EMAIL_RE.findall(line))
    return emails


def _fallback_comma_split(line: str) -> list:
    """Simple comma split used when no superscript markers are detected."""
    names = [n.strip() for n in line.split(',') if n.strip()]
    result = []
    for i, name in enumerate(names):
        name_clean = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹⁰\d*]', '', name).strip()
        first, last = _split_name(name_clean)
        result.append({
            "first_name": first,
            "last_name": last,
            "affiliation": "",
            "email": "",
            "orcid": "",
            "corresponding": i == 0,
            "_sup": str(i + 1),
        })
    return result


def _row_cells(row) -> list:
    """Return cell texts for a table row, skipping duplicate merged-cell references."""
    seen  = set()
    cells = []
    for cell in row.cells:
        cid = id(cell._tc)
        if cid not in seen:
            seen.add(cid)
            cells.append(cell.text.strip())
    return cells


