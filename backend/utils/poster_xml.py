"""
Generate JATS XML documents for posters.
"""

import base64
from xml.etree.ElementTree import Element, SubElement, tostring
from typing import Dict, Any


def generate_poster_xml(poster: Dict[str, Any]) -> str:
    """
    Generate JATS XML for poster.

    Args:
        poster: Dict with poster data

    Returns:
        XML string
    """
    # Root element
    root = Element("article")
    root.set("xmlns:xlink", "http://www.w3.org/1999/xlink")
    root.set("xmlns:mml", "http://www.w3.org/1998/Math/MathML")

    # Front matter
    front = SubElement(root, "front")

    # Article metadata
    article_meta = SubElement(front, "article-meta")

    # Title group
    title_group = SubElement(article_meta, "title-group")
    article_title = SubElement(title_group, "article-title")
    article_title.text = poster.get("title", "Untitled Poster")

    # Contrib group (authors)
    contrib_group = SubElement(article_meta, "contrib-group")
    authors = poster.get("authors", [])

    for author in authors:
        contrib = SubElement(contrib_group, "contrib")
        contrib.set("contrib-type", "author")

        name = SubElement(contrib, "name")
        surname = SubElement(name, "surname")
        surname.text = author.get("last_name", "")

        given_names = SubElement(name, "given-names")
        given_names.text = author.get("first_name", "")

        # Affiliation
        affiliation_text = author.get("affiliation", "")
        if affiliation_text:
            aff = SubElement(contrib, "aff")
            aff.text = affiliation_text

    # Abstract
    abstract_text = poster.get("abstract", "")
    if abstract_text:
        abstract = SubElement(article_meta, "abstract")
        abstract_p = SubElement(abstract, "p")
        abstract_p.text = abstract_text

    # Body with poster image
    body = SubElement(root, "body")
    sec = SubElement(body, "sec")

    # Poster image as graphic element (embedded as base64)
    poster_image = poster.get("poster_image", "")
    if poster_image:
        graphic = SubElement(sec, "graphic")
        graphic.set("xlink:href", f"data:image/png;base64,{poster_image}")
        graphic.set("position", "anchor")
        label = SubElement(graphic, "label")
        label.text = "Poster Image"

    # Convert to string
    xml_bytes = tostring(root, encoding="unicode")

    # Pretty print with declaration
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_str += '<!DOCTYPE article PUBLIC "-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.0 20120330//EN" "JATS-journalpublishing1.dtd">\n'
    xml_str += xml_bytes

    return xml_str
