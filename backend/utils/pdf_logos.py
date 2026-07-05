"""
Add logos to PDF header (top-left journal logo, top-right publisher logo).
"""

import base64
import io
import tempfile
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image


def add_logos_to_pdf(pdf_bytes: bytes, journal_logo: str = "", publisher_logo: str = "") -> bytes:
    """
    Add journal and publisher logos to first page header.

    Args:
        pdf_bytes: Original PDF as bytes
        journal_logo: Base64 encoded journal logo image
        publisher_logo: Base64 encoded publisher logo image

    Returns:
        Modified PDF as bytes
    """
    if not journal_logo and not publisher_logo:
        return pdf_bytes

    try:
        # Create temporary files for logos
        journal_img_path = None
        publisher_img_path = None

        if journal_logo:
            journal_img_path = _base64_to_temp_file(journal_logo)

        if publisher_logo:
            publisher_img_path = _base64_to_temp_file(publisher_logo)

        if not journal_img_path and not publisher_img_path:
            return pdf_bytes

        # Read original PDF
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()

        # Process pages
        for idx, page in enumerate(reader.pages):
            if idx == 0:
                # Only add logos to first page
                # Create an overlay with logos
                overlay_buffer = io.BytesIO()

                # Get page dimensions
                page_width = float(page.mediabox.width)
                page_height = float(page.mediabox.height)

                c = canvas.Canvas(overlay_buffer, pagesize=(page_width, page_height))

                # Add journal logo (top-left)
                if journal_img_path:
                    try:
                        c.drawImage(journal_img_path, 30, page_height - 80, width=120, height=70, preserveAspectRatio=True)
                    except Exception as e:
                        print(f"Warning: Could not add journal logo: {e}")

                # Add publisher logo (top-right)
                if publisher_img_path:
                    try:
                        c.drawImage(publisher_img_path, page_width - 150, page_height - 80, width=120, height=70, preserveAspectRatio=True)
                    except Exception as e:
                        print(f"Warning: Could not add publisher logo: {e}")

                c.save()
                overlay_buffer.seek(0)

                # Merge overlay with first page
                overlay_reader = PdfReader(overlay_buffer)
                if len(overlay_reader.pages) > 0:
                    overlay_page = overlay_reader.pages[0]
                    page.merge_page(overlay_page)

            writer.add_page(page)

        # Write result
        output = io.BytesIO()
        writer.write(output)
        output.seek(0)
        return output.read()

    except Exception as e:
        print(f"Warning: Could not add logos to PDF: {e}")
        return pdf_bytes
    finally:
        # Cleanup temp files
        try:
            if journal_img_path and Path(journal_img_path).exists():
                Path(journal_img_path).unlink()
            if publisher_img_path and Path(publisher_img_path).exists():
                Path(publisher_img_path).unlink()
        except Exception:
            pass


def _base64_to_temp_file(base64_str: str) -> str:
    """Convert base64 string to temporary image file."""
    try:
        # Handle data URI format
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]

        image_bytes = base64.b64decode(base64_str)

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(image_bytes)
            return tmp.name
    except Exception as e:
        print(f"Warning: Could not convert base64 to image: {e}")
        return None
