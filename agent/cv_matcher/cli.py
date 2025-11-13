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

    def run(self, job_description_input: str) -> None:
        """
        Main processing function to adapt CV to job description.

        Args:
            job_description_input: Job description text or path to file
        """
        print("📄 Reading original CV...")
        original_cv = self.parser.read_file(self.config.cv_path)

        print("🔍 Extracting CV sections...")
        sections = self.parser.extract_sections(original_cv)

        # Load job description
        job_description = self._load_job_description(job_description_input)

        print("🤖 Analyzing CV and job description with Gemini...")
        adaptations = self.adapter.adapt_cv(sections, job_description)

        # Print explanation if available
        if "explanation" in adaptations:
            print(f"\n📝 Changes made:\n{adaptations['explanation']}\n")

        print("✏️  Applying adaptations to CV...")
        adapted_cv = self.writer.apply_adaptations(original_cv, adaptations)

        print(f"💾 Saving adapted CV to: {self.config.output_path}")
        self.writer.write_file(self.config.output_path, adapted_cv)

        print("✅ CV adaptation complete!")

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
        default="gemini-1.5-pro",
        help="Gemini model to use (default: gemini-1.5-pro)",
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
