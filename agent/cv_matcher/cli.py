"""Command-line interface for the CV Matcher Agent."""

import argparse
import os
import sys
from typing import Optional

from cv_matcher.config import AgentConfig
from cv_matcher.gemini_adapter import GeminiAdapter
from cv_matcher.latex_parser import LaTeXParser
from cv_matcher.latex_writer import LaTeXWriter
from cv_matcher.pdf_validator import PDFValidator
from cv_matcher.text_adapter import TextBasedAdapter, PositionExtractor, LaTeXReconstructor


class CVMatcherCLI:
    """Command-line interface for the CV Matcher Agent."""

    def __init__(
        self,
        config: AgentConfig,
        original_pdf: Optional[str] = None,
        text_mode: bool = False,
    ):
        """
        Initialize the CLI.

        Args:
            config: Agent configuration
            original_pdf: Path to the original CV PDF for visual validation
            text_mode: Use text-based adaptation (safer, preserves LaTeX structure)
        """
        self.config = config
        self.original_pdf = original_pdf
        self.text_mode = text_mode
        self.parser = LaTeXParser()
        self.writer = LaTeXWriter()

        # Initialize appropriate adapter based on mode
        if text_mode:
            self.text_adapter = TextBasedAdapter(
                api_key=config.api_key, model_name=config.model_name
            )
            self.text_extractor = PositionExtractor()
            self.reconstructor = LaTeXReconstructor()
        else:
            self.adapter = GeminiAdapter(
                api_key=config.api_key, model_name=config.model_name
            )

        # Initialize PDF validator if original PDF is provided
        self.pdf_validator = (
            PDFValidator(api_key=config.api_key) if original_pdf else None
        )

    def run(self, job_description_input: str, max_retries: int = 3) -> None:
        """
        Main processing function to adapt CV to job description.

        Args:
            job_description_input: Job description text or path to file
            max_retries: Maximum number of retry attempts if validation fails
        """
        if self.text_mode:
            self.run_text_mode(job_description_input)
        else:
            self.run_legacy_mode(job_description_input, max_retries)

    def run_text_mode(self, job_description_input: str) -> None:
        """
        Text-based adaptation mode using position-based replacement.

        This mode:
        1. Extracts TEXT content with positions from the CV
        2. Sends text to Gemini for adaptation
        3. Replaces text by direct string slicing (no pattern matching)

        The LaTeX structure is NEVER modified, guaranteeing valid output.

        Args:
            job_description_input: Job description text or path to file
        """
        print("📄 Reading original CV...")
        original_cv = self.parser.read_file(self.config.cv_path)

        # Load job description
        job_description = self._load_job_description(job_description_input)

        print("🔍 Extracting text content with positions...")
        print("   (Using position-based replacement for reliability)")
        extracted = self.text_extractor.extract_all(original_cv)

        print(f"   Found {len(extracted.jobs)} jobs")
        print(f"   Found {len(extracted.achievements)} achievements")
        print(f"   Found {len(extracted.general_skills)} skill tags")
        print(f"   Found {len(extracted.experiences)} experience descriptions")

        print("\n🤖 Adapting text content with Gemini...")
        print("   (Only text is sent to AI, not LaTeX)")

        adaptations = self.text_adapter.adapt_cv(original_cv, job_description)

        # Validate that adaptations are not empty
        if not adaptations.get("job_titles"):
            print("⚠️  Warning: job_titles is empty, using originals", file=sys.stderr)
            adaptations["job_titles"] = [job.title.text for job in extracted.jobs]

        if not adaptations.get("achievements"):
            print("⚠️  Warning: achievements is empty, using originals", file=sys.stderr)
            adaptations["achievements"] = [ach.text for ach in extracted.achievements]

        if not adaptations.get("general_skills"):
            print("⚠️  Warning: general_skills is empty, using originals", file=sys.stderr)
            adaptations["general_skills"] = [tag.text for tag in extracted.general_skills]

        if not adaptations.get("experience_descriptions"):
            print("⚠️  Warning: experience_descriptions is empty, using originals", file=sys.stderr)
            adaptations["experience_descriptions"] = [
                {"company": exp.company, "bullets": exp.content.text.split("\\\\")}
                for exp in extracted.experiences
            ]

        # Show stats
        print(f"   Received {len(adaptations.get('job_titles', []))} job titles")
        print(f"   Received {len(adaptations.get('achievements', []))} achievements")
        print(f"   Received {len(adaptations.get('general_skills', []))} skills")
        print(f"   Received {len(adaptations.get('experience_descriptions', []))} experience descriptions")

        if "explanation" in adaptations:
            print(f"\n📝 Changes made:\n{adaptations['explanation']}\n")

        # Show diff between original and adapted content
        print("📊 Comparing original vs adapted content:")
        tagline_text = extracted.tagline.text if extracted.tagline else ""
        self._show_diff("tagline", tagline_text, adaptations.get("tagline", ""))
        self._show_diff(
            "job_titles",
            [j.title.text for j in extracted.jobs],
            adaptations.get("job_titles", []),
        )
        self._show_diff(
            "achievements",
            [a.text for a in extracted.achievements],
            adaptations.get("achievements", []),
        )
        self._show_diff(
            "general_skills",
            [t.text for t in extracted.general_skills],
            adaptations.get("general_skills", []),
        )

        print("\n✏️  Applying adaptations using position-based replacement...")
        adapted_cv = self.reconstructor.apply_adaptations(
            original_cv, adaptations, extracted
        )

        print("\n🔨 Validating LaTeX compilation...")
        is_valid, error = LaTeXWriter._compile_latex(adapted_cv)

        if not is_valid:
            print(f"\n⚠️  Compilation failed: {error}", file=sys.stderr)
            print("   This shouldn't happen in position mode - please report this bug.")
            raise ValueError(f"LaTeX compilation error: {error}")

        print("✅ LaTeX compilation successful!")

        # Save the adapted CV
        print(f"\n💾 Saving adapted CV to: {self.config.output_path}")
        self.writer.write_file(self.config.output_path, adapted_cv)

        # Quality control: Compare page counts and layout
        if self.original_pdf:
            print("\n🔍 Running quality control validation...")

            # Compile adapted CV to PDF
            adapted_pdf = self.config.output_path.replace(".tex", ".pdf")
            latex_dir = os.path.dirname(self.config.cv_path)

            print("   📄 Compiling adapted CV to PDF...")
            compile_success, compile_error = LaTeXWriter.compile_to_pdf(
                self.config.output_path, adapted_pdf, latex_dir
            )

            if not compile_success:
                raise ValueError(f"PDF compilation failed: {compile_error}")

            # Quick page count check
            original_pages = self._get_page_count(self.original_pdf)
            adapted_pages = self._get_page_count(adapted_pdf)

            print(f"   📊 Page count: original={original_pages}, adapted={adapted_pages}")

            if original_pages != adapted_pages:
                print(f"\n❌ QUALITY CONTROL FAILED!", file=sys.stderr)
                print(f"   Page count mismatch: {original_pages} -> {adapted_pages}", file=sys.stderr)
                print(f"   The adapted content is too long. Content must fit in {original_pages} pages.", file=sys.stderr)
                raise ValueError(
                    f"Quality control failed: page count changed from {original_pages} to {adapted_pages}. "
                    "The adapted content is too long."
                )

            # Optional: Full visual validation with Gemini
            if self.pdf_validator:
                print("   🖼️  Running visual validation...")
                is_valid, explanation = self.pdf_validator.validate_adaptation(
                    self.original_pdf, adapted_pdf
                )

                if not is_valid:
                    print(f"\n❌ VISUAL VALIDATION FAILED: {explanation}", file=sys.stderr)
                    raise ValueError(f"Visual validation failed: {explanation}")

                print(f"   ✅ Visual validation passed: {explanation}")

            print("✅ Quality control passed!")

        print("\n✅ CV adaptation complete!")

    @staticmethod
    def _get_page_count(pdf_path: str) -> int:
        """Get the number of pages in a PDF using pdfinfo."""
        import subprocess
        try:
            result = subprocess.run(
                ["pdfinfo", pdf_path],
                capture_output=True,
                text=True,
                check=True
            )
            for line in result.stdout.split("\n"):
                if line.startswith("Pages:"):
                    return int(line.split(":")[1].strip())
            return 0
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
            return 0

    def run_legacy_mode(self, job_description_input: str, max_retries: int = 3) -> None:
        """
        Legacy mode using full LaTeX adaptation with retry loop.

        Uses a feedback loop to automatically fix compilation errors:
        1. Generate adaptation with Gemini (structured output)
        2. Apply adaptations to CV
        3. Compile LaTeX to validate
        4. If compilation fails, send error back to Gemini for correction
        5. Repeat until success or max retries reached

        Args:
            job_description_input: Job description text or path to file
            max_retries: Maximum number of retry attempts if validation fails
        """
        print("📄 Reading original CV...")
        original_cv = self.parser.read_file(self.config.cv_path)

        print("🔍 Extracting CV sections...")
        sections = self.parser.extract_sections(original_cv)

        # Load job description
        job_description = self._load_job_description(job_description_input)

        print("🤖 Analyzing CV and job description with Gemini...")
        print("   Using structured output for reliable JSON parsing")

        # Agent feedback loop with retries
        adaptations = None
        adapted_cv = None
        validation_error = None
        failed_section = None

        for attempt in range(max_retries):
            if attempt == 0:
                # First attempt - normal adaptation
                print("\n📤 Sending adaptation request to Gemini...")
                adaptations = self.adapter.adapt_cv(sections, job_description)
            else:
                # Retry with error feedback
                print(f"\n🔄 Retry attempt {attempt}/{max_retries-1}")
                print("   Sending compilation error feedback to Gemini...")
                if failed_section:
                    print(f"   Problematic section identified: {failed_section}")

                # Type assertions: adaptations and validation_error are set in first iteration
                assert adaptations is not None
                assert validation_error is not None
                adaptations = self.adapter.fix_adaptation_errors(
                    sections,
                    job_description,
                    adaptations,
                    validation_error,
                    failed_section,
                )

            # Print explanation if available
            if "explanation" in adaptations:
                print(f"\n📝 Changes made:\n{adaptations['explanation']}\n")

            print("✏️  Applying adaptations to CV...")
            print("🔨 Compiling LaTeX to validate...")

            try:
                adapted_cv = self.writer.apply_adaptations(original_cv, adaptations)

                # LaTeX compilation passed!
                print("✅ LaTeX compilation successful!")

                # Visual validation if original PDF is provided
                if self.pdf_validator and self.original_pdf:
                    print("🔍 Running visual PDF validation...")

                    # Write the adapted .tex file temporarily
                    self.writer.write_file(self.config.output_path, adapted_cv)

                    # Compile to PDF for visual comparison
                    adapted_pdf = self.config.output_path.replace(".tex", ".pdf")
                    latex_dir = os.path.dirname(self.config.cv_path)

                    print("📄 Compiling adapted CV to PDF...")
                    compile_success, compile_error = LaTeXWriter.compile_to_pdf(
                        self.config.output_path, adapted_pdf, latex_dir
                    )

                    if not compile_success:
                        raise ValueError(f"PDF compilation failed: {compile_error}")

                    # Run visual validation
                    is_valid, explanation = self.pdf_validator.validate_adaptation(
                        self.original_pdf, adapted_pdf
                    )

                    if is_valid:
                        print(f"✅ Visual validation passed: {explanation}")
                        # File is already written, we're done
                        print(f"\n💾 Adapted CV saved to: {self.config.output_path}")
                        print("\n✅ CV adaptation complete!")
                        return
                    else:
                        # Clean up the invalid files
                        if os.path.exists(self.config.output_path):
                            os.remove(self.config.output_path)
                        if os.path.exists(adapted_pdf):
                            os.remove(adapted_pdf)

                        # Treat visual validation failure as a validation error
                        raise ValueError(f"Visual validation failed: {explanation}")
                else:
                    break

            except ValueError as e:
                validation_error = str(e)
                failed_section = self._extract_failed_section(validation_error)

                print("\n⚠️  Build failed!", file=sys.stderr)
                if failed_section:
                    print(f"   Section: {failed_section}", file=sys.stderr)

                # Show truncated error for user
                error_preview = (
                    validation_error[:500] + "..."
                    if len(validation_error) > 500
                    else validation_error
                )
                print(f"   Error: {error_preview}", file=sys.stderr)

                if attempt == max_retries - 1:
                    print(f"\n❌ Failed after {max_retries} attempts", file=sys.stderr)
                    print("   The AI could not produce valid LaTeX.", file=sys.stderr)
                    raise

                print("\n🔁 Asking Gemini to fix the error...")

        # Type assertion: adapted_cv is set if we reach here (otherwise exception raised)
        assert adapted_cv is not None
        print(f"\n💾 Saving adapted CV to: {self.config.output_path}")
        self.writer.write_file(self.config.output_path, adapted_cv)

        print("\n✅ CV adaptation complete!")

    @staticmethod
    def _extract_failed_section(error_message: str) -> str | None:
        """
        Extract the section name that caused the validation error.

        Args:
            error_message: The validation error message

        Returns:
            Section name if found, None otherwise
        """
        error_lower = error_message.lower()

        # Check for section names in error message
        sections = [
            "tagline",
            "mainbar",
            "highlightbar",
            "experiences",
            "general_skills",
        ]
        for section in sections:
            if section in error_lower:
                return section

        # Check for common LaTeX command patterns
        if "\\job" in error_lower or "work history" in error_lower:
            return "mainbar"
        if "\\tag" in error_lower:
            return "general_skills"
        if "\\skill" in error_lower:
            return "highlightbar"
        if "experience" in error_lower:
            return "experiences"

        return None

    @staticmethod
    def _show_diff(field_name: str, original: any, adapted: any) -> None:
        """Show difference between original and adapted content."""
        def normalize(text: str) -> str:
            """Normalize text for comparison."""
            return " ".join(str(text).lower().split())

        if isinstance(original, list) and isinstance(adapted, list):
            # Compare lists
            changes = 0
            for i, (orig, adap) in enumerate(zip(original, adapted)):
                if normalize(orig) != normalize(adap):
                    changes += 1
            if changes > 0:
                print(f"   ✅ {field_name}: {changes}/{len(original)} items changed")
            else:
                print(f"   ⚪ {field_name}: no changes")
        else:
            # Compare strings
            if normalize(original) != normalize(adapted):
                print(f"   ✅ {field_name}: changed")
                # Show first 100 chars of each
                orig_preview = str(original)[:80].replace("\n", " ")
                adap_preview = str(adapted)[:80].replace("\n", " ")
                print(f"      - Original: {orig_preview}...")
                print(f"      + Adapted:  {adap_preview}...")
            else:
                print(f"   ⚪ {field_name}: no changes")

    @staticmethod
    def _load_job_description(input_str: str) -> str:
        """
        Load job description from file or use as direct text.

        Args:
            input_str: Job description text or path to file

        Returns:
            Job description text
        """
        if os.path.isfile(input_str):
            print(f"📋 Reading job description from file: {input_str}")
            with open(input_str, "r", encoding="utf-8") as f:
                return f.read()
        else:
            print("📋 Using job description from command line argument")
            return input_str


