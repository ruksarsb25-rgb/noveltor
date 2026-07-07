"""
Parse DOCX files to extract poster metadata and image.
Expected document structure:
- Title (heading or first paragraph)
- Authors (with affiliations)
- Abstract
- Poster image (embedded image in document)
"""

import base64
import io
import subprocess
import tempfile
import os
from pathlib import Path
from docx import Document
from typing import Dict, Any


def _convert_image_via_libreoffice(image_bytes: bytes) -> str:
    """
    Convert large images (EMF, etc) to PNG via LibreOffice.
    Returns base64-encoded PNG or empty string if conversion fails.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Save raw image
            input_path = tmpdir / "image.emf"
            input_path.write_bytes(image_bytes)

            # Convert to PNG via LibreOffice with size limit
            output_path = tmpdir / "image.png"

            # Use LibreOffice to convert
            soffice_path = _find_soffice()
            if not soffice_path:
                return ""

            cmd = [
                soffice_path,
                "--headless",
                "--convert-to", "png",
                "--outdir", str(tmpdir),
                str(input_path),
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=30)

            if result.returncode != 0 or not output_path.exists():
                return ""

            # Read PNG and resize if needed
            png_bytes = output_path.read_bytes()

            # If still too large, resize with PIL
            if len(png_bytes) > 2 * 1024 * 1024:
                try:
                    from PIL import Image

                    img = Image.open(io.BytesIO(png_bytes))
                    max_dim = 1024
                    if img.width > max_dim or img.height > max_dim:
                        ratio = min(max_dim / img.width, max_dim / img.height)
                        new_size = (int(img.width * ratio), int(img.height * ratio))
                        img = img.resize(new_size, Image.Resampling.LANCZOS)

                    # Re-encode as optimized PNG
                    optimized = io.BytesIO()
                    img.save(optimized, format="PNG", optimize=True, quality=85)
                    png_bytes = optimized.getvalue()
                except Exception:
                    pass  # Use PNG as-is if PIL fails

            # Base64 encode
            return base64.b64encode(png_bytes).decode("utf-8")

    except Exception:
        return ""


def _find_soffice() -> str:
    """Find LibreOffice soffice command."""
    import platform

    if platform.system() == "Darwin":  # macOS
        paths = [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        ]
    else:  # Linux
        paths = ["/usr/bin/soffice", "/usr/local/bin/soffice"]

    for path in paths:
        if os.path.exists(path):
            return path

    # Try in PATH
    result = subprocess.run(["which", "soffice"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()

    return ""


def parse_poster(docx_path: str) -> Dict[str, Any]:
    """
    Parse a DOCX file as a poster document.

    Structure expected:
    - Line 1: Title
    - Line 2: Authors (separated by commas)
    - Line 3: Affiliation
    - Line 4: Email/Contact
    - Line N: "Abstract"
    - Following lines: Abstract text
    - Images: Embedded poster image

    Returns:
        Dict with keys:
            - type: "poster"
            - title: str
            - authors: list of {"first_name", "last_name", "affiliation"}
            - abstract: str
            - poster_image: str (base64 encoded image or empty)
    """
    doc = Document(docx_path)

    title = ""
    authors = []
    affiliation = ""
    abstract = ""
    poster_image = ""

    # Extract paragraphs with text
    paragraphs_text = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs_text.append(text)

    if not paragraphs_text:
        return {
            "type": "poster",
            "title": "Untitled Poster",
            "authors": [{"first_name": "Author", "last_name": "Name", "affiliation": ""}],
            "abstract": "",
            "poster_image": "",
        }

    # Line 0: Title
    title = paragraphs_text[0]

    # Line 1: Authors (comma-separated: "FirstName LastName, FirstName LastName, ...")
    authors_str = paragraphs_text[1] if len(paragraphs_text) > 1 else ""
    author_names = [a.strip() for a in authors_str.split(",")]

    # Line 2: Affiliation
    affiliation = paragraphs_text[2] if len(paragraphs_text) > 2 else ""

    # Extract authors with shared affiliation
    for author_str in author_names:
        if author_str:
            # Try to split into first and last name
            parts = author_str.rsplit(" ", 1)
            if len(parts) == 2:
                authors.append({
                    "first_name": parts[0].strip(),
                    "last_name": parts[1].strip(),
                    "affiliation": affiliation,
                })
            elif parts:
                authors.append({
                    "first_name": parts[0].strip(),
                    "last_name": "",
                    "affiliation": affiliation,
                })

    # Find Abstract section and extract text
    abstract_idx = -1
    for i, text in enumerate(paragraphs_text):
        if text.lower().startswith("abstract"):
            abstract_idx = i
            break

    if abstract_idx >= 0:
        # Collect abstract text until we hit another section (Keywords, Author Contributions, etc.)
        abstract_lines = []
        for i in range(abstract_idx + 1, len(paragraphs_text)):
            section_keywords = [
                "keywords",
                "author contributions",
                "funding",
                "data availability",
                "acknowledgments",
                "conflicts of interest",
                "references",
            ]
            if any(
                paragraphs_text[i].lower().startswith(kw)
                for kw in section_keywords
            ):
                break
            abstract_lines.append(paragraphs_text[i])

        abstract = " ".join(abstract_lines).strip()

    # Find References section and extract
    references = []
    references_idx = -1
    for i, text in enumerate(paragraphs_text):
        if text.lower().startswith("references"):
            references_idx = i
            break

    if references_idx >= 0:
        for i in range(references_idx + 1, len(paragraphs_text)):
            ref_text = paragraphs_text[i].strip()
            # Stop if we hit another major section
            if any(
                ref_text.lower().startswith(kw)
                for kw in ["author contributions", "funding", "acknowledgments"]
            ):
                break
            if ref_text:  # Skip empty lines
                references.append({"raw_text": ref_text})

    # Extract embedded images and convert to base64
    poster_image = ""
    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            try:
                image_part = rel.target_part
                image_bytes = image_part.blob

                # If image is small (<5MB), use as-is. Otherwise convert via LibreOffice
                if len(image_bytes) < 5 * 1024 * 1024:
                    # Small image, just base64 encode
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                else:
                    # Large image (probably EMF), convert to PNG via LibreOffice
                    image_base64 = _convert_image_via_libreoffice(image_bytes)

                if image_base64:
                    poster_image = image_base64
                    break
            except Exception:
                continue

    # Fallback: if no authors extracted, create default
    if not authors:
        authors = [{"first_name": "Author", "last_name": "Name", "affiliation": affiliation}]

    return {
        "type": "poster",
        "title": title or "Untitled Poster",
        "authors": authors,
        "abstract": abstract,
        "references": references,
        "poster_image": poster_image,
    }
