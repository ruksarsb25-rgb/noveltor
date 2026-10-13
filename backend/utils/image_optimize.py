"""
Shrink figure and logo images before an export is generated.

Exports used to embed every image at exactly the resolution it was pasted
into the Word file. A journal-cover logo that's printed 1.4 cm wide is
typically a 1500x2000 px picture (~2.5 MB of flate-compressed RGB), and
photographic figures (SEM/TEM micrographs, plates) were stored as lossless
PNG — so a plain article routinely landed at 5-8 MB. Google Scholar's
crawler skips PDFs above ~5 MB, so size is a correctness problem for the
export, not just a nicety.

This does the shrinking once, on the article JSON, so every exporter
(JATS XML package, web ZIP, HTML, WeasyPrint PDF, LaTeX PDF) sees the same
smaller images and — because the data URI's mime type is rewritten here, not
inside each exporter — filenames/extensions derived from it stay consistent
between the XML hrefs and the files actually written into the package.
"""

import base64
import io
from typing import Any, Dict, Tuple

# A4 text width is ~6.3 in, so 1800 px is ~285 ppi even for a full-width
# figure — past the point where print quality visibly improves.
FIGURE_MAX_PX = 1800
# Logos are drawn at 1.4 cm (LaTeX) / 46 pt (WeasyPrint) / 40 px (web);
# 512 px is several times oversampled at every one of those sizes.
LOGO_MAX_PX = 512
JPEG_QUALITY = 85

# Unique colours in a nearest-neighbour sample. Charts, schemes and
# line art sit well under this; photographs are far over it. Only
# photographic images are worth the lossy JPEG round trip — it would
# visibly smear the sharp text and thin lines in a chart.
_PHOTO_COLOR_THRESHOLD = 4000
_SAMPLE_SIDE = 256
# JPEG must come out at least this many times smaller than the PNG.
_JPEG_MIN_GAIN = 1.8

_LOGO_KEYS = ("journal_logo", "brand_logo")


def _is_photographic(img) -> bool:
    from PIL import Image
    w, h = img.size
    scale = max(w, h) / _SAMPLE_SIDE
    if scale > 1:
        sample = img.resize(
            (max(1, int(w / scale)), max(1, int(h / scale))), Image.NEAREST
        )
    else:
        sample = img
    colors = sample.convert("RGB").getcolors(maxcolors=_SAMPLE_SIDE * _SAMPLE_SIDE)
    return colors is None or len(colors) > _PHOTO_COLOR_THRESHOLD


def _reencode(raw: bytes, max_px: int, jpeg_quality: int) -> Tuple[bytes, str]:
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(raw))
    img.load()
    img = ImageOps.exif_transpose(img)

    has_alpha = img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info
    )
    if has_alpha:
        img = img.convert("RGBA")
        # An alpha channel that is fully opaque (very common for pasted
        # PNGs) buys nothing but a PDF soft-mask object per image.
        if img.getchannel("A").getextrema()[0] == 255:
            img = img.convert("RGB")
            has_alpha = False
    elif img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    if max(img.size) > max_px:
        img.thumbnail((max_px, max_px), Image.LANCZOS)

    png = io.BytesIO()
    png_img = img
    if img.mode == "RGB" and img.getcolors(maxcolors=256) is not None:
        # <=256 distinct colours: a palette is a lossless 3x saving.
        png_img = img.convert("P", palette=Image.ADAPTIVE, colors=256)
    png_img.save(png, format="PNG", optimize=True)

    if not has_alpha and _is_photographic(img):
        jpg = io.BytesIO()
        img.convert("RGB").save(jpg, format="JPEG", quality=jpeg_quality, optimize=True)
        # Lossy only when it pays for itself. A chart that merely has
        # anti-aliased/blurred edges can pass the colour-count test, but
        # its lossless PNG is already close in size — keep that one
        # pixel-exact rather than risk ringing around axis text.
        if len(jpg.getvalue()) * _JPEG_MIN_GAIN < len(png.getvalue()):
            return jpg.getvalue(), "image/jpeg"
    return png.getvalue(), "image/png"


def optimize_data_uri(data_uri: str, max_px: int = FIGURE_MAX_PX,
                      jpeg_quality: int = JPEG_QUALITY) -> str:
    """Return a smaller equivalent data URI, or the original unchanged if
    it can't be decoded, isn't a PNG/JPEG, or wouldn't get smaller."""
    if not data_uri or not data_uri.startswith("data:image/") or "," not in data_uri:
        return data_uri
    header, b64 = data_uri.split(",", 1)
    mime = header[5:].split(";")[0].lower()
    if mime not in ("image/png", "image/jpeg", "image/jpg") or ";base64" not in header:
        return data_uri
    try:
        raw = base64.b64decode(b64)
        out, out_mime = _reencode(raw, max_px, jpeg_quality)
    except Exception:
        return data_uri
    if len(out) >= len(raw):
        return data_uri
    return f"data:{out_mime};base64,{base64.b64encode(out).decode()}"


def _walk_figures(sections):
    for sec in sections or []:
        for block in sec.get("content", []) or []:
            if block.get("type") == "figure":
                yield block
        yield from _walk_figures(sec.get("subsections"))


def optimize_article_images(article: Dict[str, Any]) -> Dict[str, int]:
    """Shrink every figure image and the journal/brand logos in place.
    Equation images are left alone (small, and text-like). Returns
    {"before": bytes, "after": bytes} of base64 payload, for logging."""
    before = after = 0

    def _shrink(holder: Dict[str, Any], key: str, max_px: int):
        nonlocal before, after
        uri = holder.get(key) or ""
        if not uri:
            return
        new = optimize_data_uri(uri, max_px=max_px)
        before += len(uri)
        after += len(new)
        holder[key] = new

    for block in _walk_figures(article.get("sections")):
        _shrink(block, "data_uri", FIGURE_MAX_PX)
    for key in _LOGO_KEYS:
        _shrink(article, key, LOGO_MAX_PX)

    if before:
        print(f"[IMAGE] export images {before / 1e6:.2f} MB -> {after / 1e6:.2f} MB (base64)")
    return {"before": before, "after": after}
