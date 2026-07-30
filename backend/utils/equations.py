"""
Equation utilities for converting between formats (OMML, LaTeX, MathML).
Supports multiple export formats: Word, XML/JATS, HTML, PDF.
"""
import re
from lxml import etree

def extract_equation_text(omml_str: str, html_sub_sup: bool = False) -> str:
    """
    Extract text representation from OMML, preserving subscripts/superscripts.
    Recursively processes all elements including nested fractions, subscripts, etc.

    By default converts subscripts/superscripts to Unicode characters
    (₀₁₂₃₄₅₆₇₈₉) for readability in plain-text contexts (PDF/Word fallback
    text). Pass html_sub_sup=True to wrap them in <sub>/<sup> tags instead —
    used when this text is spliced into ordinary paragraph text, which is
    rendered through the same <sub>/<sup>-aware pipeline as the rest of the
    document (see _run_text_with_fmt in docx_parser.py).
    """
    if not omml_str:
        return ""

    # Unicode subscript and superscript mappings
    subscript_map = {
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
        '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
        'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
        'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ',
        'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
        'v': 'ᵥ', 'x': 'ₓ', '-': '₋', '+': '₊', '=': '₌',
    }

    superscript_map = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
        '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
        'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ',
        'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',
        'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ',
        'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
        'v': 'ᵛ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ', '-': '⁻',
        '+': '⁺', '=': '⁼',
    }

    try:
        omml = etree.fromstring(omml_str.encode('utf-8'))

        def get_tag_name(elem):
            """Extract local tag from namespaced element."""
            return elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        def process_element(elem):
            """
            Recursively process an OMML element and return its text representation.
            Handles subscripts, superscripts, fractions, and all nested structures.
            """
            result = ""
            tag_name = get_tag_name(elem)

            # Text element
            if tag_name == 't':
                return elem.text or ""

            # Regular text run (m:r)
            elif tag_name == 'r':
                for child in elem:
                    result += process_element(child)

            # Script subscript (m:sSub: base + subscript). The 'e' (base) and
            # 'sub' (subscript) children are processed as-is — 'sub' already
            # applies the subscript conversion itself, so it isn't repeated here.
            elif tag_name == 'sSub':
                for child in elem:
                    child_tag = get_tag_name(child)
                    if child_tag in ('e', 'sub'):
                        result += process_element(child)

            # Script superscript (m:sSup: base + superscript). Same note as sSub.
            elif tag_name == 'sSup':
                for child in elem:
                    child_tag = get_tag_name(child)
                    if child_tag in ('e', 'sup'):
                        result += process_element(child)

            # Regular subscript (m:sub)
            elif tag_name == 'sub':
                sub_text = ""
                for child in elem:
                    sub_text += process_element(child)
                if html_sub_sup:
                    result += f'<sub>{sub_text}</sub>'
                else:
                    result += ''.join(subscript_map.get(c, c) for c in sub_text)

            # Regular superscript (m:sup)
            elif tag_name == 'sup':
                sup_text = ""
                for child in elem:
                    sup_text += process_element(child)
                if html_sub_sup:
                    result += f'<sup>{sup_text}</sup>'
                else:
                    result += ''.join(superscript_map.get(c, c) for c in sup_text)

            # Fraction (m:f: numerator / denominator)
            elif tag_name == 'f':
                num_text = ""
                den_text = ""
                for child in elem:
                    child_tag = get_tag_name(child)
                    if child_tag == 'num':
                        num_text = process_element(child)
                    elif child_tag == 'den':
                        den_text = process_element(child)
                if num_text or den_text:
                    result += f"{num_text}/{den_text}"

            # Element wrapper (m:e)
            elif tag_name == 'e':
                for child in elem:
                    result += process_element(child)

            # Numerator (m:num)
            elif tag_name == 'num':
                for child in elem:
                    result += process_element(child)

            # Denominator (m:den)
            elif tag_name == 'den':
                for child in elem:
                    result += process_element(child)

            # Bracket/delimiter (m:d)
            elif tag_name == 'd':
                for child in elem:
                    result += process_element(child)

            # Radical/root (m:rad)
            elif tag_name == 'rad':
                for child in elem:
                    result += process_element(child)

            # Math paragraph properties - skip
            elif tag_name in ('oMathPara', 'sPr', 'rPr', 'fPr', 'sSubPr', 'sSupPr', 'ctrlPr', 'rFonts', 'sz', 'szCs', 'nor'):
                return ""

            # Properties and formatting - skip
            elif tag_name.endswith('Pr') or tag_name in ('w:rPr', 'w:rFonts', 'w:sz', 'w:szCs'):
                return ""

            # Default: process all children
            else:
                for child in elem:
                    result += process_element(child)

            return result

        # Start processing from root
        text = process_element(omml).strip()
        return text

    except Exception as e:
        print(f"Warning: OMML text extraction failed: {e}")

    return ""


