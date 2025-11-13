"""LaTeX CV parser for extracting editable sections."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class CVSections:
    """Container for CV sections."""

    tagline: Optional[str] = None
    highlightbar: Optional[str] = None
    mainbar: Optional[str] = None
    experiences: Optional[str] = None
    general_skills: Optional[str] = None


class LaTeXParser:
    """Parser for extracting sections from LaTeX CV files."""

    @staticmethod
    def read_file(file_path: str) -> str:
        """
        Read the LaTeX CV file.

        Args:
            file_path: Path to the LaTeX CV file

        Returns:
            Content of the CV file
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def extract_sections(latex_content: str) -> CVSections:
        """
        Extract the editable sections from the LaTeX CV.

        Args:
            latex_content: Full LaTeX content

        Returns:
            CVSections object with extracted sections
        """
        sections = CVSections()

        # Extract tagline
        tagline_match = re.search(
            r"\\tagline\{([^}]+)\}", latex_content, re.DOTALL
        )
        if tagline_match:
            sections.tagline = tagline_match.group(1)

        # Extract highlightbar content
        highlightbar_match = re.search(
            r"\\highlightbar\{(.*?)\n\}", latex_content, re.DOTALL
        )
        if highlightbar_match:
            sections.highlightbar = highlightbar_match.group(1)

        # Extract mainbar content (first page)
        mainbar_match = re.search(
            r"\\mainbar\{(.*?)\\makebody", latex_content, re.DOTALL
        )
        if mainbar_match:
            sections.mainbar = mainbar_match.group(1)

        # Extract detailed experiences (second page)
        exp_match = re.search(
            r"\\section\{Experiences description\}(.*?)\\makebody",
            latex_content,
            re.DOTALL,
        )
        if exp_match:
            sections.experiences = exp_match.group(1)

        # Extract general skills tags
        gen_skills_match = re.search(
            r"\\section\{General Skills\}(.*?)\\section\{Wheel Chart\}",
            latex_content,
            re.DOTALL,
        )
        if gen_skills_match:
            sections.general_skills = gen_skills_match.group(1)

        return sections

    @staticmethod
    def sections_to_dict(sections: CVSections) -> dict:
        """
        Convert CVSections to a dictionary for template formatting.

        Args:
            sections: CVSections object

        Returns:
            Dictionary with section names and content
        """
        return {
            "tagline": sections.tagline or "N/A",
            "highlightbar": sections.highlightbar or "N/A",
            "mainbar": sections.mainbar or "N/A",
            "experiences": sections.experiences or "N/A",
            "general_skills": sections.general_skills or "N/A",
        }
