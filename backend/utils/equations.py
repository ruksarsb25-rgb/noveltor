"""
Equation utilities for converting between formats (OMML, LaTeX, MathML).
Supports multiple export formats: Word, XML/JATS, HTML, PDF.
"""
import re
from lxml import etree

def mathml_from_omml(omml_str: str) -> str:
    """
    Convert OMML (Office Math Markup Language) to MathML.
    Returns basic MathML or empty string if conversion fails.
    """
    if not omml_str:
        return ""

    try:
        # Parse OMML
        omml = etree.fromstring(omml_str.encode('utf-8'))

        # Extract text elements to build equation representation
        text_elements = omml.xpath('.//*[local-name()="t"]')
        equation_text = "".join([t.text or "" for t in text_elements]).strip()

        if equation_text:
            # Create proper MathML with actual equation content
            # Escape special XML characters
            safe_text = equation_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            mathml = f'''<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">
  <mrow>
    <mtext>{safe_text}</mtext>
  </mrow>
</math>'''
            return mathml
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


def extract_equation_text(omml_str: str) -> str:
    """
    Extract text representation from OMML, preserving subscripts/superscripts.
    Converts subscripts to Unicode characters (₀₁₂₃₄₅₆₇₈₉) for readability.
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

        def get_tag_name(element):
            """Extract local tag name from namespaced tag."""
            tag = element.tag
            return tag.split('}')[-1] if '}' in tag else tag

        def iter_text_with_format(element):
            """Iteratively extract text, preserving subscripts/superscripts."""
            # Use a stack for iterative processing to avoid recursion issues
            stack = [(element, False)]  # (element, is_processed)
            result_stack = []

            while stack:
                elem, is_processed = stack.pop()
                tag_name = get_tag_name(elem)

                if is_processed:
                    # Second pass: we've processed children, now handle this element
                    if tag_name == 'sub':
                        # Convert to subscript
                        text = result_stack.pop() if result_stack else ""
                        result_stack.append(''.join(subscript_map.get(c, c) for c in text))
                    elif tag_name == 'sup':
                        # Convert to superscript
                        text = result_stack.pop() if result_stack else ""
                        result_stack.append(''.join(superscript_map.get(c, c) for c in text))
                    elif tag_name == 't':
                        # Text element
                        result_stack.append(elem.text or "")
                    else:
                        # Accumulate text from children
                        pass
                else:
                    # First pass: mark for processing and add children to stack
                    stack.append((elem, True))
                    # Add children in reverse order (for stack processing)
                    for child in reversed(list(elem)):
                        stack.append((child, False))

            return "".join(result_stack).strip()

        # Process elements in order, tracking what we've handled
        result = ""
        processed_t_elements = set()

        for elem in omml.iter():
            tag_name = get_tag_name(elem)

            if tag_name == 'sub':
                # Get text in subscript element
                sub_text_elems = elem.xpath('.//*[local-name()="t"]')
                for t_elem in sub_text_elems:
                    if id(t_elem) not in processed_t_elements:
                        sub_text = t_elem.text or ""
                        result += ''.join(subscript_map.get(c, c) for c in sub_text)
                        processed_t_elements.add(id(t_elem))

            elif tag_name == 'sup':
                # Get text in superscript element
                sup_text_elems = elem.xpath('.//*[local-name()="t"]')
                for t_elem in sup_text_elems:
                    if id(t_elem) not in processed_t_elements:
                        sup_text = t_elem.text or ""
                        result += ''.join(superscript_map.get(c, c) for c in sup_text)
                        processed_t_elements.add(id(t_elem))

            elif tag_name == 't':
                # Regular text - only process if not part of sub/sup
                if id(elem) not in processed_t_elements:
                    parent_tag = get_tag_name(elem.getparent()) if elem.getparent() is not None else None
                    if parent_tag not in ('sub', 'sup'):
                        result += elem.text or ""
                        processed_t_elements.add(id(elem))

        return result.strip()
    except Exception as e:
        print(f"Warning: OMML text extraction failed: {e}")

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
