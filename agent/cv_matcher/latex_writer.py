"""LaTeX writer for applying CV adaptations."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, Optional, Tuple


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

            # Copy required LaTeX files (class file, supporting files, images)
            # Look for .cls, .sty, and image files in the LaTeX directory
            latex_path = os.path.abspath(latex_dir)
            if os.path.exists(latex_path):
                for filename in os.listdir(latex_path):
                    if filename.endswith((".cls", ".sty", ".jpg", ".png", ".pdf", ".jpeg")):
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
                # xelatex not available - this is an error, not a skip
                return False, (
                    "xelatex not found. Install texlive-xetex to enable validation. "
                    "Without validation, broken LaTeX files may be generated."
                )
            except Exception as e:
                return False, f"Compilation error: {str(e)}"

    @staticmethod
    def compile_to_pdf(
        tex_path: str, output_pdf_path: str, latex_dir: str = "../LaTeX", timeout: int = 60
    ) -> Tuple[bool, str]:
        """
        Compile a LaTeX file to PDF.

        Args:
            tex_path: Path to the .tex file to compile
            output_pdf_path: Path where the output PDF should be saved
            latex_dir: Directory containing LaTeX class files and dependencies
            timeout: Compilation timeout in seconds

        Returns:
            Tuple of (success, error_message)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Copy the tex file to temp directory
            tex_filename = os.path.basename(tex_path)
            tex_copy = os.path.join(tmpdir, tex_filename)
            shutil.copy2(tex_path, tex_copy)

            # Copy required LaTeX files (class file, supporting files, images)
            latex_path = os.path.abspath(latex_dir)
            if os.path.exists(latex_path):
                for filename in os.listdir(latex_path):
                    if filename.endswith((".cls", ".sty", ".jpg", ".png", ".pdf", ".jpeg")):
                        src = os.path.join(latex_path, filename)
                        dst = os.path.join(tmpdir, filename)
                        try:
                            shutil.copy2(src, dst)
                        except Exception:
                            pass

            try:
                # Run xelatex to produce PDF
                result = subprocess.run(
                    [
                        "xelatex",
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        tex_filename,
                    ],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )

                if result.returncode != 0:
                    full_error = "\n".join(result.stdout.split("\n")[-40:])
                    return False, f"LaTeX compilation failed:\n{full_error}"

                # Copy the generated PDF to the output path
                pdf_filename = tex_filename.replace(".tex", ".pdf")
                pdf_path = os.path.join(tmpdir, pdf_filename)

                if os.path.exists(pdf_path):
                    shutil.copy2(pdf_path, output_pdf_path)
                    return True, ""
                else:
                    return False, "PDF file was not generated"

            except subprocess.TimeoutExpired:
                return False, "LaTeX compilation timed out"
            except FileNotFoundError:
                return False, "xelatex not found. Install texlive-xetex."
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
    def _escape_latex_specials(content: str) -> str:
        """
        Escape special LaTeX characters that Gemini might forget to escape.

        Only escapes characters that are NOT already escaped.
        Preserves LaTeX commands (backslash followed by letters).

        Args:
            content: Content that may contain unescaped special characters

        Returns:
            Content with special characters properly escaped
        """
        # Characters that need escaping in LaTeX: & % $ #
        # We skip { } because they're structural
        # We skip _ because it's often in commands

        # Use regex to find unescaped special chars
        # A char is unescaped if not preceded by odd number of backslashes

        def escape_if_needed(match: re.Match) -> str:
            """Escape the character if not already escaped."""
            full = match.group(0)
            # Check how many backslashes precede
            backslashes = len(full) - 1  # Everything except the special char
            special_char = full[-1]

            # If even number of backslashes (including 0), the char is unescaped
            if backslashes % 2 == 0:
                return full[:-1] + "\\" + special_char
            else:
                # Already escaped
                return full

        # Match: any number of backslashes followed by special char
        # We process & % $ # separately
        result = content

        # Escape & (but not \&)
        result = re.sub(r"(\\*)&", escape_if_needed, result)

        # Escape % (but not \%)
        result = re.sub(r"(\\*)%", escape_if_needed, result)

        # Escape $ (but not \$) - be careful with $$ math mode
        # Don't escape if it's $$ (display math)
        result = re.sub(r"(\\*)\$(?!\$)", escape_if_needed, result)

        # Escape # (but not \#)
        result = re.sub(r"(\\*)#", escape_if_needed, result)

        return result

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
        # First, escape any unescaped special LaTeX characters
        content = LaTeXWriter._escape_latex_specials(content)

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
        # First, validate ALL sections BEFORE applying any changes
        print("🔍 Validating adapted sections...", file=sys.stderr)
        validation_errors = []

        for section_name in ["tagline", "mainbar", "experiences", "general_skills", "highlightbar"]:
            if section_name in adaptations:
                content = adaptations[section_name].strip()
                is_valid, error = LaTeXWriter._validate_braces(content, section_name)
                if not is_valid:
                    validation_errors.append(f"{section_name}: {error}")
                    print(f"❌ {section_name}: {error}", file=sys.stderr)
                    # Show context around the error
                    print(f"   Content preview: {content[:200]}...", file=sys.stderr)
                else:
                    print(f"✓ {section_name}: braces balanced", file=sys.stderr)

        # If any validation errors, raise immediately
        if validation_errors:
            error_msg = "Brace validation failed:\n" + "\n".join(validation_errors)
            raise ValueError(error_msg)

        print("✅ All sections validated", file=sys.stderr)

        updated_cv = original_cv

        # Replace tagline
        if "tagline" in adaptations:
            tagline_content = adaptations["tagline"].strip()
            # Remove any LaTeX command prefix if Gemini accidentally included it
            tagline_content = re.sub(
                r"^\\tagline\{(.+)\}$", r"\1", tagline_content, flags=re.DOTALL
            )

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

            updated_cv = re.sub(
                r"(\\highlightbar\{)(.*?)(\n\})",
                lambda m: m.group(1) + "\n" + highlightbar_content + m.group(3),
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace mainbar section
        if "mainbar" in adaptations:
            mainbar_content = LaTeXWriter._clean_content(adaptations["mainbar"])

            # The pattern captures: \mainbar{ ... content ... } \makebody
            # We need to preserve the closing brace before \makebody
            updated_cv = re.sub(
                r"(\\mainbar\{)(.*?)(\}\s*\\makebody)",
                lambda m: m.group(1) + "\n" + mainbar_content + "\n" + m.group(3),
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace experiences section
        if "experiences" in adaptations:
            experiences_content = LaTeXWriter._clean_content(adaptations["experiences"])

            # The experiences section is inside the second \mainbar{...}
            # Preserve the closing brace before \makebody
            updated_cv = re.sub(
                r"(\\section\{Experiences description\})(.*?)(\}\s*\\makebody)",
                lambda m: m.group(1) + "\n" + experiences_content + "\n" + m.group(3),
                updated_cv,
                flags=re.DOTALL,
            )

        # Replace general skills
        if "general_skills" in adaptations:
            general_skills_content = LaTeXWriter._clean_content(
                adaptations["general_skills"]
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
        print("🔨 Compiling LaTeX to validate structure...", file=sys.stderr)
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
