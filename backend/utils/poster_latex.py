"""
Convert poster content to LaTeX format for professional PDF generation.
Page 1: Metadata (title, authors, affiliations, abstract)
Page 2: Poster image (converted from EMF to PNG if needed)
"""

import base64
import io
import subprocess
from typing import Dict, Any
from pathlib import Path


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
        Save and convert image (EMF → PNG) for LaTeX inclusion.
        Returns filename if successful, empty string otherwise.
        """
        if not self.poster_image:
            return ""

        try:
            # Decode base64
            image_data = self.poster_image
            if "," in image_data:
                image_data = image_data.split(",")[1]

            image_bytes = base64.b64decode(image_data)

            # Save raw image
            tmpdir = Path(tmpdir)
            raw_image_path = tmpdir / "poster_raw.emf"
            raw_image_path.write_bytes(image_bytes)

            # Convert EMF to PNG using ImageMagick
            png_path = tmpdir / "poster.png"
            try:
                # Try newer 'magick' command first (ImageMagick v7+)
                subprocess.run(
                    ["magick", str(raw_image_path), str(png_path)],
                    capture_output=True,
                    timeout=60,
                    check=True
                )
                if png_path.exists():
                    return "poster.png"
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                # If conversion fails, try using the image as-is
                pass

            # Fallback: if conversion failed, check if it's already a supported format
            # Try to use raw file directly
            if raw_image_path.exists():
                return "poster_raw.emf"

            return ""

        except Exception:
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
\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{setspace}
\setstretch{1.3}

\title{}
\author{}
\date{}

\begin{document}

"""

        # Title - larger and centered
        latex += f"\\section*{{{self.escape_latex(self.title)}}}\n\n"

        # Authors - with affiliations
        if self.authors:
            for author in self.authors:
                first_name = author.get("first_name", "").strip()
                last_name = author.get("last_name", "").strip()
                affiliation = author.get("affiliation", "").strip()

                name = f"{first_name} {last_name}".strip()
                latex += f"\\textbf{{{self.escape_latex(name)}}}\n\n"

                if affiliation:
                    latex += f"\\textit{{{self.escape_latex(affiliation)}}}\n\n"

        # Abstract
        if self.abstract:
            latex += "\\section*{Abstract}\n\n"
            latex += f"{self.escape_latex(self.abstract)}\n\n"

        # References
        if hasattr(self, 'references') and self.references:
            latex += "\\section*{References}\n\n"
            latex += "\\begin{enumerate}\n"
            for ref in self.references:
                ref_text = ref.get("raw_text") if isinstance(ref, dict) else str(ref)
                latex += f"\\item {self.escape_latex(ref_text)}\n"
            latex += "\\end{enumerate}\n\n"

        # Page break before image
        if image_filename:
            latex += "\\newpage\n\n"
            latex += "\\section*{Poster}\n\n"
            latex += "\\begin{center}\n"
            latex += f"\\includegraphics[width=0.9\\textwidth]{{{image_filename}}}\n"
            latex += "\\end{center}\n\n"

        latex += "\\end{document}\n"

        return latex
