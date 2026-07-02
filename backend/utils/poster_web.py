"""
Generate responsive HTML preview for posters.
Displays metadata (title, authors, affiliations, abstract) + poster image.
"""

import base64
from typing import Dict, Any


def generate_poster_html(poster: Dict[str, Any]) -> str:
    """
    Generate responsive HTML for poster display.

    Args:
        poster: Dict with keys:
            - title: str
            - authors: list of {"first_name": str, "last_name": str, "affiliation": str}
            - abstract: str
            - poster_image: str (base64 encoded image data or URL)

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
            authors_html += f'<div class="author">{name}'
            if affiliation:
                authors_html += f'<br><span class="affiliation">{affiliation}</span>'
            authors_html += '</div>'

    # Determine if image is base64 or URL
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
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}

        .metadata-section {{
            padding: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        .metadata-section h1 {{
            font-size: 2.5rem;
            margin-bottom: 20px;
            font-weight: 600;
            line-height: 1.3;
        }}

        .authors-container {{
            margin: 25px 0;
            border-top: 2px solid rgba(255, 255, 255, 0.3);
            padding-top: 20px;
        }}

        .author {{
            margin-bottom: 15px;
            font-size: 1.1rem;
        }}

        .affiliation {{
            font-size: 0.95rem;
            opacity: 0.9;
            font-style: italic;
        }}

        .abstract-section {{
            padding: 40px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
        }}

        .abstract-section h2 {{
            color: #333;
            font-size: 1.3rem;
            margin-bottom: 15px;
            font-weight: 600;
        }}

        .abstract-section p {{
            color: #555;
            font-size: 1rem;
            line-height: 1.8;
            text-align: justify;
        }}

        .poster-section {{
            padding: 40px;
            display: flex;
            justify-content: center;
            align-items: center;
            background: white;
            border-top: 1px solid #e0e0e0;
        }}

        .poster-image {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
        }}

        @media (max-width: 768px) {{
            .metadata-section {{
                padding: 25px;
            }}

            .metadata-section h1 {{
                font-size: 1.8rem;
            }}

            .author {{
                font-size: 1rem;
            }}

            .abstract-section,
            .poster-section {{
                padding: 25px;
            }}

            .abstract-section h2 {{
                font-size: 1.1rem;
            }}

            .abstract-section p {{
                font-size: 0.95rem;
            }}
        }}

        .footer {{
            padding: 20px 40px;
            background: #f0f0f0;
            text-align: center;
            color: #666;
            font-size: 0.9rem;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Metadata Section -->
        <div class="metadata-section">
            <h1>{title}</h1>
            <div class="authors-container">
                {authors_html}
            </div>
        </div>

        <!-- Abstract Section -->
        {f'<div class="abstract-section"><h2>Abstract</h2><p>{abstract}</p></div>' if abstract else ''}

        <!-- Poster Section -->
        <div class="poster-section">
            {image_tag}
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>Generated with Novel Future Publishing</p>
        </div>
    </div>
</body>
</html>
"""

    return html
