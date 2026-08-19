"""
Equation utilities for converting between formats (OMML, LaTeX, MathML).
Supports multiple export formats: Word, XML/JATS, HTML, PDF.
"""
import re
import unicodedata
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


# OMML property/formatting elements that carry no visible math content —
# shared by both the MathML and LaTeX converters below. Must be skipped
# entirely (not recursed into) or they generate empty <mrow/> noise and,
# for sSub/sSup, get misidentified as if they were actual base/script
# content (see the sSub bug this replaces).
_OMML_PROPERTY_TAGS = {
    'rPr', 'rFonts', 'sz', 'szCs', 'i', 'b', 'sty', 'nor', 'ctrlPr',
    'sSubPr', 'sSupPr', 'sSubSupPr', 'fPr', 'radPr', 'dPr', 'oMathParaPr',
    'jc', 'proofErr',
}

_FENCE_CHARS = set('()[]{}')


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
                if tag_name(child) in _OMML_PROPERTY_TAGS:
                    continue
                node = omml_to_mml(child)
                if node is not None:
                    mrow.append(node)
            return mrow

        def omml_to_mml(elem):
            """Recursively convert an OMML element to a MathML element (or
            None for property/formatting elements that carry no content)."""
            tname = tag_name(elem)
            if tname in _OMML_PROPERTY_TAGS:
                return None

            # Text element → mi (identifier) or mn (number)
            if tname == 't':
                text = elem.text or ""
                if any(c in _FENCE_CHARS for c in text):
                    # Bracket characters mixed into a multi-char identifier run
                    # (e.g. "Degradation Efficiency (%)") — split them out as
                    # their own <mo> operator elements rather than leaving them
                    # inside <mi> text. Some MathML renderers mishandle fence
                    # punctuation left inside an identifier token.
                    mrow = etree.Element("mrow")
                    for piece in re.split(r'([()\[\]{}])', text):
                        if not piece:
                            continue
                        if piece in _FENCE_CHARS:
                            node = etree.Element("mo")
                        else:
                            node = etree.Element("mn" if re.fullmatch(r'[0-9]+(\.[0-9]+)?', piece) else "mi")
                        node.text = piece
                        mrow.append(node)
                    return mrow
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


# Unicode symbols (Greek letters, operators, relations) mapped to their
# standard LaTeX macros. Applied to non-prose OMML text runs so the emitted
# .tex source is plain ASCII — pdflatex has no inputenc/fontenc setup, so a
# literal "β" byte sequence in the source would fail to compile or render
# wrong; "\beta" is what a human LaTeX author would actually type.
_LATEX_SYMBOL_MAP = {
    # Greek lowercase (+ micro sign, commonly used interchangeably with mu)
    'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'δ': r'\delta',
    'ε': r'\epsilon', 'ζ': r'\zeta', 'η': r'\eta', 'θ': r'\theta',
    'ι': r'\iota', 'κ': r'\kappa', 'λ': r'\lambda', 'μ': r'\mu', 'µ': r'\mu',
    'ν': r'\nu', 'ξ': r'\xi', 'π': r'\pi', 'ρ': r'\rho', 'ς': r'\varsigma',
    'σ': r'\sigma', 'τ': r'\tau', 'υ': r'\upsilon', 'φ': r'\phi',
    'χ': r'\chi', 'ψ': r'\psi', 'ω': r'\omega',
    # Greek uppercase (only the glyphs that differ from Latin letters)
    'Γ': r'\Gamma', 'Δ': r'\Delta', 'Θ': r'\Theta', 'Λ': r'\Lambda',
    'Ξ': r'\Xi', 'Π': r'\Pi', 'Σ': r'\Sigma', 'Υ': r'\Upsilon',
    'Φ': r'\Phi', 'Ψ': r'\Psi', 'Ω': r'\Omega',
    # Operators / relations
    '×': r'\times', '÷': r'\div', '±': r'\pm', '∓': r'\mp',
    '≤': r'\leq', '≥': r'\geq', '≠': r'\neq', '≈': r'\approx',
    '≡': r'\equiv', '∝': r'\propto', '∞': r'\infty', '·': r'\cdot',
    '→': r'\rightarrow', '←': r'\leftarrow', '↔': r'\leftrightarrow',
    '⇒': r'\Rightarrow', '⇌': r'\rightleftharpoons',
    '∑': r'\sum', '∏': r'\prod', '∫': r'\int', '∂': r'\partial',
    '∇': r'\nabla', '√': r'\sqrt', '∈': r'\in', '∉': r'\notin',
    '∀': r'\forall', '∃': r'\exists', '∅': r'\emptyset', '°': r'^\circ',
    '•': r'\bullet',  # e.g. •OH — a radical species dot, common in chemistry
    # OMML's invisible layout operators — no LaTeX equivalent, just drop them
    '⁡': '', '⁢': '', '⁣': '', '⁤': '',
}

