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
from docx import Document
from typing import Dict, Any


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
                from PIL import Image
                import io as io_module
                import warnings

                image_part = rel.target_part
                image_bytes = image_part.blob

                print(f"[POSTER] Extracted image: {len(image_bytes)} bytes")

                # Convert to PIL Image to resize if too large
                try:
                    # Disable decompression bomb check for large images
                    Image.MAX_IMAGE_PIXELS = None

                    # Suppress decompression bomb warnings
                    warnings.filterwarnings('ignore', category=Image.DecompressionBombWarning)

                    img = Image.open(io_module.BytesIO(image_bytes))
                    print(f"[POSTER] Image opened: {img.format} {img.width}x{img.height} {img.mode}")

                    # Resize if too large (max 2000x2000 to keep base64 reasonable)
                    max_dim = 2000
                    if img.width > max_dim or img.height > max_dim:
                        ratio = min(max_dim / img.width, max_dim / img.height)
                        new_size = (int(img.width * ratio), int(img.height * ratio))
                        print(f"[POSTER] Resizing from {img.width}x{img.height} to {new_size}")
                        img = img.resize(new_size, Image.Resampling.LANCZOS)

                    # Convert to RGB and save as PNG
                    if img.mode in ("RGBA", "LA", "P"):
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == "RGBA":
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img)
                        img = background

                    # Encode as PNG (smaller than EMF)
                    png_bytes = io_module.BytesIO()
                    img.save(png_bytes, format="PNG", optimize=True)
                    image_base64 = base64.b64encode(png_bytes.getvalue()).decode("utf-8")
                    print(f"[POSTER] Compressed to PNG: {len(image_base64)} base64 bytes")

                except Exception as e:
                    # Fallback: just base64 encode raw bytes if PIL conversion fails
                    print(f"[POSTER] PIL conversion failed: {e}, using raw bytes")
                    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

                # Use first image found as poster
                poster_image = image_base64
                break
            except Exception as e:
                print(f"[POSTER] Error extracting image: {e}")
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
