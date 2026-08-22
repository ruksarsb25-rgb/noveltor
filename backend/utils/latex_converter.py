"""
Convert article content to LaTeX format for professional PDF generation.
Handles equations, sections, references, figures, and proper mathematical typesetting.
"""

import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Any

from utils.equations import _LATEX_SYMBOL_MAP, _normalize_math_alphanumerics

# Article-type badge labels — same mapping as the WeasyPrint template
# (_TYPE_LABELS in html_template.py) so both PDFs show the same text.
_TYPE_LABELS = {
    "Research Article":        "RESEARCH ARTICLE",
    "Review":                  "REVIEW ARTICLE",
    "Conference Proceeding":   "CONFERENCE PROCEEDING",
    "Enhanced Poster Abstract": "ENHANCED POSTER ABSTRACT",
    "Conference Report":       "CONFERENCE REPORT",
}

# HTML tags the rest of the app uses for inline formatting: <sub>/<sup> from
# the DOCX parser (chemical formulas, citation numbers), <strong>/<em> from
# the Sections screen's Bold/Italic toolbar. escape_latex() must convert
# these to real LaTeX before general escaping, or they show up as literal
# "<sub>2</sub>" text in the compiled PDF.
_SUB_TAG_RE = re.compile(r'<sub>(.*?)</sub>', re.IGNORECASE | re.DOTALL)
_SUP_TAG_RE = re.compile(r'<sup>(.*?)</sup>', re.IGNORECASE | re.DOTALL)
_STRONG_TAG_RE = re.compile(r'<strong>(.*?)</strong>', re.IGNORECASE | re.DOTALL)
_EM_TAG_RE = re.compile(r'<em>(.*?)</em>', re.IGNORECASE | re.DOTALL)

# Bare URLs (e.g. a DOI the parser appended as plain text after a hyperlink,
# or a URL an author pasted directly) — same pattern as the WeasyPrint
# template's _linkify(), so both PDFs turn the same text into clickable
# links. Split out and wrapped in \url{} *before* general character
# escaping since \url{} is verbatim and must receive the raw URL text.
_URL_RE = re.compile(r'(https?://[^\s<>"\')\]]+)', re.IGNORECASE)

# Bracket citations — "[1]", "[1, 2]", "[1-3]" — same pattern as the
# WeasyPrint template's _citify(). Matched on raw text (digits/commas/
# hyphens/brackets need no LaTeX escaping) and replaced with a <cite>
# marker that, like <sub>/<sup>, survives step-1 character escaping
# untouched and is expanded to real \hyperref links in step 2.
_CITE_RE = re.compile(r'\[([\d,\s–—-]+)\]')
_CITE_TAG_RE = re.compile(r'<cite>([\d,]+)</cite>')


def _citify_marker(text: str) -> str:
    """Replace bracket citations with a <cite> marker carrying the expanded
    (range-resolved) list of reference numbers, e.g. "[1-3]" -> "<cite>1,2,3</cite>"."""
    def replace_bracket(m):
        inner = m.group(1)
        nums = []
        for part in inner.split(','):
            part = part.strip()
            range_match = re.match(r'^(\d+)\s*[–—-]\s*(\d+)$', part)
            if range_match:
                nums.extend(range(int(range_match.group(1)), int(range_match.group(2)) + 1))
            elif re.match(r'^\d+$', part):
                nums.append(int(part))
        if not nums:
            return m.group(0)
        return '<cite>' + ','.join(str(n) for n in nums) + '</cite>'
    return _CITE_RE.sub(replace_bracket, text)

# inputenc's utf8 table reliably covers Latin-1 Supplement (À-ÿ) and, in
# modern TeX Live, Latin Extended-A (Ā-ſ, e.g. ă, ş, ț) too — confirmed
# empirically: a real reference list with ă/ş/ü/í/ó in author names compiled
# fine, only a much rarer Latin Extended-B letter (ƫ) failed. Anything
# outside this range is a compile-failure risk we have no specific mapping
# for and falls through to the transliteration safety net below.
_SAFE_UNICODE_RE = re.compile('[À-ſ]')

