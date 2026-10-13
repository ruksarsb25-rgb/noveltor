from weasyprint import HTML


def render_pdf(html_string: str) -> bytes:
    # optimize_images re-encodes each embedded image with the smallest
    # lossless settings available (Google Scholar skips PDFs over ~5 MB).
    return HTML(string=html_string, base_url=None).write_pdf(optimize_images=True)