def main():
    """Main entry point for the CV Matcher Agent CLI."""
    parser = argparse.ArgumentParser(
        description="Adapt a LaTeX CV to match a job description using Gemini API"
    )
    parser.add_argument(
        "--cv",
        type=str,
        default="./LaTeX/resume.tex",
        help="Path to the LaTeX CV file (default: ./LaTeX/resume.tex)",
    )
    parser.add_argument(
        "--job-description",
        type=str,
        required=True,
        help="Job description text or path to a file containing the job description",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./LaTeX/resume_adapted.tex",
        help="Path to save the adapted CV (default: ./LaTeX/resume_adapted.tex)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Gemini API key (can also be set via GEMINI_API_KEY env var)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-3-pro-preview",
        help="Gemini model to use (default: gemini-3-pro-preview)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum retry attempts for LaTeX validation (default: 5)",
    )
    parser.add_argument(
        "--original-pdf",
        type=str,
        default=None,
        help="Path to original CV PDF for visual validation (optional)",
    )
    parser.add_argument(
        "--text-mode",
        action="store_true",
        default=True,
        help="Use text-based adaptation (safer, default). Gemini only sees text, not LaTeX.",
    )
    parser.add_argument(
        "--legacy-mode",
        action="store_true",
        help="Use legacy LaTeX-based adaptation (less reliable).",
    )

    args = parser.parse_args()

    # Determine mode
    text_mode = not args.legacy_mode  # Text mode by default unless legacy is specified

    # Create configuration
    try:
        config = AgentConfig.from_env(
            api_key=args.api_key,
            model_name=args.model,
            cv_path=args.cv,
            output_path=args.output,
        )
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Run the CLI
    if text_mode:
        print("🔧 Using TEXT MODE (safer, preserves LaTeX structure)")
    else:
        print("🔧 Using LEGACY MODE (LaTeX-based, may have errors)")

    cli = CVMatcherCLI(config, original_pdf=args.original_pdf, text_mode=text_mode)

    try:
        cli.run(args.job_description, max_retries=args.max_retries)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