# Unicode subscript/superscript digits and letters → their plain ASCII form,
# used to rebuild real LaTeX subscript/superscript math (e.g. "BaAl₂O₄" →
# "BaAl$_{2}$O$_{4}$") for chemical formulas typed directly into prose text.
_SUB_MAP = {
    '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
    '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9',
    'ₐ': 'a', 'ₑ': 'e', 'ₕ': 'h', 'ᵢ': 'i', 'ⱼ': 'j',
    'ₖ': 'k', 'ₗ': 'l', 'ₘ': 'm', 'ₙ': 'n', 'ₒ': 'o',
    'ₚ': 'p', 'ᵣ': 'r', 'ₛ': 's', 'ₜ': 't', 'ᵤ': 'u',
    'ᵥ': 'v', 'ₓ': 'x', '₋': '-', '₊': '+', '₌': '=',
}
_SUP_MAP = {
    '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
    '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
    'ᵃ': 'a', 'ᵇ': 'b', 'ᶜ': 'c', 'ᵈ': 'd', 'ᵉ': 'e',
    'ᶠ': 'f', 'ᵍ': 'g', 'ʰ': 'h', 'ⁱ': 'i', 'ʲ': 'j',
    'ᵏ': 'k', 'ˡ': 'l', 'ᵐ': 'm', 'ⁿ': 'n', 'ᵒ': 'o',
    'ᵖ': 'p', 'ʳ': 'r', 'ˢ': 's', 'ᵗ': 't', 'ᵘ': 'u',
    'ᵛ': 'v', 'ʷ': 'w', 'ˣ': 'x', 'ʸ': 'y', 'ᶻ': 'z',
    '⁻': '-', '⁺': '+', '⁼': '=',
}
_SUB_RUN_RE = re.compile('[' + ''.join(_SUB_MAP) + ']+')
_SUP_RUN_RE = re.compile('[' + ''.join(_SUP_MAP) + ']+')

# Manuscript table/figure captions already carry the author's own number
# ("Table 2. Crystallite size..."), but LaTeX's \caption{} also
# auto-numbers — left alone, both fire and the number prints twice
# ("Table 2: Table 2"). Strip the author's leading number so only LaTeX's
# own numbering shows. (Section headings are handled differently — see
# format_section() — since \section{}'s own counter can't be taught every
# case where the manuscript's numbering doesn't start at 1 or skips
# unnumbered front-matter headings, so those are printed unnumbered with
# the manuscript's heading text, number included, kept verbatim instead.)
_LEADING_TABLE_LABEL_RE = re.compile(r'^table\s+\d+\s*[:.]?\s*', re.IGNORECASE)
_LEADING_FIG_LABEL_RE = re.compile(r'^fig(?:ure)?\.?\s*\d+\s*[:.]?\s*', re.IGNORECASE)

# Tags/marks that can differ cosmetically between the same caption text
# appearing twice (once as the figure/table block's own caption, once as a
# leftover manuscript paragraph right after the image/table) without it
# being a different caption — stripped out before the duplicate check below.
_CAPTION_NORM_TAG_RE = re.compile(r'</?(?:sub|sup|strong|em)>', re.IGNORECASE)
_CAPTION_NORM_NONALNUM_RE = re.compile(r'[^a-z0-9]+')


_LATIN_LETTER_NAME_RE = re.compile(r'LATIN (SMALL|CAPITAL) LETTER ([A-Z]+)')


def _ascii_fallback(ch: str) -> str:
    """Pass an ASCII or Latin-1/Extended-A character through unchanged
    (inputenc handles both); transliterate anything else to its closest
    plain-ASCII form. Most accented letters decompose via NFKD (stripping
    the combining mark leaves the base letter); some rare ones don't (e.g.
    "ƫ" LATIN SMALL LETTER T WITH PALATAL HOOK has no decomposition at all —
    Unicode never gave it one), so fall back to parsing "LATIN ... LETTER X"
    out of the character's own name. Truly unrecognisable characters (other
    scripts, symbols) are dropped rather than crashing the whole export."""
    if ord(ch) < 128 or _SAFE_UNICODE_RE.match(ch):
        return ch

    decomposed = unicodedata.normalize('NFKD', ch)
    base = ''.join(c for c in decomposed if not unicodedata.combining(c))
    if base and base != ch:
        return base

    try:
        name = unicodedata.name(ch)
    except ValueError:
        return ''
    m = _LATIN_LETTER_NAME_RE.match(name)
    if m:
        letter = m.group(2)
        return letter if m.group(1) == 'CAPITAL' else letter.lower()
    return ''


def _normalize_caption_for_match(text: str) -> str:
    """Collapse a caption down to just its lowercase alphanumerics, with
    <sub>/<sup>/<strong>/<em> tags stripped and Unicode sub/superscript
    digits folded to plain ASCII — so the same caption text written two
    slightly different ways (e.g. "SrO2" vs "SrO<sub>2</sub>" vs "SrO₂")
    still compares equal. Used only to detect a duplicate caption paragraph,
    never for anything that ends up in the actual LaTeX output."""
    s = _CAPTION_NORM_TAG_RE.sub('', text)
    for uni, ascii_ch in {**_SUB_MAP, **_SUP_MAP}.items():
        s = s.replace(uni, ascii_ch)
    return _CAPTION_NORM_NONALNUM_RE.sub('', s.lower())