# Property/formatting elements that carry no visible math content — must be
# skipped entirely (not recursed into) or they generate empty <mrow/> noise
# and, for sSub/sSup, get misidentified as if they were actual base/script
# content (see the sSub bug this replaces).
_MATHML_SKIP_TAGS = {
    'rPr', 'rFonts', 'sz', 'szCs', 'i', 'b', 'sty', 'nor', 'ctrlPr',
    'sSubPr', 'sSupPr', 'sSubSupPr', 'fPr', 'radPr', 'oMathParaPr',
    'jc', 'proofErr',
}


def mathml_from_omml(omml_str: str) -> str:
    """
    Convert OMML (Office Math Markup Language) to MathML.
    Creates proper MathML structures for fractions, subscripts, superscripts, etc.
    """
    if not omml_str:
        return ""

    try:
        omml = etree.fromstring(omml_str.encode('utf-8'))

        def tag_name(elem):
            """Get local tag name without namespace."""
            return elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        def wrap_children(elem):
            """Wrap an element's non-property children in a single <mrow>."""
            mrow = etree.Element("mrow")
            for child in elem:
                if tag_name(child) in _MATHML_SKIP_TAGS:
                    continue
                node = omml_to_mml(child)
                if node is not None:
                    mrow.append(node)
            return mrow

        def omml_to_mml(elem):
            """Recursively convert an OMML element to a MathML element (or
            None for property/formatting elements that carry no content)."""
            tname = tag_name(elem)
            if tname in _MATHML_SKIP_TAGS:
                return None

            # Text element → mi (identifier) or mn (number)
            if tname == 't':
                text = elem.text or ""
                mml = etree.Element("mn" if re.fullmatch(r'[0-9]+(\.[0-9]+)?', text) else "mi")
                mml.text = text
                return mml

            # Pure grouping containers — oMath/oMathPara (root), r (run),
            # e (base/element wrapper), sub/sup (script content when reached
            # directly, e.g. via a bare m:sub outside sSub).
            if tname in ('oMath', 'oMathPara', 'r', 'e', 'sub', 'sup', 'base'):
                return wrap_children(elem)

            # Fraction (m:f: numerator/denominator)
            if tname == 'f':
                mml = etree.Element("mfrac")
                num_node = den_node = None
                for child in elem:
                    ctag = tag_name(child)
                    if ctag == 'num':
                        num_node = wrap_children(child)
                    elif ctag == 'den':
                        den_node = wrap_children(child)
                mml.append(num_node if num_node is not None else etree.Element("mrow"))
                mml.append(den_node if den_node is not None else etree.Element("mrow"))
                return mml

            # Subscript (m:sSub: base 'e' + subscript 'sub'). The 'sub' child
            # is a content container (like 'e'), not another sSub — must be
            # unwrapped with wrap_children directly, not re-dispatched.
            if tname == 'sSub':
                mml = etree.Element("msub")
                base = sub = None
                for child in elem:
                    ctag = tag_name(child)
                    if ctag == 'e':
                        base = wrap_children(child)
                    elif ctag == 'sub':
                        sub = wrap_children(child)
                mml.append(base if base is not None else etree.Element("mrow"))
                mml.append(sub if sub is not None else etree.Element("mrow"))
                return mml

            # Superscript (m:sSup: base 'e' + superscript 'sup'). Same note as sSub.
            if tname == 'sSup':
                mml = etree.Element("msup")
                base = sup = None
                for child in elem:
                    ctag = tag_name(child)
                    if ctag == 'e':
                        base = wrap_children(child)
                    elif ctag == 'sup':
                        sup = wrap_children(child)
                mml.append(base if base is not None else etree.Element("mrow"))
                mml.append(sup if sup is not None else etree.Element("mrow"))
                return mml

            # Combined sub+superscript (m:sSubSup: base 'e' + 'sub' + 'sup')
            if tname == 'sSubSup':
                mml = etree.Element("msubsup")
                base = sub = sup = None
                for child in elem:
                    ctag = tag_name(child)
                    if ctag == 'e':
                        base = wrap_children(child)
                    elif ctag == 'sub':
                        sub = wrap_children(child)
                    elif ctag == 'sup':
                        sup = wrap_children(child)
                mml.append(base if base is not None else etree.Element("mrow"))
                mml.append(sub if sub is not None else etree.Element("mrow"))
                mml.append(sup if sup is not None else etree.Element("mrow"))
                return mml

            # Radical / square root (m:rad: optional degree 'deg' + radicand 'e')
            if tname == 'rad':
                base = etree.Element("mrow")
                deg_node = None
                for child in elem:
                    ctag = tag_name(child)
                    if ctag == 'e':
                        base = wrap_children(child)
                    elif ctag == 'deg' and len(child):
                        deg_node = wrap_children(child)
                if deg_node is not None:
                    mml = etree.Element("mroot")
                    mml.append(base)
                    mml.append(deg_node)
                else:
                    mml = etree.Element("msqrt")
                    mml.append(base)
                return mml

            # Delimiter / bracket (m:d) — the visual bracket characters live
            # in dPr attributes rather than text; just group the enclosed content.
            if tname == 'd':
                return wrap_children(elem)

            # Default: group any unrecognised container's children
            return wrap_children(elem)

        mml_root = omml_to_mml(omml)
        if mml_root is None:
            return ""

        # Wrap in math element with proper namespace
        math = etree.Element("math", xmlns="http://www.w3.org/1998/Math/MathML")
        math.set("display", "block")
        math.append(mml_root)

        return etree.tostring(math, encoding="unicode", pretty_print=False)

    except Exception as e:
        print(f"Warning: OMML to MathML conversion failed: {e}")

    return ""


