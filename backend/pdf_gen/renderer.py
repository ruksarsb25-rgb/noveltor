from weasyprint import HTML


def render_pdf(html_string: str) -> bytes:
    return HTML(string=html_string, base_url=None).write_pdf()