def equation_to_latex(equation_text: str) -> str:
    """
    Convert extracted equation text to proper LaTeX format.
    Handles subscripts, superscripts, fractions, and mathematical symbols.
    """
    if not equation_text:
        return ""

    # Map Unicode subscripts/superscripts back to LaTeX
    unicode_to_latex = {
        '₀': '_0', '₁': '_1', '₂': '_2', '₃': '_3', '₄': '_4',
        '₅': '_5', '₆': '_6', '₇': '_7', '₈': '_8', '₉': '_9',
        'ₐ': '_a', 'ₑ': '_e', 'ₜ': '_t', 'ₓ': '_x', 'ₙ': '_n',
        '⁰': '^0', '¹': '^1', '²': '^2', '³': '^3', '⁴': '^4',
    }

    latex = equation_text
    for unicode_char, latex_char in unicode_to_latex.items():
        latex = latex.replace(unicode_char, latex_char)

    # Escape special LaTeX characters (do this before fraction conversion)
    latex = latex.replace('&', r'\&')
    latex = latex.replace('%', r'\%')
    latex = latex.replace('$', r'\$')
    latex = latex.replace('#', r'\#')

    # Replace × with proper LaTeX multiplication
    latex = latex.replace('×', r'\times')

    return latex


def _author_affs(a: Dict[str, Any]) -> List[str]:
    """An author's affiliations as a list — "affiliations" (an author can
    belong to more than one institution) if present, else the legacy
    single "affiliation" string wrapped in a list, for records from before
    the list field existed. Same helper as the WeasyPrint templates use,
    so every export agrees on affiliation numbering for the same article."""
    affs = a.get("affiliations")
    if affs:
        return [s.strip() for s in affs if (s or "").strip()]
    single = (a.get("affiliation") or "").strip()
    return [single] if single else []


