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
    abstract = ""
    poster_image = ""

    # Extract title from first non-empty paragraph
    for para in doc.paragraphs[:10]:
        text = para.text.strip()
        if text and not title:
            title = text
            break

    # Extract body text for authors and abstract
    body_text = []
    for para in doc.paragraphs[1:]:
        text = para.text.strip()
        if text:
            body_text.append(text)

    # Simple heuristic: look for "Abstract" or "ABSTRACT" keyword
    abstract_idx = -1
    for i, text in enumerate(body_text):
        if "abstract" in text.lower():
            abstract_idx = i
            break

    # If abstract found, extract it (next paragraph(s) until we hit something else)
    if abstract_idx >= 0:
        # Combine remaining paragraphs as abstract (simplified)
        abstract_parts = []
        for i in range(abstract_idx + 1, len(body_text)):
            if body_text[i]:
                abstract_parts.append(body_text[i])
                # Stop if we hit too much text (assume abstract is first ~500 chars)
                if len(" ".join(abstract_parts)) > 500:
                    break
        abstract = " ".join(abstract_parts)

    # Extract authors with affiliations
    # Simple approach: parse from document metadata or body
    authors_from_meta = []

    # Try to get authors from document core properties
    if doc.core_properties.author:
        author_names = doc.core_properties.author.split(",")
        for name in author_names:
            name = name.strip()
            if name:
                parts = name.rsplit(" ", 1)  # Split by last space
                if len(parts) == 2:
                    authors_from_meta.append({
                        "first_name": parts[0],
                        "last_name": parts[1],
                        "affiliation": ""
                    })

    if authors_from_meta:
        authors = authors_from_meta
    else:
        # Create default author if none found
        authors = [{
            "first_name": "Author",
            "last_name": "Name",
            "affiliation": ""
        }]

    # Extract embedded images and convert first one to base64
    poster_image = ""
    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            try:
                image_part = rel.target_part
                image_bytes = image_part.blob
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                # Use first image found
                poster_image = image_base64
                break
            except Exception:
                continue

    return {
        "type": "poster",
        "title": title or "Untitled Poster",
        "authors": authors,
        "abstract": abstract,
        "poster_image": poster_image,
    }
