"""LaTeX writer for applying CV adaptations."""

import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, Tuple


class LaTeXWriter:
    """Writer for applying adaptations to LaTeX CV files."""

    @staticmethod
    def _compile_latex(
        latex_content: str, latex_dir: str = "../LaTeX", timeout: int = 30
    ) -> Tuple[bool, str]:
        """
        Attempt to compile LaTeX content to check for errors.

        Args:
            latex_content: LaTeX content to compile
            latex_dir: Directory containing LaTeX class files and dependencies
            timeout: Compilation timeout in seconds

        Returns:
            Tuple of (success, error_message)
        """
        import shutil

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write LaTeX content to temp file
            tex_file = os.path.join(tmpdir, "test.tex")
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(latex_content)

            # Copy required LaTeX files (class file, supporting files)
            # Look for .cls, .sty files in the LaTeX directory
            latex_path = os.path.abspath(latex_dir)
            if os.path.exists(latex_path):
                for filename in os.listdir(latex_path):
                    if filename.endswith((".cls", ".sty")):
                        src = os.path.join(latex_path, filename)
                        dst = os.path.join(tmpdir, filename)
                        try:
                            shutil.copy2(src, dst)
                        except Exception:
                            pass  # Continue even if some files can't be copied

            try:
                # Run xelatex with minimal output
                result = subprocess.run(
                    [
                        "xelatex",
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        "-no-pdf",
                        "test.tex",
                    ],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                if result.returncode != 0:
                    # Get the last 40 lines which usually contain the error context
                    full_error = "\n".join(result.stdout.split("\n")[-40:])
                    return False, f"LaTeX compilation failed:\n{full_error}"

                return True, ""

            except subprocess.TimeoutExpired:
                return False, "LaTeX compilation timed out"
            except FileNotFoundError:
                # xelatex not available - fall back to basic validation
                print(
                    "⚠️  xelatex not available, skipping compilation check",
                    file=sys.stderr,
                )
                return True, ""
            except Exception as e:
                return False, f"Compilation error: {str(e)}"

    @staticmethod
    def _validate_braces(content: str, section_name: str = "") -> Tuple[bool, str]:
        """
        Validate that LaTeX braces are properly matched.

        Args:
            content: LaTeX content to validate
            section_name: Name of the section for error messages

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Count braces, ignoring escaped braces \{ and \}
        # We need to track brace depth
        depth = 0
        i = 0
        while i < len(content):
            if i > 0 and content[i - 1] == "\\":
                # This is an escaped brace, skip it
                i += 1
                continue

            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1

            if depth < 0:
                return (
                    False,
                    f"Unmatched closing brace in {section_name} at position {i}",
                )

            i += 1

        if depth != 0:
            return False, f"Unmatched opening braces in {section_name} (depth: {depth})"

        return True, ""

    @staticmethod
    def _validate_latex_structure(
        original_cv: str, adapted_cv: str
    ) -> Tuple[bool, str]:
        """
        Validate that the adapted CV has valid LaTeX structure.

        Args:
            original_cv: Original CV content
            adapted_cv: Adapted CV content

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check overall brace matching
        is_valid, error = LaTeXWriter._validate_braces(adapted_cv, "adapted CV")
        if not is_valid:
            return False, error

        # Check that key structural commands are still present
        required_commands = [
            r"\\name\{",
            r"\\tagline\{",
            r"\\makeheader\{",
            r"\\highlightbar\{",
            r"\\mainbar\{",
        ]
        for cmd in required_commands:
            if not re.search(cmd, adapted_cv):
                return (
                    False,
                    f"Missing required command {cmd.replace(chr(92)*2, chr(92))} in adapted CV",
                )

        return True, ""

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
            return " ".join(content.split())

    @staticmethod
    def apply_adaptations(original_cv: str, adaptations: Dict[str, str]) -> str:
        """
        Apply the adaptations to the original CV.

        Args:
            original_cv: Original LaTeX CV content
            adaptations: Dictionary with adapted sections

        Returns:
            Updated CV content with adaptations applied

        Raises:
            ValueError: If adapted content has invalid LaTeX structure
        """
        updated_cv = original_cv

        # Replace tagline
        if "tagline" in adaptations:
            # Strip leading/trailing whitespace and normalize line breaks
            tagline_content = adaptations["tagline"].strip()
            # Remove any LaTeX command prefix if Gemini accidentally included it
            tagline_content = re.sub(
                r"^\\tagline\{(.+)\}$", r"\1", tagline_content, flags=re.DOTALL
            )

            # Validate braces in tagline
            is_valid, error = LaTeXWriter._validate_braces(tagline_content, "tagline")
            if not is_valid:
                print(f"⚠️  Warning: {error}", file=sys.stderr)
                print(f"Content: {tagline_content[:100]}...", file=sys.stderr)

            updated_cv = re.sub(
                r"\\tagline\{[^}]+\}",
                lambda m: f"\\tagline{{{tagline_content}}}",
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace highlightbar section
        if "highlightbar" in adaptations:
            highlightbar_content = LaTeXWriter._clean_content(
                adaptations["highlightbar"]
            )

            # Validate braces
            is_valid, error = LaTeXWriter._validate_braces(
                highlightbar_content, "highlightbar"
            )
            if not is_valid:
                print(f"⚠️  Warning: {error}", file=sys.stderr)
                print(
                    f"Content preview: {highlightbar_content[:100]}...", file=sys.stderr
                )

            updated_cv = re.sub(
                r"(\\highlightbar\{)(.*?)(\n\})",
                lambda m: m.group(1) + "\n" + highlightbar_content + m.group(3),
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace mainbar section
        if "mainbar" in adaptations:
            mainbar_content = LaTeXWriter._clean_content(adaptations["mainbar"])

            # Validate braces in mainbar - this is critical!
            is_valid, error = LaTeXWriter._validate_braces(mainbar_content, "mainbar")
            if not is_valid:
                print(f"⚠️  Warning: {error}", file=sys.stderr)
                print(f"Content preview: {mainbar_content[:200]}...", file=sys.stderr)

            updated_cv = re.sub(
                r"(\\mainbar\{)(.*?)(\\makebody)",
                lambda m: m.group(1) + "\n" + mainbar_content + "\n\n" + m.group(3),
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace experiences section
        if "experiences" in adaptations:
            experiences_content = LaTeXWriter._clean_content(adaptations["experiences"])

            # Validate braces
            is_valid, error = LaTeXWriter._validate_braces(
                experiences_content, "experiences"
            )
            if not is_valid:
                print(f"⚠️  Warning: {error}", file=sys.stderr)
                print(
                    f"Content preview: {experiences_content[:200]}...", file=sys.stderr
                )

            updated_cv = re.sub(
                r"(\\section\{Experiences description\})(.*?)(\\makebody)",
                lambda m: m.group(1) + "\n" + experiences_content + "\n\n" + m.group(3),
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace general skills
        if "general_skills" in adaptations:
            general_skills_content = LaTeXWriter._clean_content(
                adaptations["general_skills"]
            )

            # Validate braces
            is_valid, error = LaTeXWriter._validate_braces(
                general_skills_content, "general_skills"
            )
            if not is_valid:
                print(f"⚠️  Warning: {error}", file=sys.stderr)
                print(
                    f"Content preview: {general_skills_content[:100]}...",
                    file=sys.stderr,
                )

            updated_cv = re.sub(
                r"(\\section\{General Skills\})(.*?)(\\section\{Wheel Chart\})",
                lambda m: m.group(1)
                + "\n"
                + general_skills_content
                + "\n\n"
                + m.group(3),
                updated_cv,
                flags=re.DOTALL,
            )

        # Validate the final adapted CV by actually compiling it
        print("🔍 Compiling LaTeX to validate structure...", file=sys.stderr)
        is_valid, error = LaTeXWriter._compile_latex(updated_cv)
        if not is_valid:
            print("❌ LaTeX compilation failed", file=sys.stderr)
            raise ValueError(f"LaTeX compilation error:\n{error}")

        print("✅ LaTeX compilation successful", file=sys.stderr)
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