def mathml_from_latex(latex_str: str) -> str:
    """
    Convert LaTeX to MathML using latex2mathml library.
    """
    try:
        from latex2mathml.converter import convert
        mathml = convert(latex_str)
        return mathml
    except Exception as e:
        print(f"Warning: LaTeX to MathML conversion failed: {e}")

    return ""


def equation_to_latex(omml_str: str) -> str:
    """
    Convert OMML to LaTeX representation.
    This is a simplified converter - full conversion would be more complex.
    """
    if not omml_str:
        return ""

    # Extract text elements from OMML as LaTeX approximation
    equation_text = extract_equation_text(omml_str)

    # Basic LaTeX formatting (this would be much more complex for real usage)
    latex = equation_text.replace("²", "^2").replace("³", "^3").replace("√", "\\sqrt")

    return latex


def jats_equation_xml(eq_id: int, mathml: str = "", img_href: str = "", equation_text: str = "") -> str:
    """
    Generate JATS XML for a display equation with MathML and optional image.
    """
    mathml_elem = ""
    if mathml:
        # Include MathML inline
        mathml_elem = f"\n    {mathml}"

    img_elem = ""
    if img_href:
        img_elem = f'''
    <graphic href="{img_href}" mimetype="image" mime-subtype="png"/>'''

    text_elem = ""
    if equation_text and not mathml:
        text_elem = f'''
    <label-alt>{equation_text}</label-alt>'''

    return f'''<disp-formula id="E{eq_id}">{mathml_elem}{img_elem}{text_elem}
  </disp-formula>'''


def html_equation_element(mathml: str = "", img_data_uri: str = "", equation_text: str = "") -> str:
    """
    Generate HTML for an equation with MathML and MathJax fallback.
    """
    if mathml:
        # Use MathML with MathJax as fallback
        return f'''<div class="equation">
  {mathml}
  <script type="text/javascript">
    MathJax?.typesetPromise?.([document.currentScript.previousElementSibling]).catch(err => console.log(err));
  </script>
</div>'''
    elif img_data_uri:
        # Fallback to image
        alt_text = equation_text or "Equation"
        return f'<div class="equation"><img src="{img_data_uri}" alt="{alt_text}"/></div>'
    else:
        return f'<div class="equation"><p>{equation_text or "Equation"}</p></div>'
