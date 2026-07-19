"""
Convert LaTeX math expressions to MathML for proper equation rendering.
Supports standard LaTeX notation used in DOCX documents.
"""
import re


def detect_latex_formulas(text: str) -> list:
    """
    Detect LaTeX formulas in text.
    Supports:
    - Display mode: $$ ... $$
    - Inline mode: $ ... $ or \( ... \)

    Returns list of (start_idx, end_idx, formula_text, is_display)
    """
    formulas = []

    # Display mode: $$ ... $$
    for match in re.finditer(r'\$\$(.*?)\$\$', text, re.DOTALL):
        formulas.append((match.start(), match.end(), match.group(1).strip(), True))

    # Inline mode: \( ... \)
    for match in re.finditer(r'\\\((.*?)\\\)', text, re.DOTALL):
        formulas.append((match.start(), match.end(), match.group(1).strip(), False))

    # Inline mode: $ ... $ (but not $$)
    for match in re.finditer(r'(?<!\$)\$([^\$]+)\$(?!\$)', text):
        formulas.append((match.start(), match.end(), match.group(1).strip(), False))

    return sorted(formulas, key=lambda x: x[0])


def latex_to_mathml(latex_str: str, display: bool = True) -> str:
    """
    Convert simple LaTeX to MathML.

    Supports:
    - Fractions: \frac{a}{b}
    - Subscripts: x_i, x_{ij}
    - Superscripts: x^2, x^{n+1}
    - Greek letters: \alpha, \beta, etc.
    - Text mode: \text{...}
    - Basic operators: =, +, -, \times, \div, etc.

    Returns MathML string.
    """
    latex = latex_str.strip()

    # Convert LaTeX to MathML using simple substitution rules
    # This is a basic converter; for complex formulas, use mathjax-node or similar

    mathml = f'<math xmlns="http://www.w3.org/1998/Math/MathML" display="{"block" if display else "inline"}">'
    mathml += '<mrow>'

    # Process the LaTeX formula
    mathml += _parse_latex(latex)

    mathml += '</mrow></math>'
    return mathml


def _parse_latex(latex: str) -> str:
    """Recursively parse LaTeX and generate MathML."""
    result = ""
    i = 0

    while i < len(latex):
        # Whitespace
        if latex[i].isspace():
            i += 1
            continue

        # Backslash command (e.g., \frac, \alpha, \text)
        if latex[i] == '\\':
            i, mml = _parse_command(latex, i)
            result += mml
            continue

        # Curly braces (grouping)
        if latex[i] == '{':
            i, group = _extract_braced(latex, i)
            result += _parse_latex(group)
            continue

        # Superscript/Subscript
        if latex[i] in ('^', '_'):
            operator = latex[i]
            i += 1
            # Get the next token (single char or {...})
            if i < len(latex):
                if latex[i] == '{':
                    i, content = _extract_braced(latex, i)
                    content_mml = _parse_latex(content)
                else:
                    content_mml = _char_to_mml(latex[i])
                    i += 1

                # Wrap previous result or create new element
                if operator == '^':
                    result = f'<msup><mrow>{result}</mrow><mrow>{content_mml}</mrow></msup>'
                else:  # '_'
                    result = f'<msub><mrow>{result}</mrow><mrow>{content_mml}</mrow></msub>'
            continue

        # Regular character
        result += _char_to_mml(latex[i])
        i += 1

    return result


def _parse_command(latex: str, start: int) -> tuple:
    """Parse a LaTeX command starting with backslash. Returns (new_index, mathml)."""
    i = start + 1

    # Extract command name
    cmd_start = i
    while i < len(latex) and latex[i].isalpha():
        i += 1
    command = latex[cmd_start:i]

    # Skip whitespace after command
    while i < len(latex) and latex[i].isspace():
        i += 1

    # Handle specific commands
    if command == 'frac':
        # \frac{numerator}{denominator}
        if i < len(latex) and latex[i] == '{':
            i, num = _extract_braced(latex, i)
            if i < len(latex) and latex[i] == '{':
                i, den = _extract_braced(latex, i)
                return i, f'<mfrac><mrow>{_parse_latex(num)}</mrow><mrow>{_parse_latex(den)}</mrow></mfrac>'

    elif command == 'text':
        # \text{...}
        if i < len(latex) and latex[i] == '{':
            i, text = _extract_braced(latex, i)
            return i, f'<mtext>{_escape_xml(text)}</mtext>'

    elif command == 'times':
        return i, '<mo>×</mo>'
    elif command == 'div':
        return i, '<mo>÷</mo>'
    elif command == 'pm':
        return i, '<mo>±</mo>'
    elif command == 'sqrt':
        # \sqrt{...} or \sqrt[n]{...}
        root = None
        if i < len(latex) and latex[i] == '[':
            i += 1
            bracket_end = latex.find(']', i)
            if bracket_end != -1:
                root = latex[i:bracket_end]
                i = bracket_end + 1

        if i < len(latex) and latex[i] == '{':
            i, content = _extract_braced(latex, i)
            if root:
                return i, f'<mroot><mrow>{_parse_latex(content)}</mrow><mrow>{_parse_latex(root)}</mrow></mroot>'
            else:
                return i, f'<msqrt><mrow>{_parse_latex(content)}</mrow></msqrt>'

    # Greek letters and special symbols
    greek_map = {
        'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ',
        'epsilon': 'ε', 'zeta': 'ζ', 'eta': 'η', 'theta': 'θ',
        'iota': 'ι', 'kappa': 'κ', 'lambda': 'λ', 'mu': 'μ',
        'nu': 'ν', 'xi': 'ξ', 'omicron': 'ο', 'pi': 'π',
        'rho': 'ρ', 'sigma': 'σ', 'tau': 'τ', 'upsilon': 'υ',
        'phi': 'φ', 'chi': 'χ', 'psi': 'ψ', 'omega': 'ω',
        'Gamma': 'Γ', 'Delta': 'Δ', 'Theta': 'Θ', 'Lambda': 'Λ',
        'Xi': 'Ξ', 'Pi': 'Π', 'Sigma': 'Σ', 'Upsilon': 'Υ',
        'Phi': 'Φ', 'Psi': 'Ψ', 'Omega': 'Ω',
        'infty': '∞', 'sum': '∑', 'prod': '∏', 'int': '∫',
        'leq': '≤', 'geq': '≥', 'neq': '≠', 'approx': '≈',
    }

    if command in greek_map:
        return i, f'<mi>{greek_map[command]}</mi>'

    # Unknown command, return as-is
    return i, f'<mi>\\{command}</mi>'


def _extract_braced(latex: str, start: int) -> tuple:
    """Extract content between braces. Returns (end_index, content)."""
    if start >= len(latex) or latex[start] != '{':
        return start, ""

    i = start + 1
    depth = 1
    while i < len(latex) and depth > 0:
        if latex[i] == '{':
            depth += 1
        elif latex[i] == '}':
            depth -= 1
        i += 1

    return i, latex[start+1:i-1]


def _char_to_mml(char: str) -> str:
    """Convert a single character to MathML."""
    if char in '0123456789':
        return f'<mn>{char}</mn>'
    elif char in '()[]':
        return f'<mo>{char}</mo>'
    elif char in '=+-':
        return f'<mo>{char}</mo>'
    elif char.isalpha():
        return f'<mi>{char}</mi>'
    else:
        return f'<mo>{char}</mo>'


def _escape_xml(text: str) -> str:
    """Escape XML special characters."""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&apos;')
    return text