# Standard LaTeX "log-like" math operators (upright, correctly spaced) — a
# bare OMML text run matching one of these exactly becomes \cos, \sin, etc.
# instead of being left to render as italicized single letters.
_LATEX_FUNC_NAMES = {
    'cos', 'sin', 'tan', 'cot', 'sec', 'csc', 'log', 'ln', 'exp', 'lim',
    'max', 'min', 'sup', 'inf', 'det', 'gcd', 'arg',
    'cosh', 'sinh', 'tanh', 'coth',
}

# A run of 2+ Latin letters reads as a word/label (e.g. "Degradation
# Efficiency", "Where") rather than a math variable — checked BEFORE any
# symbol substitution, since substituted macros (e.g. "\beta") also contain
# letter runs and would otherwise be misdetected as prose.
_LATEX_WORD_RE = re.compile(r'[A-Za-z]{2,}')


def _normalize_math_alphanumerics(text: str) -> str:
    """
    Word's equation editor sometimes stores italicized math variables using
    Unicode "Mathematical Alphanumeric Symbols" codepoints (e.g. U+1D458
    MATHEMATICAL ITALIC SMALL K, "𝑘") instead of plain ASCII — the italic
    styling is baked into the character itself. LaTeX math mode already
    italicizes plain letters automatically, and pdflatex has no glyph for
    this Unicode block at all, so normalize back to plain ASCII (NFKD
    compatibility decomposition maps these to their base Latin letter).
    """
    out = []
    for ch in text:
        if 0x1D400 <= ord(ch) <= 0x1D7FF:
            decomposed = unicodedata.normalize('NFKD', ch)
            out.append(decomposed[0] if decomposed else ch)
        else:
            out.append(ch)
    return ''.join(out)


def _latex_symbols(text: str) -> str:
    """Apply the Unicode→LaTeX macro table character by character."""
    text = _normalize_math_alphanumerics(text)
    return ''.join(_LATEX_SYMBOL_MAP.get(c, c) for c in text)


def _latex_escape_text(text: str) -> str:
    """Escape LaTeX-special characters for use inside \\text{...}."""
    text = text.replace('\xa0', ' ')  # non-breaking space → plain ASCII space
    text = text.replace('\\', r'\textbackslash{}')  # must come first
    for ch, esc in (
        ('&', r'\&'), ('%', r'\%'), ('$', r'\$'), ('#', r'\#'),
        ('_', r'\_'), ('{', r'\{'), ('}', r'\}'),
        ('~', r'\textasciitilde{}'), ('^', r'\textasciicircum{}'),
    ):
        text = text.replace(ch, esc)
    return text


_LATEX_FUNC_NAMES_BY_LEN = sorted(_LATEX_FUNC_NAMES, key=len, reverse=True)


def _convert_mixed_math_text(raw: str) -> str:
    """Convert a single OMML text run that mixes Greek letters/operators
    with a known function name and no spaces — e.g. "βcosθ" (a very common
    compact physics notation: FWHM(β) times cos(theta), typed as one run)
    — into valid LaTeX math-mode tokens.

    This exists because the caller's "is this a prose label?" check keys
    off finding 2+ consecutive Latin letters, which "cos" inside "βcosθ"
    satisfies — but the run isn't prose, it's still math. Wrapping it in
    \\text{} as if it were leaves the raw, un-mapped β/θ characters sitting
    inside a text-mode argument, which pdflatex can't compile without full
    Unicode math support ("Unicode character β (U+03B2) not set up for use
    with LaTeX"). Blindly mapping β→\\beta and splicing it directly next to
    "cos" isn't safe either — adjacent control-word macros with no
    separator merge into one undefined macro name ("\\betacos"), the exact
    failure mode join_children()'s space-joining already guards against
    for separate elements — so each token gets a trailing space here too.
    """
    out = []
    i, n = 0, len(raw)
    while i < n:
        ch = raw[i]
        if ch in _LATEX_SYMBOL_MAP:
            out.append(_LATEX_SYMBOL_MAP[ch] + ' ')
            i += 1
            continue
        matched = next((f for f in _LATEX_FUNC_NAMES_BY_LEN if raw.startswith(f, i)), None)
        if matched:
            out.append('\\' + matched + ' ')
            i += len(matched)
            continue
        out.append(ch)  # plain Latin letter/digit/punctuation — safe as-is in math mode
        i += 1
    return ''.join(out).strip()


