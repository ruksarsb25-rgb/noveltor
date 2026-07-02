"""
Generate HTML documents for posters.
Multi-page HTML with metadata and poster image.
"""

import base64
from typing import Dict, Any


def generate_poster_html_document(poster: Dict[str, Any]) -> str:
    """
    Generate multi-page HTML document for poster (for saving as HTML file).

    Args:
        poster: Dict with poster data

    Returns:
        HTML string
    """
    title = poster.get("title", "Untitled Poster")
    authors = poster.get("authors", [])
    abstract = poster.get("abstract", "")
    poster_image = poster.get("poster_image", "")

    # Build author list with affiliations
    authors_html = ""
    for author in authors:
        first_name = author.get("first_name", "")
        last_name = author.get("last_name", "")
        affiliation = author.get("affiliation", "")

        name = f"{first_name} {last_name}".strip()
        if name:
            authors_html += f"<h3>{name}</h3>"
            if affiliation:
                authors_html += f'<p class="affiliation">{affiliation}</p>'

    # Prepare image tag
    if poster_image.startswith("data:"):
        image_tag = f'<img src="{poster_image}" alt="Poster" class="poster-image">'
    elif poster_image.startswith("http"):
        image_tag = f'<img src="{poster_image}" alt="Poster" class="poster-image">'
    else:
        # Assume it's base64 encoded
        image_tag = f'<img src="data:image/png;base64,{poster_image}" alt="Poster" class="poster-image">'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: Georgia, 'Times New Roman', serif;
            line-height: 1.6;
            color: #333;
            background: white;
        }}

        .page {{
            page-break-after: always;
            padding: 40px;
            min-height: 100vh;
        }}

        .page:last-child {{
            page-break-after: avoid;
        }}

        /* Metadata Page */
        .metadata-page {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            text-align: center;
        }}

        .metadata-page h1 {{
            font-size: 2.5em;
            margin-bottom: 30px;
            color: #2c3e50;
            font-weight: 700;
        }}

        .metadata-page h3 {{
            font-size: 1.2em;
            margin-top: 20px;
            color: #34495e;
            font-weight: 600;
        }}

        .affiliation {{
            font-size: 0.95em;
            font-style: italic;
            color: #555;
            margin: 5px 0;
        }}

        .abstract-section {{
            margin-top: 40px;
            text-align: justify;
        }}

        .abstract-section h2 {{
            font-size: 1.3em;
            margin-bottom: 15px;
            color: #2c3e50;
            text-align: center;
        }}

        .abstract-section p {{
            font-size: 1em;
            line-height: 1.8;
        }}

        /* Poster Page */
        .poster-page {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .poster-image {{
            max-width: 100%;
            height: auto;
        }}

        @media print {{
            body {{
                background: white;
            }}

            .page {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <!-- Page 1: Metadata -->
    <div class="page metadata-page">
        <h1>{title}</h1>
        <div class="authors-section">
            {authors_html}
        </div>
        {f'<div class="abstract-section"><h2>Abstract</h2><p>{abstract}</p></div>' if abstract else ''}
    </div>

    <!-- Page 2: Poster Image -->
    <div class="page poster-page">
        {image_tag}
    </div>
</body>
</html>
"""

    return html
