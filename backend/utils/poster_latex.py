"""
Convert poster content to LaTeX format for professional PDF generation.
Page 1: Metadata (title, authors, affiliations, abstract)
Page 2: Poster image (converted from EMF to PNG if needed)
"""

import base64
import io
import subprocess
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PosterLaTeXGenerator:
    """Generate LaTeX documents for posters."""

    def __init__(self, poster: Dict[str, Any]):
        self.poster = poster
        self.title = poster.get("title", "Untitled Poster")
        self.authors = poster.get("authors", [])
        self.abstract = poster.get("abstract", "")
        self.poster_image = poster.get("poster_image", "")

    def escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters."""
        if not text:
            return ""
        text = str(text)
        # Order matters: backslash first
        text = text.replace("\\", r"\textbackslash{}")
        text = text.replace("&", r"\&")
        text = text.replace("%", r"\%")
        text = text.replace("$", r"\$")
        text = text.replace("#", r"\#")
        text = text.replace("_", r"\_")
        text = text.replace("{", r"\{")
        text = text.replace("}", r"\}")
        text = text.replace("~", r"\textasciitilde{}")
        text = text.replace("^", r"\textasciicircum{}")
        return text

    def format_authors(self) -> str:
        """Format author list with affiliations."""
        if not self.authors:
            return ""

        author_list = []
        for author in self.authors:
            first_name = author.get("first_name", "").strip()
            last_name = author.get("last_name", "").strip()
            affiliation = author.get("affiliation", "").strip()

            name = f"{first_name} {last_name}".strip()
            if name:
                name = self.escape_latex(name)
                if affiliation:
                    name += f"\\\\ \\small {self.escape_latex(affiliation)}"
                author_list.append(name)

        return " \\and ".join(author_list) if author_list else ""

    def save_image_file(self, tmpdir) -> str:
        """
        Save and convert image to PNG for LaTeX inclusion.
        Handles EMF, PNG, JPEG, and other Pillow-supported formats.
        Resizes large images to prevent issues.
        Returns filename if successful, empty string otherwise.
        """
        if not self.poster_image:
            logger.info("[POSTER] No poster_image data provided")
            return ""

        try:
            from PIL import Image

            # Decode base64
            image_data = self.poster_image
            if "," in image_data:
                image_data = image_data.split(",")[1]

            image_bytes = base64.b64decode(image_data)
            logger.info(f"[POSTER] Decoded image: {len(image_bytes)} bytes")

            # Try to open and convert with Pillow
            tmpdir = Path(tmpdir)
            img = Image.open(io.BytesIO(image_bytes))
            logger.info(f"[POSTER] Image opened: {img.format} {img.width}x{img.height} {img.mode}")

            # Resize if too large (prevent issues with LaTeX)
            max_dim = 4000
            if img.width > max_dim or img.height > max_dim:
                ratio = min(max_dim / img.width, max_dim / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"[POSTER] Resized to: {new_size}")

            # Convert to RGB if necessary (for JPEG compatibility)
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
                logger.info(f"[POSTER] Converted to RGB")

            # Save as PNG
            png_path = tmpdir / "poster.png"
            img.save(png_path, format="PNG", optimize=True)
            logger.info(f"[POSTER] Saved PNG: {png_path}")

            if png_path.exists():
                logger.info(f"[POSTER] PNG file exists, returning filename")
                return "poster.png"

            return ""

        except Exception as e:
            logger.error(f"[POSTER] Error processing image: {e}", exc_info=True)
            # Fallback: if all else fails, try to save raw and use EMF directly
            try:
                tmpdir = Path(tmpdir)
                image_data = self.poster_image
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                image_bytes = base64.b64decode(image_data)
                raw_path = tmpdir / "poster_raw.emf"
                raw_path.write_bytes(image_bytes)
                logger.info(f"[POSTER] Saved raw EMF fallback")
                # EMF files don't work directly in pdflatex, so return empty
                return ""
            except Exception as e2:
                logger.error(f"[POSTER] Fallback also failed: {e2}", exc_info=True)
                return ""

    def generate(self, tmpdir=None) -> str:
        """
        Generate complete LaTeX document.

        Args:
            tmpdir: Path object for temporary directory (used for image storage)

        Returns:
            LaTeX source string
        """
        image_filename = ""
        if tmpdir and self.poster_image:
            image_filename = self.save_image_file(tmpdir)

        latex = r"""\documentclass[12pt,a4paper]{article}
\usepackage[margin=0.75in]{geometry}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{setspace}
\usepackage{fancyhdr}
\pagestyle{empty}
\setstretch{1.2}

\title{}
\author{}
\date{}

\begin{document}

"""

        # Title - centered, large, with spacing
        latex += "\\begin{center}\n"
        latex += f"\\textbf{{\\Large {self.escape_latex(self.title)}}}\n"
        latex += "\\end{center}\n\n"

        # Authors - centered with affiliations
        if self.authors:
            latex += "\\begin{center}\n"
            for i, author in enumerate(self.authors):
                first_name = author.get("first_name", "").strip()
                last_name = author.get("last_name", "").strip()
                affiliation = author.get("affiliation", "").strip()

                name = f"{first_name} {last_name}".strip()
                if name:
                    latex += f"\\textbf{{{self.escape_latex(name)}}}\\\\\n"
                    if affiliation:
                        latex += f"{{\\small \\textit{{{self.escape_latex(affiliation)}}}}}\\\\\n"
                    if i < len(self.authors) - 1:
                        latex += "\\vspace{0.1cm}\n"

            latex += "\\end{center}\n\n"

        # Abstract
        if self.abstract:
            latex += "\\section*{Abstract}\n"
            latex += f"{self.escape_latex(self.abstract)}\n\n"

        # Poster image - full page
        if image_filename:
            latex += "\\newpage\n"
            latex += "\\begin{center}\n"
            latex += f"\\includegraphics[width=\\textwidth,height=\\textheight,keepaspectratio]{{{image_filename}}}\n"
            latex += "\\end{center}\n\n"

        # References
        if hasattr(self, 'references') and self.references:
            latex += "\\section*{References}\n"
            latex += "\\begin{enumerate}\n"
            for ref in self.references:
                ref_text = ref.get("raw_text") if isinstance(ref, dict) else str(ref)
                latex += f"\\item {self.escape_latex(ref_text)}\n"
            latex += "\\end{enumerate}\n\n"

        latex += "\\end{document}\n"

        return latex
