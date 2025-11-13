"""LaTeX writer for applying CV adaptations."""

import re
from typing import Dict


class LaTeXWriter:
    """Writer for applying adaptations to LaTeX CV files."""

    @staticmethod
    def apply_adaptations(
        original_cv: str, adaptations: Dict[str, str]
    ) -> str:
        """
        Apply the adaptations to the original CV.

        Args:
            original_cv: Original LaTeX CV content
            adaptations: Dictionary with adapted sections

        Returns:
            Updated CV content with adaptations applied
        """
        updated_cv = original_cv

        # Replace tagline
        if "tagline" in adaptations:
            updated_cv = re.sub(
                r"\\tagline\{[^}]+\}",
                f"\\\\tagline{{{adaptations['tagline']}}}",
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace highlightbar section
        if "highlightbar" in adaptations:
            updated_cv = re.sub(
                r"(\\highlightbar\{)(.*?)(\n\})",
                f"\\1{adaptations['highlightbar']}\\3",
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace mainbar section
        if "mainbar" in adaptations:
            updated_cv = re.sub(
                r"(\\mainbar\{)(.*?)(\\makebody)",
                f"\\1{adaptations['mainbar']}\\3",
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace experiences section
        if "experiences" in adaptations:
            updated_cv = re.sub(
                r"(\\section\{Experiences description\})(.*?)(\\makebody)",
                f"\\1{adaptations['experiences']}\\3",
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace general skills
        if "general_skills" in adaptations:
            updated_cv = re.sub(
                r"(\\section\{General Skills\})(.*?)(\\section\{Wheel Chart\})",
                f"\\1{adaptations['general_skills']}\\3",
                updated_cv,
                flags=re.DOTALL,
            )

        return updated_cv

    @staticmethod
    def write_file(file_path: str, content: str) -> None:
        """
        Write content to a file.

        Args:
            file_path: Path to the output file
            content: Content to write
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
