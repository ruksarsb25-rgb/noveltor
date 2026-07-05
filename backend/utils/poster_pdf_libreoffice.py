"""
Generate PDFs for posters using LibreOffice conversion.
Converts DOCX → PDF with embedded images, much more reliable than manual EMF handling.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any


def generate_poster_pdf_libreoffice(docx_path: str) -> bytes:
    """
    Convert poster DOCX to PDF using LibreOffice.

    Args:
        docx_path: Path to the DOCX file

    Returns:
        PDF file as bytes
    """
    import platform

    docx_path = Path(docx_path)

    if not docx_path.exists():
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Detect LibreOffice path based on OS
        system = platform.system()
        if system == "Darwin":
            # macOS
            libreoffice_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        else:
            # Linux and others - use 'soffice' from PATH
            libreoffice_path = "soffice"

        try:
            # Convert DOCX to PDF using LibreOffice
            result = subprocess.run(
                [
                    libreoffice_path,
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", str(tmpdir),
                    str(docx_path)
                ],
                capture_output=True,
                timeout=120
            )

            if result.returncode != 0:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                raise Exception(f"LibreOffice conversion failed:\n{error_msg}")

            # Find the generated PDF
            pdf_file = tmpdir / docx_path.with_suffix('.pdf').name

            if not pdf_file.exists():
                raise Exception("PDF generation failed: output file not created")

            return pdf_file.read_bytes()

        except FileNotFoundError:
            raise Exception(
                "LibreOffice not found. Please install: "
                "(macOS) brew install libreoffice OR "
                "(Linux) apt-get install libreoffice"
            )
        except subprocess.TimeoutExpired:
            raise Exception("LibreOffice conversion timed out")
