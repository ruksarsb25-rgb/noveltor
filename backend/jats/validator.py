"""
JATS XML validator — checks structural requirements and NFP consistency rules.
Returns {valid, errors, warnings} without requiring network access.
"""
import re
from xml.etree import ElementTree as ET


REQUIRED_ELEMENTS = [
    ("journal-meta", "//front/journal-meta"),
    ("article-meta", "//front/article-meta"),
    ("body", "//body"),
    ("back", "//back"),
]


def validate_jats(xml_string: str) -> dict:
    errors = []
    warnings = []

    # Strip DTD declaration for local parsing
    clean_xml = re.sub(r"<!DOCTYPE[^>]+>", "", xml_string)
    clean_xml = re.sub(r"<\?xml[^>]+\?>", "", clean_xml).strip()

    try:
        root = ET.fromstring(clean_xml)
    except ET.ParseError as e:
        return {"valid": False, "errors": [f"XML parse error: {e}"], "warnings": []}

    ns = {"xlink": "http://www.w3.org/1999/xlink"}

    # Required top-level attributes
    if root.get("article-type") is None:
        errors.append("Missing required attribute: article-type on <article>")
    if root.get("{http://www.w3.org/XML/1998/namespace}lang") is None and root.get("xml:lang") is None:
        errors.append("Missing required attribute: xml:lang on <article>")
    if root.get("dtd-version") is None:
        warnings.append("Missing dtd-version attribute on <article>")

    front = root.find("front")
    if front is None:
        errors.append("Missing <front> element")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    # Journal meta
    jm = front.find("journal-meta")
    if jm is None:
        errors.append("Missing <journal-meta> inside <front>")
    else:
        if jm.find("journal-title-group/journal-title") is None:
            errors.append("Missing <journal-title> inside <journal-meta>")
        if jm.find("publisher/publisher-name") is None:
            errors.append("Missing <publisher-name> inside <journal-meta>")

    # Article meta
    am = front.find("article-meta")
    if am is None:
        errors.append("Missing <article-meta> inside <front>")
    else:
        title_el = am.find("title-group/article-title")
        if title_el is None or not (title_el.text or "").strip():
            errors.append("Missing or empty <article-title>")

        # Abstract word count check
        abstract_el = am.find("abstract")
        if abstract_el is not None:
            abstract_text = " ".join(abstract_el.itertext())
            word_count = len(abstract_text.split())
            if word_count < 150:
                warnings.append(f"Abstract has {word_count} words — minimum is 150")
            elif word_count > 300:
                warnings.append(f"Abstract has {word_count} words — maximum is 300")
        else:
            errors.append("Missing <abstract>")

        # Keywords
        kwd_group = am.find("kwd-group")
        if kwd_group is not None:
            kwds = kwd_group.findall("kwd")
            if len(kwds) < 3:
                errors.append(f"Only {len(kwds)} keyword(s) found — minimum is 3")
            elif len(kwds) > 10:
                errors.append(f"{len(kwds)} keywords found — maximum is 10")
        else:
            warnings.append("No <kwd-group> found — keywords recommended")

        # DOI check
        doi_el = am.find("article-id[@pub-id-type='doi']")
        if doi_el is not None and doi_el.text:
            if not re.match(r"^10\.\d{4,}/\S+$", doi_el.text.strip()):
                errors.append(f"DOI format invalid: '{doi_el.text}' — expected pattern 10.XXXX/xxx")
        else:
            warnings.append("No DOI found in article-meta")

        # Author checks
        contribs = am.findall(".//contrib[@contrib-type='author']")
        if not contribs:
            errors.append("No <contrib contrib-type='author'> elements found")
        else:
            has_corresponding = False
            for contrib in contribs:
                name_el = contrib.find("name")
                if name_el is not None:
                    surname = (name_el.findtext("surname") or "").strip()
                    given = (name_el.findtext("given-names") or "").strip()
                    if not surname or not given:
                        errors.append(f"Author missing first or last name: '{given} {surname}'")
                if contrib.get("corresp") == "yes":
                    has_corresponding = True
                    if not (contrib.findtext("email") or "").strip():
                        errors.append("Corresponding author must have an email address")
            if not has_corresponding:
                errors.append("At least one author must be marked corresp='yes'")

    # Body checks
    body = root.find("body")
    if body is None:
        errors.append("Missing <body> element")
    else:
        secs = body.findall("sec")
        if not secs:
            warnings.append("No <sec> elements found in <body>")
        for sec in secs:
            title_el = sec.find("title")
            if title_el is None or not (title_el.text or "").strip():
                errors.append("A <sec> element is missing a non-empty <title>")

    # Back / references
    back = root.find("back")
    if back is None:
        warnings.append("Missing <back> element — references and figures should be here")
    else:
        ref_list = back.find("ref-list")
        if ref_list is not None:
            refs = ref_list.findall("ref")
            for i, ref in enumerate(refs, 1):
                if ref.get("id") != f"ref{i}":
                    warnings.append(f"Reference id mismatch at position {i}: expected 'ref{i}', got '{ref.get('id')}'")

        # Figure captions
        for fig in back.findall("fig"):
            cap = fig.find("caption/p")
            if cap is None or not (cap.text or "").strip():
                fig_id = fig.get("id", "unknown")
                errors.append(f"Figure '{fig_id}' is missing a caption")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
