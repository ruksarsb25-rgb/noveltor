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
    references = poster.get("references", [])
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

    # For web preview, only include image if it's reasonably sized
    # Large base64 images (>10MB) won't render well in browsers
    image_tag = ""
    if poster_image:
        image_size_mb = len(poster_image) / (1024 * 1024)
        if image_size_mb > 50:
            # Image too large for web preview, show placeholder
            image_tag = f'<div class="poster-placeholder"><p>Poster Image ({image_size_mb:.1f} MB)</p><p style="font-size: 0.9em; color: #999;">Image too large for web preview. Download Word, PDF, or HTML for full image.</p></div>'
        else:
            # Include smaller images
            if poster_image.startswith("data:"):
                image_tag = f'<img src="{poster_image}" alt="Poster" class="poster-image">'
            elif poster_image.startswith("http"):
                image_tag = f'<img src="{poster_image}" alt="Poster" class="poster-image">'
            else:
                # Base64 encoded
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

        .poster-placeholder {{
            padding: 60px 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
            border: 2px dashed #999;
            border-radius: 8px;
            text-align: center;
            color: #666;
        }}

        .poster-placeholder p {{
            margin: 10px 0;
            font-size: 1.1em;
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

        {f'''<!-- References Section -->
        <div class="poster-section" style="background: #f8f9fa; border-top: 1px solid #e0e0e0;">
            <div style="width: 100%; text-align: left;">
                <h2 style="color: #333; font-size: 1.3rem; margin-bottom: 15px; font-weight: 600;">References</h2>
                <ol style="color: #555; font-size: 0.95rem; line-height: 1.6; margin-left: 20px;">
                    {chr(10).join(f"<li>{ref.get('raw_text', ref) if isinstance(ref, dict) else ref}</li>" for ref in references)}
                </ol>
            </div>
        </div>
        ''' if references else ''}

        <!-- Footer -->
        <div class="footer">
            <p>Generated with Novel Future Publishing</p>
        </div>
    </div>
</body>
</html>
"""

    return html
