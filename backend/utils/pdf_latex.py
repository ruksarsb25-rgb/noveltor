"""
Generate PDFs using LaTeX for professional mathematical typesetting.
Replaces WeasyPrint for better equation rendering and academic appearance.
"""

import re
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, Any

_LINE_REF_RE = re.compile(r'^l\.(\d+)')


def _extract_latex_error(log: str, latex_source: str = "") -> str:
    """
    Pull the actual error out of a pdflatex log.

    pdflatex's stdout is dominated by dozens of lines of harmless
    "(/usr/share/texlive/.../package.sty)" package-loading noise before it
    ever reaches the real failure — a line starting with "!" followed by an
    "l.NNN" line-number reference into the generated .tex file. Any caller
    that truncates a long error message (a toast, a UI panel) ends up
    showing only that boilerplate and never the actual problem. Surface the
    "!" block first — with the offending source line quoted directly, when
    the log's "l.NNN" reference lets us look it up — and the full log after
    for reference.
    """
    lines = log.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('!'):
            block = lines[i:i + 8]
            if latex_source:
                src_lines = latex_source.splitlines()
                for bl in block:
                    m = _LINE_REF_RE.match(bl)
                    if m:
                        n = int(m.group(1))
                        if 1 <= n <= len(src_lines):
                            block.append(f'--- document.tex line {n} ---')
                            block.append(src_lines[n - 1])
                        break
            return '\n'.join(block)
    # No "!" marker found (e.g. a crash before LaTeX started reporting
    # errors normally) — fall back to the tail of the log, which is closer
    # to the actual failure than the package-loading preamble at the top.
    return '\n'.join(lines[-25:])


def generate_pdf_from_latex(article: Dict[str, Any]) -> bytes:
    """
    Generate a professional PDF from article data using LaTeX.

    Returns:
        PDF file as bytes
    """
    from utils.latex_converter import LaTeXGenerator

    # Generate LaTeX source
    from utils.latex_converter import LaTeXGenerator

    generator = LaTeXGenerator(article)
    latex_source = generator.generate()

    # Create temporary directory for LaTeX compilation
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Write LaTeX source to file
        tex_file = tmpdir / "document.tex"
        tex_file.write_text(latex_source, encoding='utf-8')

        # Run pdflatex
        try:
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-output-directory", str(tmpdir),
                    str(tex_file)
                ],
                capture_output=True,
                timeout=30
            )

            if result.returncode != 0:
                full_log = result.stdout.decode('utf-8', errors='ignore')
                summary = _extract_latex_error(full_log, latex_source)
                raise Exception(
                    f"LaTeX compilation failed:\n{summary}\n\n"
                    f"--- full log ---\n{full_log}"
                )

            # Read generated PDF
            pdf_file = tmpdir / "document.pdf"
            if not pdf_file.exists():
                raise Exception("PDF generation failed: output file not created")

            return pdf_file.read_bytes()

        except subprocess.TimeoutExpired:
            raise Exception("LaTeX compilation timed out")
        except FileNotFoundError:
            raise Exception(
                "pdflatex not found. Please install LaTeX (MacTeX, TeX Live, or MiKTeX) "
                "and ensure pdflatex is in your PATH"
            )
