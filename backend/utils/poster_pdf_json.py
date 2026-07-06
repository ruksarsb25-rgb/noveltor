"""
Generate poster PDFs from JSON data (parsed poster metadata).
Simpler than the DOCX approach - works directly with extracted data.
"""

import io
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any


def generate_poster_pdf_from_json(poster_data: Dict[str, Any], journal_logo: str = "", publisher_logo: str = "") -> bytes:
    """
    Generate poster PDF from parsed JSON data.

    Args:
        poster_data: Poster metadata from parser (title, authors, abstract, image, references)
        journal_logo: Optional base64 journal logo
        publisher_logo: Optional base64 publisher logo

    Returns:
        PDF as bytes
    """
    from utils.poster_latex import PosterLaTeXGenerator
    from utils.pdf_logos import add_logos_to_pdf

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Generate LaTeX
        generator = PosterLaTeXGenerator(poster_data)
        generator.references = poster_data.get("references", [])
        latex_source = generator.generate(tmpdir)

        # Write LaTeX
        tex_file = tmpdir / "poster.tex"
        tex_file.write_text(latex_source, encoding="utf-8")

        # Compile with pdflatex
        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-output-directory", str(tmpdir), str(tex_file)],
                capture_output=True,
                timeout=60
            )

            if result.returncode != 0:
                error_msg = result.stdout.decode("utf-8", errors="ignore")
                raise Exception(f"LaTeX compilation failed:\n{error_msg}")

            pdf_file = tmpdir / "poster.pdf"
            if not pdf_file.exists():
                raise Exception("PDF generation failed: output file not created")

            pdf_bytes = pdf_file.read_bytes()

            # Add logos if provided
            if journal_logo or publisher_logo:
                pdf_bytes = add_logos_to_pdf(pdf_bytes, journal_logo, publisher_logo)

            return pdf_bytes

        except subprocess.TimeoutExpired:
            raise Exception("LaTeX compilation timed out")
        except FileNotFoundError:
            raise Exception("pdflatex not found. Please install LaTeX.")
