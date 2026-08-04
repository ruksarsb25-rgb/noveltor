"""
Convert article content to LaTeX format for professional PDF generation.
Handles equations, sections, references, figures, and proper mathematical typesetting.
"""

import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Any

from utils.equations import _LATEX_SYMBOL_MAP, _normalize_math_alphanumerics

# HTML tags the rest of the app uses for inline formatting: <sub>/<sup> from
# the DOCX parser (chemical formulas, citation numbers), <strong>/<em> from
# the Sections screen's Bold/Italic toolbar. escape_latex() must convert
# these to real LaTeX before general escaping, or they show up as literal
# "<sub>2</sub>" text in the compiled PDF.
_SUB_TAG_RE = re.compile(r'<sub>(.*?)</sub>', re.IGNORECASE | re.DOTALL)
_SUP_TAG_RE = re.compile(r'<sup>(.*?)</sup>', re.IGNORECASE | re.DOTALL)
_STRONG_TAG_RE = re.compile(r'<strong>(.*?)</strong>', re.IGNORECASE | re.DOTALL)
_EM_TAG_RE = re.compile(r'<em>(.*?)</em>', re.IGNORECASE | re.DOTALL)

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

# Manuscript headings/table captions already carry the author's own number
# (e.g. "3.2 SEM analysis", "Table 2. Crystallite size..."), but LaTeX's
# \section{}/\subsection{}/\caption{} also auto-number — left alone, both
# fire and the number prints twice ("3.2 3.2 SEM analysis", "Table 2: Table
# 2"). Strip the author's leading number so only LaTeX's own numbering shows.
_LEADING_HEADING_NUM_RE = re.compile(r'^\d+(?:\.\d+)*\.?\s+')
_LEADING_TABLE_LABEL_RE = re.compile(r'^table\s+\d+\s*[:.]?\s*', re.IGNORECASE)


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
        text = text.replace('\xa0', ' ')  # non-breaking space
        # Some authors paste/type styled Unicode math letters (e.g. "𝑘𝑡")
        # directly into prose instead of using Word's Equation Editor —
        # normalize to plain ASCII before anything else touches it.
        text = _normalize_math_alphanumerics(text)

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

    def format_authors(self) -> str:
        """
        Build \\author[]{}/\\affil[]{} commands (the authblk package) —
        each author gets a numbered superscript marker linking to their
        affiliation, and the corresponding author's email is attached as a
        \\thanks{} footnote. Returns the complete set of commands, not
        wrapped in an outer \\author{} — generate() inserts this as-is.
        """
        if not self.authors:
            return ""

        # Number each unique affiliation in first-seen order
        affil_numbers: Dict[str, int] = {}
        affil_order: List[str] = []
        for author in self.authors:
            aff = (author.get('affiliation') or '').strip()
            if aff and aff not in affil_numbers:
                affil_numbers[aff] = len(affil_order) + 1
                affil_order.append(aff)

        lines = []
        for author in self.authors:
            first_name = (author.get('first_name') or '').strip()
            last_name = (author.get('last_name') or '').strip()
            name = f"{first_name} {last_name}".strip()
            if not name:
                continue

            aff = (author.get('affiliation') or '').strip()
            marker = f"[{affil_numbers[aff]}]" if aff in affil_numbers else ""

            thanks = ""
            if author.get('corresponding') and author.get('email'):
                email = self.escape_latex(author['email'])
                thanks = f"\\thanks{{Corresponding author: {email}}}"

            lines.append(f"\\author{marker}{{{self.escape_latex(name)}{thanks}}}")

        for aff in affil_order:
            lines.append(f"\\affil[{affil_numbers[aff]}]{{{self.escape_latex(aff)}}}")

        return "\n".join(lines)

    def format_section(self, section: Dict[str, Any], depth: int = 1) -> str:
        """Format a section with content and subsections."""
        latex = ""

        heading = section.get("heading", "").strip()
        if heading:
            # Strip the manuscript's own leading number ("3.2 SEM analysis"
            # -> "SEM analysis") — \section/\subsection add their own.
            heading = _LEADING_HEADING_NUM_RE.sub('', heading)
            if depth == 1:
                latex += f"\\section{{{self.escape_latex(heading)}}}\n\n"
            elif depth == 2:
                latex += f"\\subsection{{{self.escape_latex(heading)}}}\n\n"
            else:
                latex += f"\\subsubsection{{{self.escape_latex(heading)}}}\n\n"

        # Process content blocks
        content = section.get("content", [])
        for block in content:
            block_type = block.get("type")

            if block_type == "paragraph":
                text = block.get("text", "").strip()
                if text:
                    latex += f"{self.escape_latex(text)}\n\n"

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

            elif block_type == "table":
                caption = block.get("caption", "")
                latex += self.format_table(block, caption)

            elif block_type == "figure":
                caption = block.get("caption", "")
                label = block.get("label", "Figure")
                data_uri = block.get("data_uri", "")
                img_path = self._write_image(data_uri, "fig")
                if img_path or caption:
                    latex += "\\begin{figure}[!htbp]\n\\centering\n"
                    if img_path:
                        latex += f"\\includegraphics[width=0.85\\textwidth]{{{img_path}}}\n"
                    else:
                        # No image data available — keep the caption/label
                        # visible instead of silently dropping the figure.
                        latex += f"\\fbox{{\\parbox{{0.6\\textwidth}}{{\\centering {self.escape_latex(label)}}}}}\n"
                    if caption:
                        latex += f"\\caption{{{self.escape_latex(caption)}}}\n"
                    latex += "\\end{figure}\n\n"

        # Process subsections
        subsections = section.get("subsections", [])
        for subsection in subsections:
            latex += self.format_section(subsection, depth + 1)

        return latex

    def format_table(self, table: Dict[str, Any], caption: str = "") -> str:
        """Format a table in LaTeX."""
        rows = table.get("rows", [])
        headers = table.get("headers", [])

        if not rows:
            return ""

        # Estimate columns
        num_cols = len(headers) if headers else (len(rows[0]) if rows else 1)

        latex = "\\begin{table}[!htbp]\n\\centering\n"
        if caption:
            # \caption{} already prints its own "Table N:" prefix — strip
            # the manuscript's own "Table N" label so it isn't doubled.
            caption_text = _LEADING_TABLE_LABEL_RE.sub('', caption).strip()
            if caption_text:
                latex += f"\\caption{{{self.escape_latex(caption_text)}}}\n"

        # tabularx's X columns share the available \textwidth and wrap cell
        # text to fit, instead of plain "l" columns running off the page
        # edge for wide tables.
        latex += f"\\begin{{tabularx}}{{\\textwidth}}{{|*{{{num_cols}}}{{X|}}}}\n\\hline\n"

        # Headers
        if headers:
            latex += " & ".join(self.escape_latex(str(h)) for h in headers)
            latex += " \\\\\n\\hline\n"

        # Rows
        for row in rows:
            latex += " & ".join(self.escape_latex(str(cell)) for cell in row)
            latex += " \\\\\n"

        latex += "\\hline\n\\end{tabularx}\n\\end{table}\n\n"
        return latex

    def format_references(self) -> str:
        """Format references section."""
        if not self.references:
            return ""

        latex = "\\begin{thebibliography}{99}\n\n"

        for i, ref in enumerate(self.references, 1):
            if isinstance(ref, dict):
                text = ref.get("raw_text") or ref.get("text", "")
            else:
                text = str(ref)

            if text:
                latex += f"\\bibitem{{{i}}} {self.escape_latex(text)}\n\n"

        latex += "\\end{thebibliography}\n"
        return latex

    def format_journal_header(self) -> str:
        """
        Journal branding (name, publisher, logo) printed above the title —
        a self-contained block that doesn't touch \\title{}/\\author{}/
        \\maketitle, so their formatting is unaffected either way.
        """
        journal_logo = self.article.get("journal_logo", "")
        publisher_name = self.article.get("publisher_name", "")

        lines = []
        logo_path = self._write_image(journal_logo, "journal_logo")
        if logo_path:
            lines.append(f"\\includegraphics[height=1.4cm]{{{logo_path}}}")
        if self.journal_name:
            lines.append(f"\\textbf{{{self.escape_latex(self.journal_name)}}}")
        if publisher_name:
            lines.append(f"\\textit{{{self.escape_latex(publisher_name)}}}")

        if not lines:
            return ""
        return "\\begin{center}\n" + " \\\\\n".join(lines) + "\n\\end{center}\n\\vspace{6pt}\n\n"

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
\usepackage{tabularx}
\usepackage{authblk}

\raggedbottom
% A little breathing room between paragraphs — spacing only, the default
% \parindent (and everything else about the existing text style) is untouched.
\setlength{\parskip}{6pt plus 2pt minus 1pt}

"""

        # Title
        latex += f"\\title{{{self.escape_latex(self.title)}}}\n"

        # Authors — format_authors() returns complete \author[]{}/\affil[]{}
        # commands (authblk), not a plain name list to wrap in \author{}.
        if self.authors:
            latex += f"{self.format_authors()}\n"

        # Date
        latex += "\\date{}\n\n"

        latex += "\\begin{document}\n\n"

        # Journal header (name, publisher, logo) — printed above the title,
        # entirely separate from \title{}/\author{}/\maketitle below so
        # their existing formatting is untouched.
        latex += self.format_journal_header()

        latex += "\\maketitle\n\n"

        # Abstract
        if self.abstract:
            latex += "\\begin{abstract}\n"
            latex += f"{self.escape_latex(self.abstract)}\n"
            latex += "\\end{abstract}\n\n"

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