def omml_to_latex(omml_str: str) -> str:
    """
    Convert OMML (Office Math Markup Language) to a LaTeX math expression
    (no surrounding $ / \\[ \\] — the caller wraps it in a math environment).

    Walks the same OMML tree as mathml_from_omml, emitting LaTeX macros
    instead of MathML elements: m:f → \\frac{num}{den}, m:sSub → base_{sub},
    m:sSup → base^{sup}, m:rad → \\sqrt{...}, Greek letters/operators →
    their LaTeX macros. This works from the structured tree rather than the
    flattened Unicode text extraction, so fractions and scripts survive
    intact instead of collapsing to a bare "/" or plain digit.
    """
    if not omml_str:
        return ""

    try:
        omml = etree.fromstring(omml_str.encode('utf-8'))

        def tag_name(elem):
            return elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        def join_children(elem):
            """Convert an element's non-property children and join with a
            space — the space is invisible in rendered math-mode spacing,
            but prevents adjacent control-word macros from merging into an
            undefined one (e.g. "\\theta" + "x" must not become "\\thetax")."""
            parts = []
            for child in elem:
                if tag_name(child) in _OMML_PROPERTY_TAGS:
                    continue
                piece = convert(child)
                if piece:
                    parts.append(piece)
            return ' '.join(parts)

        def convert(elem):
            tname = tag_name(elem)
            if tname in _OMML_PROPERTY_TAGS:
                return ""

            if tname == 't':
                raw = elem.text or ""
                if not raw:
                    return ""
                stripped = raw.strip()
                if stripped in _LATEX_FUNC_NAMES:
                    return raw.replace(stripped, '\\' + stripped, 1)
                if _LATEX_WORD_RE.search(raw):
                    if any(c in _LATEX_SYMBOL_MAP for c in raw):
                        # Not prose — a compact notation mixing Greek/
                        # operator characters with a function name and no
                        # spaces (e.g. "βcosθ"). Wrapping the whole thing
                        # in \text{} would leave the raw, un-mapped Greek
                        # character sitting inside a text-mode argument,
                        # which pdflatex can't compile without full
                        # Unicode math support.
                        return _convert_mixed_math_text(raw)
                    # Genuine prose label — render upright via \text{} so
                    # LaTeX doesn't italicize/space it like a run of
                    # variables.
                    return r'\text{' + _latex_escape_text(raw) + '}'
                # A math symbol, digit, or operator — safe to leave in math
                # mode directly once Unicode symbols are mapped to macros.
                return _latex_symbols(raw)

            if tname in ('oMath', 'oMathPara', 'r', 'e', 'sub', 'sup', 'base'):
                return join_children(elem)

            if tname == 'f':
                num = den = ""
                for child in elem:
                    ctag = tag_name(child)
                    if ctag == 'num':
                        num = join_children(child)
                    elif ctag == 'den':
                        den = join_children(child)
                return f'\\frac{{{num}}}{{{den}}}'

            if tname == 'sSub':
                base = sub = ""
                for child in elem:
                    ctag = tag_name(child)
                    if ctag == 'e':
                        base = join_children(child)
                    elif ctag == 'sub':
                        sub = join_children(child)
                return f'{base}_{{{sub}}}'

            if tname == 'sSup':
                base = sup = ""
                for child in elem:
                    ctag = tag_name(child)
                    if ctag == 'e':
                        base = join_children(child)
                    elif ctag == 'sup':
                        sup = join_children(child)
                return f'{base}^{{{sup}}}'

            if tname == 'sSubSup':
                base = sub = sup = ""
                for child in elem:
                    ctag = tag_name(child)
                    if ctag == 'e':
                        base = join_children(child)
                    elif ctag == 'sub':
                        sub = join_children(child)
                    elif ctag == 'sup':
                        sup = join_children(child)
                return f'{base}_{{{sub}}}^{{{sup}}}'

            if tname == 'rad':
                base = ""
                deg = None
                for child in elem:
                    ctag = tag_name(child)
                    if ctag == 'e':
                        base = join_children(child)
                    elif ctag == 'deg' and len(child):
                        deg = join_children(child)
                return f'\\sqrt[{deg}]{{{base}}}' if deg else f'\\sqrt{{{base}}}'

            if tname == 'd':
                # Delimiter chars (begChr/endChr) live in dPr attributes, not
                # text; assuming plain parentheses covers the common case.
                # \left/\right auto-size to the enclosed content's height.
                return f'\\left({join_children(elem)}\\right)'

            # Default: join any unrecognised container's children
            return join_children(elem)

        return convert(omml).strip()

    except Exception as e:
        print(f"Warning: OMML to LaTeX conversion failed: {e}")

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