class LaTeXGenerator:
    """Generate complete LaTeX documents from article data."""

    def __init__(self, article: Dict[str, Any], images_dir=None):
        """
        images_dir: directory to write decoded figure/logo images into, so
        \\includegraphics can reference them by absolute path. Pass the same
        directory pdflatex will compile in (pdf_latex.py creates it before
        constructing this generator). None disables image embedding — the
        .tex source is still valid, just without figures.
        """
        self.article = article
        self.journal_name = article.get("journal_name", "Novel Future Publishing")
        self.title = article.get("title", "Untitled")
        self.authors = article.get("authors", [])
        self.abstract = article.get("abstract", "")
        self.keywords = article.get("keywords", [])
        self.sections = article.get("sections", [])
        self.references = article.get("references", [])
        self.images_dir = images_dir
        self._img_counter = 0

    def _write_image(self, data_uri: str, prefix: str):
        """Decode a data: URI image and write it to self.images_dir,
        returning an absolute path for \\includegraphics. Returns None if
        there's no images_dir, no data, or it fails to decode — callers
        must handle that (e.g. fall back to a placeholder comment)."""
        if not self.images_dir or not data_uri or "," not in data_uri:
            return None
        import base64
        header, b64_data = data_uri.split(",", 1)
        ext = "png"
        if "jpeg" in header or "jpg" in header:
            ext = "jpg"
        elif "gif" in header:
            ext = "gif"
        try:
            img_bytes = base64.b64decode(b64_data)
        except Exception:
            return None
        self._img_counter += 1
        path = Path(self.images_dir) / f"{prefix}{self._img_counter}.{ext}"
        try:
            path.write_bytes(img_bytes)
        except Exception:
            return None
        return str(path)

    def escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters and make plain-text Unicode
        (chemical-formula subscripts, Greek letters, dashes, …) safe for
        pdflatex, which has no inputenc table for most of these — a raw
        "₂" or "λ" byte sequence in the .tex source fails to compile.
        """
        if not text:
            return ""
        text = str(text)

        # Undo the docx parser's own HTML-escaping (_run_text_with_fmt
        # escapes every run's text so it's safe to wrap in <sub>/<sup>
        # HTML tags — correct for the WeasyPrint/web HTML path, which
        # un-escapes it again when the browser parses the markup, but
        # this LaTeX path never does, so a plain "&" in the manuscript
        # arrives here as the literal 5-character string "&amp;" and gets
        # printed as exactly that in the compiled PDF instead of "&").
        # Must run before anything else — the sub/sup tags themselves are
        # real, un-escaped "<"/">" characters (added after escaping the
        # run's own text, not html.escape()'d themselves), so this can't
        # collide with them.
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

        # 0. Bare URLs must be pulled out and wrapped in \url{} (verbatim)
        #    *before* anything below touches them — general escaping would
        #    both mangle the URL and make it unclickable. Non-URL segments
        #    recurse back through this same method for normal processing;
        #    recursion terminates because split-off segments never contain
        #    another URL match.
        url_parts = _URL_RE.split(text)
        if len(url_parts) > 1:
            out = []
            for i, part in enumerate(url_parts):
                if i % 2 == 1:  # captured URL group
                    clean = part.rstrip('.,;)')
                    tail = part[len(clean):]
                    out.append(f'\\url{{{clean}}}')
                    if tail:
                        out.append(self.escape_latex(tail))
                else:
                    out.append(self.escape_latex(part))
            return ''.join(out)

        text = text.replace('\xa0', ' ')  # non-breaking space
        # Some authors paste/type styled Unicode math letters (e.g. "𝑘𝑡")
        # directly into prose instead of using Word's Equation Editor —
        # normalize to plain ASCII before anything else touches it.
        text = _normalize_math_alphanumerics(text)
        # Bracket citations ("[1]", "[1-3]") -> <cite> markers, expanded to
        # \hyperref links in step 2 below, linking to \label{cite:N} anchors
        # placed on each \bibitem by format_references().
        text = _citify_marker(text)

        # 1. Escape LaTeX-reserved characters first, on the raw text. This
        #    never touches < or >, so the HTML tags step 2 looks for survive
        #    intact — and the LaTeX commands inserted from here on must not
        #    be re-escaped, which is why this step runs before all of them.
        text = text.replace('\\', r'\textbackslash{}')
        text = text.replace('&', r'\&')
        text = text.replace('%', r'\%')
        text = text.replace('$', r'\$')
        text = text.replace('#', r'\#')
        text = text.replace('_', r'\_')
        text = text.replace('{', r'\{')
        text = text.replace('}', r'\}')
        text = text.replace('~', r'\textasciitilde{}')
        text = text.replace('^', r'\textasciicircum{}')

        # 2. The app's own inline-formatting convention — <sub>/<sup> from
        #    the DOCX parser, <strong>/<em> from the Bold/Italic toolbar —
        #    to real LaTeX. Content is already escaped from step 1, so this
        #    is just wrapping, not touching characters that need escaping.
        text = _SUB_TAG_RE.sub(lambda m: '$_{' + m.group(1) + '}$', text)
        text = _SUP_TAG_RE.sub(lambda m: '$^{' + m.group(1) + '}$', text)
        text = _STRONG_TAG_RE.sub(lambda m: r'\textbf{' + m.group(1) + '}', text)
        text = _EM_TAG_RE.sub(lambda m: r'\textit{' + m.group(1) + '}', text)
        text = _CITE_TAG_RE.sub(
            lambda m: '[' + ','.join(f'\\hyperref[cite:{n}]{{{n}}}' for n in m.group(1).split(',')) + ']',
            text,
        )

        # 3. Unicode subscript/superscript digits (e.g. "BaAl₂O₄") → real
        #    LaTeX subscript/superscript math, the standard way chemical
        #    formulas are written in LaTeX.
        text = _SUB_RUN_RE.sub(lambda m: '$_{' + ''.join(_SUB_MAP[c] for c in m.group()) + '}$', text)
        text = _SUP_RUN_RE.sub(lambda m: '$^{' + ''.join(_SUP_MAP[c] for c in m.group()) + '}$', text)

        # 4. Dashes — LaTeX's own text-mode ligatures
        text = text.replace('—', '---').replace('–', '--')

        # 5. Greek letters / math operators appearing in plain prose (e.g.
        #    "λ - wavelength of Cu Kα radiation") — wrap each individually
        #    in inline math since they're not valid outside math mode.
        text = ''.join(f'${_LATEX_SYMBOL_MAP[c]}$' if c in _LATEX_SYMBOL_MAP else c for c in text)

        # 6. Safety net: any character still non-ASCII and outside the
        #    Latin-1 Supplement range (which inputenc reliably covers) is a
        #    compile-failure risk we have no specific mapping for (e.g. "ƫ"
        #    U+01AB, an obscure Romanian letter that showed up in a
        #    reference's author name and isn't in inputenc's table).
        #    Transliterate to its closest plain-ASCII form via NFKD rather
        #    than crash the whole export over one rare diacritic.
        text = ''.join(_ascii_fallback(c) for c in text)

        return text

    def _build_affils(self) -> List[str]:
        """Unique affiliations across ALL authors' affiliation lists, in
        first-seen order — same dedup logic as the WeasyPrint template's
        _build_affils(), so both outputs agree on affiliation numbering
        for the same article. An author can belong to more than one
        institution, so this flattens every author's list rather than
        assuming one affiliation each."""
        seen: List[str] = []
        for a in self.authors:
            for aff in _author_affs(a):
                if aff not in seen:
                    seen.append(aff)
        return seen

    def format_title_block(self) -> str:
        """
        The full masthead: badges, title, authors-with-superscripts on one
        line, numbered affiliations, corresponding-author email, dates, and
        DOI — replacing \\maketitle entirely so we control layout precisely
        (a plain \\maketitle+authblk block can grow taller than one page
        for many authors and get pushed to page 2 by itself, leaving page 1
        blank under the journal header). Mirrors the same field names and
        author/affiliation logic as the WeasyPrint template (build_html in
        html_template.py) so both PDFs show the same information.
        """
        article_type = self.article.get("article_type") or "Research Article"
        type_label = _TYPE_LABELS.get(article_type, article_type.upper())

        parts = []

        # Badges — left, above the centered title block below
        parts.append(
            "\\noindent"
            f"\\colorbox{{nfpbadgeblue}}{{\\textcolor{{white}}{{\\small\\textbf{{ {self.escape_latex(type_label)} }}}}}}"
            "\\hspace{4pt}"
            "\\colorbox{nfpbadgegreen}{\\textcolor{white}{\\small\\textbf{ OPEN ACCESS }}}"
            "\n\n"
        )

        # Title through DOI are centered as one block, matching standard
        # academic-paper PDF convention (title/authors/affiliations centered
        # on the page, unlike the left-aligned web-article layout).
        parts.append("\\begin{center}\n")

        # Title
        parts.append(f"{{\\LARGE\\bfseries\\color{{nfpnavy}} {self.escape_latex(self.title)}\\par}}\n\n")

        # Authors — one comma-joined line with superscript affiliation
        # numbers and "*" for corresponding authors (matches build_html's
        # authors_html construction exactly).
        affils = self._build_affils()
        multi_affil = len(affils) > 1
        author_chunks = []
        for a in self.authors:
            name = f"{(a.get('first_name') or '').strip()} {(a.get('last_name') or '').strip()}".strip()
            if not name:
                continue
            sups = []
            if multi_affil:
                for aff in _author_affs(a):
                    if aff in affils:
                        sups.append(str(affils.index(aff) + 1))
            if a.get("corresponding"):
                sups.append("*")
            chunk = self.escape_latex(name)
            if sups:
                chunk += f"\\textsuperscript{{{','.join(sups)}}}"
            author_chunks.append(chunk)
        if author_chunks:
            parts.append(", ".join(author_chunks) + "\\par\\smallskip\n\n")

        # Affiliations — numbered only when there's more than one. Joined
        # with \\ (a line break) inside ONE {\footnotesize ...} group
        # instead of \par-separating each entry: \par starts a new
        # paragraph, which picks up the full \parskip (set globally in the
        # preamble) between every single affiliation — for six-plus
        # affiliations, several wrapping to two lines, that reads as a lot
        # of dead vertical space. \footnotesize (down from \small) also
        # shrinks how often a long institutional address wraps at all.
        if affils:
            aff_lines = []
            for i, aff in enumerate(affils, 1):
                prefix = f"\\textsuperscript{{{i}}}\\," if multi_affil else ""
                aff_lines.append(f"{prefix}{self.escape_latex(aff)}")
            parts.append(
                "{\\footnotesize " + "\\\\[1pt]\n".join(aff_lines) + "}\\par\\smallskip\n\n"
            )

        # Corresponding author email(s)
        corresp_emails = [a.get("email") for a in self.authors if a.get("corresponding") and a.get("email")]
        if corresp_emails:
            label = "Corresponding authors" if len(corresp_emails) > 1 else "Corresponding author"
            emails = ", ".join(self.escape_latex(e) for e in corresp_emails)
            parts.append(f"{{\\small *{label}: {emails}}}\\par\\smallskip\n\n")

        # Dates
        date_parts = []
        if self.article.get("received_date"):
            date_parts.append(f"\\textbf{{Received:}} {self.escape_latex(self.article['received_date'])}")
        if self.article.get("accepted_date"):
            date_parts.append(f"\\textbf{{Accepted:}} {self.escape_latex(self.article['accepted_date'])}")
        if self.article.get("published_date"):
            date_parts.append(f"\\textbf{{Published:}} {self.escape_latex(self.article['published_date'])}")
        if date_parts:
            parts.append("{\\small " + "\\quad ".join(date_parts) + "}\\par\\smallskip\n\n")

        # DOI — \url{} does its own verbatim-style character handling, so
        # the raw value goes in directly rather than through escape_latex()
        # (which would double-escape any backslashes \url{} itself inserts
        # no special chars for, and DOIs don't need LaTeX escaping anyway).
        doi_val = (self.article.get("doi") or "").strip()
        if doi_val:
            parts.append(f"{{\\small \\textbf{{DOI:}} \\url{{https://doi.org/{doi_val}}}}}\\par\n\n")

        parts.append("\\end{center}\n\n")
        parts.append("\\vspace{4pt}\\noindent{\\color{nfpnavy}\\rule{\\linewidth}{1.2pt}}\\vspace{8pt}\n\n")

        return "".join(parts)

    def format_section(self, section: Dict[str, Any], depth: int = 1) -> str:
        """Format a section with content and subsections."""
        latex = ""

        heading = section.get("heading", "").strip()
        if heading:
            # Starred (unnumbered) commands with the manuscript's own
            # heading text kept verbatim, numbering and all — LaTeX's own
            # \section/\subsection counters don't know the manuscript
            # skips numbers for some headings (e.g. "Highlights",
            # "Graphical Abstract" before "1. Introduction") or restarts
            # per-subsection, so auto-numbering silently drifts away from
            # what the author actually wrote (observed: "1. Introduction"
            # rendering as "3 Introduction"). Printing exactly what's
            # there sidesteps that entirely instead of trying to teach the
            # counter every exception.
            if depth == 1:
                latex += f"\\section*{{{self.escape_latex(heading)}}}\n\n"
            elif depth == 2:
                latex += f"\\subsection*{{{self.escape_latex(heading)}}}\n\n"
            else:
                latex += f"\\subsubsection*{{{self.escape_latex(heading)}}}\n\n"

        # Process content blocks
        content = section.get("content", [])
        # Tracks the normalized caption of the most recently emitted
        # figure/table, so a manuscript paragraph that just restates that
        # same caption ("Fig. 2. SEM micrographs..." right after a figure
        # whose own caption is "SEM micrographs...") can be skipped instead
        # of printed a second time — \caption{} already showed it once,
        # auto-numbered.
        prev_caption_norm = None
        for block in content:
            block_type = block.get("type")

            if block_type == "paragraph":
                text = block.get("text", "").strip()
                if text:
                    delabeled = _LEADING_FIG_LABEL_RE.sub(
                        '', _LEADING_TABLE_LABEL_RE.sub('', text)
                    ).strip()
                    norm = _normalize_caption_for_match(delabeled)
                    if prev_caption_norm and len(norm) > 8 and norm == prev_caption_norm:
                        prev_caption_norm = None
                        continue
                    latex += f"{self.escape_latex(text)}\n\n"
                prev_caption_norm = None

            elif block_type == "equation":
                # Prefer real LaTeX math: either typed directly by the author
                # ($...$ in the manuscript) or converted from the OMML tree
                # (omml_to_latex, in equations.py) — both are valid LaTeX
                # already. Only fall back to the lossy flattened-text
                # reconstruction for older saved articles that predate the
                # "latex" field (e.g. a draft resumed from localStorage).
                block_latex = block.get("latex", "")
                if block_latex:
                    latex += f"\\[\n{block_latex}\n\\]\n\n"
                else:
                    eq_text = block.get("text", "")
                    if eq_text:
                        latex_eq = equation_to_latex(eq_text)
                        latex += f"\\[\n{latex_eq}\n\\]\n\n"
                prev_caption_norm = None

            elif block_type == "table":
                caption = block.get("caption", "")
                latex += self.format_table(block, caption)
                stripped_caption = _LEADING_TABLE_LABEL_RE.sub('', caption).strip() if caption else ""
                prev_caption_norm = _normalize_caption_for_match(stripped_caption) or None

            elif block_type == "figure":
                caption = block.get("caption", "")
                label = block.get("label", "Figure")
                data_uri = block.get("data_uri", "")
                img_path = self._write_image(data_uri, "fig")
                if img_path or caption:
                    # [H]: same reasoning as format_table()'s [H] — pin the
                    # figure exactly where declared instead of it floating
                    # and leaving a gap on the page it "should" be on.
                    latex += "\\begin{figure}[H]\n\\centering\n"
                    if img_path:
                        latex += f"\\includegraphics[width=0.85\\textwidth]{{{img_path}}}\n"
                    else:
                        # No image data available — keep the caption/label
                        # visible instead of silently dropping the figure.
                        latex += f"\\fbox{{\\parbox{{0.6\\textwidth}}{{\\centering {self.escape_latex(label)}}}}}\n"
                    if caption:
                        latex += f"\\caption{{{self.escape_latex(caption)}}}\n"
                    latex += "\\end{figure}\n\n"
                prev_caption_norm = _normalize_caption_for_match(caption) if caption else None

        # Process subsections
        subsections = section.get("subsections", [])
        for subsection in subsections:
            latex += self.format_section(subsection, depth + 1)

        return latex

    def format_table(self, table: Dict[str, Any], caption: str = "") -> str:
        """
        Format a table in LaTeX using xltabular (longtable's page-splitting
        + tabularx's auto-width X columns).

        A plain tabularx/tabular table — floated with [H] or not — is an
        unbreakable block: if it doesn't fit in the space left on the page,
        LaTeX moves the *whole thing* to the next page, leaving a gap where
        it "should" have been. [H] alone can't fix that; only letting the
        table itself split across the page break (what longtable/xltabular
        are for) actually does.
        """
        rows = table.get("rows", [])
        headers = table.get("headers", [])

        if not rows:
            return ""

        # Estimate columns
        num_cols = len(headers) if headers else (len(rows[0]) if rows else 1)
        col_spec = f"|*{{{num_cols}}}{{X|}}"  # centering/vertical-centering
        # comes from the global \tabularxcolumn redefinition in generate()

        # \caption{} already prints its own "Table N:" prefix, so strip the
        # manuscript's own "Table N" label from a real description to avoid
        # doubling it. If there's no better text beyond the bare label,
        # caption with empty braces — LaTeX's auto-numbering alone still
        # gives a visible "Table N:" line (every table gets *some* caption),
        # without the double-labelling a fallback of the raw "Table N" text
        # would cause once \caption{} prefixes it again.
        caption_text = _LEADING_TABLE_LABEL_RE.sub('', caption).strip() if caption else ""
        caption_cmd = f"\\caption{{{self.escape_latex(caption_text)}}}" if caption_text else "\\caption{}"

        header_row = ""
        if headers:
            header_row = (
                "\\rowcolor{nfpnavy}\n"
                + " & ".join(f"\\textcolor{{white}}{{\\textbf{{{self.escape_latex(str(h))}}}}}" for h in headers)
                + " \\\\\n\\hline\n"
            )

        latex = f"\\begin{{xltabular}}{{\\textwidth}}{{{col_spec}}}\n"
        latex += f"{caption_cmd} \\\\\n\\hline\n{header_row}\\endfirsthead\n\n"
        # Repeated on every page the table continues onto
        latex += (
            f"\\multicolumn{{{num_cols}}}{{l}}{{\\small\\itshape (Table continued)}} \\\\\n"
            f"\\hline\n{header_row}\\endhead\n\n"
        )
        latex += (
            f"\\hline \\multicolumn{{{num_cols}}}{{r}}{{\\small\\itshape (continued on next page)}} \\\\\n"
            "\\endfoot\n\n"
        )
        latex += "\\hline\n\\endlastfoot\n\n"

        # Rows
        for row in rows:
            latex += " & ".join(self.escape_latex(str(cell)) for cell in row)
            latex += " \\\\\n"

        latex += "\\end{xltabular}\n\n"
        return latex

    def format_references(self) -> str:
        """Format references section."""
        if not self.references:
            return ""

        latex = "\\begin{thebibliography}{99}\n\n"

        for i, ref in enumerate(self.references, 1):
            if isinstance(ref, dict):
                text = ref.get("raw_text") or ref.get("text", "")
                doi = (ref.get("doi") or "").strip()
            else:
                text = str(ref)
                doi = ""

            if not text:
                continue

            # A DOI already visible as literal text in the reference
            # doesn't need a second, separate link — escape_latex's own
            # bare-URL handling already turns that into a clickable
            # \url{} on its own. Otherwise, append a link using whatever
            # is known: the DOI (from the source manuscript, or from the
            # "Enrich DOIs" Crossref lookup) if there is one, else a
            # Google Scholar search built from the citation text itself.
            # Mirrors the WeasyPrint template's CrossRef/Google Scholar
            # badges — without this, a reference enriched with a DOI only
            # ever showed it in the WeasyPrint PDF and JATS XML, never
            # here, which is what "enrichment isn't working" actually was.
            link = ""
            if doi and doi not in text:
                link = f" [\\href{{https://doi.org/{doi}}}{{CrossRef}}]"
            elif not doi:
                from urllib.parse import quote as _quote
                gs_url = f"https://scholar.google.com/scholar?q={_quote(text[:300])}"
                link = f" [\\href{{{gs_url}}}{{Google Scholar}}]"

            # \label{cite:N} gives in-text "[N]" citations (turned into
            # \hyperref[cite:N]{...} links by escape_latex's citation
            # handling) something to jump to.
            latex += f"\\bibitem{{{i}}}\\label{{cite:{i}}} {self.escape_latex(text)}{link}\n\n"

        latex += "\\end{thebibliography}\n"
        return latex

    def format_journal_header(self) -> str:
        """
        Journal branding row: cover thumbnail (left), "From the journal: /
        Name" (center), publisher logo (right) — mirrors the same three
        pieces of information as the WeasyPrint template's page-header, in
        a plain LaTeX tabular instead of CSS flexbox.
        """
        journal_logo = self.article.get("journal_logo", "")
        brand_logo = self.article.get("brand_logo", "")
        logo_path = self._write_image(journal_logo, "journal_logo")
        brand_path = self._write_image(brand_logo, "brand_logo")

        if not (logo_path or self.journal_name or brand_path):
            return ""

        # Both logos constrained to the same height (with a width cap and
        # keepaspectratio so neither can blow out the header) so they read
        # as a matched pair regardless of their original image proportions —
        # a journal cover thumbnail (portrait) and a wordmark logo
        # (landscape) previously ended up at very different visual sizes
        # when each was constrained by a different fixed width instead.
        logo_opts = "height=1.4cm,width=2.4cm,keepaspectratio"
        left = f"\\includegraphics[{logo_opts}]{{{logo_path}}}" if logo_path else ""
        center = ""
        if self.journal_name:
            center = (
                "{\\small\\color{gray!70!black} From the journal:}\\\\[2pt]"
                f"{{\\bfseries\\large\\color{{nfpnavy}} {self.escape_latex(self.journal_name)}}}"
            )
        right = f"\\includegraphics[{logo_opts}]{{{brand_path}}}" if brand_path else ""

        # \centering/\raggedleft are paragraph-mode declarations: left
        # dangling with no content after them (e.g. when a logo is missing
        # and its cell would otherwise be empty), the row-ending \\ has no
        # line to close and pdflatex aborts with "There's no line here to
        # end." Only emit the declaration together with actual content —
        # an empty cell with no declaration at all is harmless.
        center_cell = f"\\centering {center}" if center else ""
        right_cell = f"\\raggedleft {right}" if right else ""

        return (
            "\\noindent\n"
            "\\begin{tabular}{@{}m{0.18\\textwidth}m{0.54\\textwidth}m{0.24\\textwidth}@{}}\n"
            f"{left} & {center_cell} & {right_cell} \\\\\n"
            "\\end{tabular}\\par\n"
            "\\vspace{4pt}\n\n"
        )

    def generate(self) -> str:
        """Generate complete LaTeX document."""
        latex = r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{booktabs}
% [table] pulls in colortbl for \rowcolor{} — loaded before array/tabularx,
% the recommended order to avoid the two patching tabular internals in
% conflicting ways.
\usepackage[table]{xcolor}
\usepackage{tabularx}
\usepackage{array}
% xltabular = longtable's page-splitting + tabularx's auto-width X columns,
% so a data table too tall for the remaining page space flows onto the next
% page instead of jumping there as one unbreakable block and leaving a gap.
\usepackage{xltabular}
% Redefine X columns to use array's "m" (vertically centered) instead of
% tabularx's default "p" (top-aligned), on top of horizontal centering —
% fixes multi-line wrapped header/cell text sitting at the top of a taller
% row instead of centered in it. Documented technique from the tabularx
% package itself for exactly this case.
\renewcommand{\tabularxcolumn}[1]{>{\centering\arraybackslash}m{#1}}
% Float package's [H] placement pins a figure exactly where declared
% instead of LaTeX's normal float algorithm deferring it to fit (tables no
% longer use this — xltabular above is a better fix for them specifically).
\usepackage{float}

% Brand colors, matching the WeasyPrint template's palette
\definecolor{nfpnavy}{HTML}{0F3557}
\definecolor{nfpbadgeblue}{HTML}{2C6FBB}
\definecolor{nfpbadgegreen}{HTML}{2E9E5B}

% Colored text instead of hyperref's default boxed-border links, navy to
% match the WeasyPrint template's link color; no boxes in the printed/PDF
% output either way (pdfborder=0), just the color as the visual cue.
\hypersetup{colorlinks=true, linkcolor=nfpnavy, citecolor=nfpnavy, urlcolor=nfpnavy, pdfborder={0 0 0}}

\raggedbottom
% A little breathing room between paragraphs — spacing only, the default
% \parindent (and everything else about the existing text style) is untouched.
\setlength{\parskip}{6pt plus 2pt minus 1pt}

"""

        latex += "\\begin{document}\n\n"

        # Journal header, then the full masthead (badges, title, authors,
        # affiliations, dates, DOI) built manually instead of \maketitle —
        # a plain \maketitle+authblk block can grow taller than one page for
        # many authors and gets pushed to page 2 entirely, leaving page 1
        # with just the journal header and nothing else on it.
        latex += self.format_journal_header()
        latex += self.format_title_block()

        # Abstract — plain bold heading (not the indented "Abstract"
        # environment) to match the journal's house style.
        if self.abstract:
            latex += "{\\bfseries\\large ABSTRACT}\\par\\smallskip\n"
            latex += f"{self.escape_latex(self.abstract)}\\par\n\n"

        # Keywords
        if self.keywords:
            keywords_str = ", ".join(self.keywords)
            latex += f"\\textbf{{Keywords:}} {self.escape_latex(keywords_str)}\n\n"

        # Sections
        for section in self.sections:
            latex += self.format_section(section)

        # References
        latex += self.format_references()

        latex += "\\end{document}\n"

        return latex
