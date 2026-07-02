"""
Generate PDFs for posters using LaTeX.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any


def generate_poster_pdf_latex(poster: Dict[str, Any]) -> bytes:
    """
    Generate a professional PDF from poster data using LaTeX.

    Args:
        poster: Dict with poster data

    Returns:
        PDF file as bytes
    """
    from utils.poster_latex import PosterLaTeXGenerator

    # Create temporary directory for LaTeX compilation
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Generate LaTeX source
        generator = PosterLaTeXGenerator(poster)
        latex_source = generator.generate(tmpdir)

        # Write LaTeX source to file
        tex_file = tmpdir / "document.tex"
        tex_file.write_text(latex_source, encoding="utf-8")

        # Run pdflatex
        try:
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-output-directory",
                    str(tmpdir),
                    str(tex_file),
                ],
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                error_msg = result.stdout.decode("utf-8", errors="ignore")
                raise Exception(f"LaTeX compilation failed:\n{error_msg}")

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
