"""Command-line interface for the CV Matcher Agent."""

import argparse
import os
import sys

from cv_matcher.config import AgentConfig
from cv_matcher.gemini_adapter import GeminiAdapter
from cv_matcher.latex_parser import LaTeXParser
from cv_matcher.latex_writer import LaTeXWriter


class CVMatcherCLI:
    """Command-line interface for the CV Matcher Agent."""

    def __init__(self, config: AgentConfig):
        """
        Initialize the CLI.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.parser = LaTeXParser()
        self.adapter = GeminiAdapter(
            api_key=config.api_key, model_name=config.model_name
        )
        self.writer = LaTeXWriter()

    def run(self, job_description_input: str, max_retries: int = 3) -> None:
        """
        Main processing function to adapt CV to job description.

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

                # Validation and compilation passed!
                print("✅ LaTeX compilation successful!")
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
        default="gemini-2.5-pro",
        help="Gemini model to use (default: gemini-2.5-pro)",
    )

    args = parser.parse_args()

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
    cli = CVMatcherCLI(config)

    try:
        cli.run(args.job_description)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
