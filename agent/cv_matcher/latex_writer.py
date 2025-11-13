"""LaTeX writer for applying CV adaptations."""

import re
from typing import Dict


class LaTeXWriter:
    """Writer for applying adaptations to LaTeX CV files."""

    @staticmethod
    def _clean_content(content: str, preserve_internal_whitespace: bool = True) -> str:
        """
        Clean adapted content from Gemini to prevent LaTeX compilation errors.

        Args:
            content: The content to clean
            preserve_internal_whitespace: If True, only strip leading/trailing whitespace

        Returns:
            Cleaned content safe for LaTeX insertion
        """
        if preserve_internal_whitespace:
            # Only strip leading and trailing whitespace/newlines
            return content.strip()
        else:
            # More aggressive cleaning if needed
            return ' '.join(content.split())

    @staticmethod
    def apply_adaptations(original_cv: str, adaptations: Dict[str, str]) -> str:
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
            # Strip leading/trailing whitespace and normalize line breaks
            tagline_content = adaptations['tagline'].strip()
            # Remove any LaTeX command prefix if Gemini accidentally included it
            tagline_content = re.sub(r'^\\tagline\{(.+)\}$', r'\1', tagline_content, flags=re.DOTALL)

            updated_cv = re.sub(
                r"\\tagline\{[^}]+\}",
                lambda m: f"\\\\tagline{{{tagline_content}}}",
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace highlightbar section
        if "highlightbar" in adaptations:
            highlightbar_content = LaTeXWriter._clean_content(adaptations['highlightbar'])
            updated_cv = re.sub(
                r"(\\highlightbar\{)(.*?)(\n\})",
                lambda m: m.group(1) + '\n' + highlightbar_content + m.group(3),
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace mainbar section
        if "mainbar" in adaptations:
            mainbar_content = LaTeXWriter._clean_content(adaptations['mainbar'])
            updated_cv = re.sub(
                r"(\\mainbar\{)(.*?)(\\makebody)",
                lambda m: m.group(1) + '\n' + mainbar_content + '\n\n' + m.group(3),
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace experiences section
        if "experiences" in adaptations:
            experiences_content = LaTeXWriter._clean_content(adaptations['experiences'])
            updated_cv = re.sub(
                r"(\\section\{Experiences description\})(.*?)(\\makebody)",
                lambda m: m.group(1) + '\n' + experiences_content + '\n\n' + m.group(3),
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace general skills
        if "general_skills" in adaptations:
            general_skills_content = LaTeXWriter._clean_content(adaptations['general_skills'])
            updated_cv = re.sub(
                r"(\\section\{General Skills\})(.*?)(\\section\{Wheel Chart\})",
                lambda m: m.group(1) + '\n' + general_skills_content + '\n\n' + m.group(3),
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
