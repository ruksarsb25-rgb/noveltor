"""
Convert article content to LaTeX format for professional PDF generation.
Handles equations, sections, references, figures, and proper mathematical typesetting.
"""

import re
from typing import Dict, List, Any

from utils.equations import _LATEX_SYMBOL_MAP, _normalize_math_alphanumerics

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

    def __init__(self, article: Dict[str, Any]):
        self.article = article
        self.journal_name = article.get("journal_name", "Novel Future Publishing")
        self.title = article.get("title", "Untitled")
        self.authors = article.get("authors", [])
        self.abstract = article.get("abstract", "")
        self.keywords = article.get("keywords", [])
        self.sections = article.get("sections", [])
        self.references = article.get("references", [])

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

        # 1. Escape LaTeX-reserved characters first, on the raw text — the
        #    LaTeX commands inserted in step 2 must not be re-escaped.
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

        # 2. Unicode subscript/superscript digits (e.g. "BaAl₂O₄") → real
        #    LaTeX subscript/superscript math, the standard way chemical
        #    formulas are written in LaTeX.
        text = _SUB_RUN_RE.sub(lambda m: '$_{' + ''.join(_SUB_MAP[c] for c in m.group()) + '}$', text)
        text = _SUP_RUN_RE.sub(lambda m: '$^{' + ''.join(_SUP_MAP[c] for c in m.group()) + '}$', text)

        # 3. Dashes — LaTeX's own text-mode ligatures
        text = text.replace('—', '---').replace('–', '--')

        # 4. Greek letters / math operators appearing in plain prose (e.g.
        #    "λ - wavelength of Cu Kα radiation") — wrap each individually
        #    in inline math since they're not valid outside math mode.
        text = ''.join(f'${_LATEX_SYMBOL_MAP[c]}$' if c in _LATEX_SYMBOL_MAP else c for c in text)

        return text

    def format_authors(self) -> str:
        """Format author list with affiliations."""
        if not self.authors:
            return ""

        author_list = []
        for author in self.authors:
            first_name = author.get('first_name', '').strip()
            last_name = author.get('last_name', '').strip()
            name = f"{first_name} {last_name}".strip()
            if name:
                author_list.append(self.escape_latex(name))

        return ' \\and '.join(author_list) if author_list else ""

    def format_section(self, section: Dict[str, Any], depth: int = 1) -> str:
        """Format a section with content and subsections."""
        latex = ""

        heading = section.get("heading", "").strip()
        if heading:
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
                latex += f"% {label}: {self.escape_latex(caption)}\n\n"

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
            latex += f"\\caption{{{self.escape_latex(caption)}}}\n"

        latex += f"\\begin{{tabular}}{{{'|'.join(['l'] * num_cols)}}}\n\\hline\n"

        # Headers
        if headers:
            latex += " & ".join(self.escape_latex(str(h)) for h in headers)
            latex += " \\\\\n\\hline\n"

        # Rows
        for row in rows:
            latex += " & ".join(self.escape_latex(str(cell)) for cell in row)
            latex += " \\\\\n"

        latex += "\\hline\n\\end{tabular}\n\\end{table}\n\n"
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

\raggedbottom

"""

        # Title
        latex += f"\\title{{{self.escape_latex(self.title)}}}\n"

        # Authors
        if self.authors:
            latex += f"\\author{{{self.format_authors()}}}\n"

        # Date
        latex += "\\date{}\n\n"

        latex += "\\begin{document}\n\n"
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
