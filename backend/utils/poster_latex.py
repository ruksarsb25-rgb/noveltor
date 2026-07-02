"""
Convert poster content to LaTeX format for professional PDF generation.
Page 1: Metadata (title, authors, affiliations, abstract)
Page 2: Poster image
"""

import base64
import io
from typing import Dict, Any


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
        Save base64 image to file and return filename.
        Returns empty string if image cannot be saved.
        """
        if not self.poster_image:
            return ""

        try:
            # Decode base64
            image_data = self.poster_image
            if "," in image_data:
                image_data = image_data.split(",")[1]

            image_bytes = base64.b64decode(image_data)

            # Save to file
            image_path = tmpdir / "poster.png"
            image_path.write_bytes(image_bytes)
            return "poster.png"
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

        latex = r"""\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{hyperref}

"""

        # Title
        latex += f"\\title{{{self.escape_latex(self.title)}}}\n"

        # Authors
        if self.authors:
            latex += f"\\author{{{self.format_authors()}}}\n"

        # Date
        latex += "\\date{}\n\n"

        latex += "\\begin{document}\n\n"
        latex += "\\maketitle\n\n"

        # Abstract
        if self.abstract:
            latex += "\\begin{abstract}\n"
            latex += f"{self.escape_latex(self.abstract)}\n"
            latex += "\\end{abstract}\n\n"

        # Page break
        latex += "\\newpage\n\n"

        # Poster image
        if image_filename:
            latex += "\\begin{center}\n"
            latex += f"\\includegraphics[width=0.9\\textwidth]{{{image_filename}}}\n"
            latex += "\\end{center}\n\n"

        latex += "\\end{document}\n"

        return latex
