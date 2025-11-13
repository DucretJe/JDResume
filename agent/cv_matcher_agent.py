#!/usr/bin/env python3
"""
CV Job Matcher Agent
Uses Gemini API to adapt a LaTeX CV to match a specific job description.
The agent stays grounded on the existing CV content and only reformulates/highlights relevant skills.
"""

import os
import sys
import argparse
import re
from pathlib import Path
import google.generativeai as genai


class CVMatcherAgent:
    """Agent that adapts a CV to match a job description using Gemini API."""

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro"):
        """
        Initialize the CV Matcher Agent.

        Args:
            api_key: Google Gemini API key
            model_name: Gemini model to use (default: gemini-1.5-pro)
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def read_latex_cv(self, cv_path: str) -> str:
        """
        Read the LaTeX CV file.

        Args:
            cv_path: Path to the LaTeX CV file

        Returns:
            Content of the CV file
        """
        with open(cv_path, 'r', encoding='utf-8') as f:
            return f.read()

    def extract_editable_sections(self, latex_content: str) -> dict:
        """
        Extract the sections that can be edited from the LaTeX CV.

        Args:
            latex_content: Full LaTeX content

        Returns:
            Dictionary with editable sections
        """
        sections = {}

        # Extract tagline
        tagline_match = re.search(r'\\tagline\{([^}]+)\}', latex_content, re.DOTALL)
        if tagline_match:
            sections['tagline'] = tagline_match.group(1)

        # Extract skills section (the entire \highlightbar{...} content)
        highlightbar_match = re.search(r'\\highlightbar\{(.*?)\n\}', latex_content, re.DOTALL)
        if highlightbar_match:
            sections['highlightbar'] = highlightbar_match.group(1)

        # Extract work experiences (the entire \mainbar{...} content on first page)
        mainbar_match = re.search(r'\\mainbar\{(.*?)\\makebody', latex_content, re.DOTALL)
        if mainbar_match:
            sections['mainbar'] = mainbar_match.group(1)

        # Extract detailed experiences (second page)
        exp_match = re.search(r'\\section\{Experiences description\}(.*?)\\makebody', latex_content, re.DOTALL)
        if exp_match:
            sections['experiences'] = exp_match.group(1)

        # Extract general skills tags
        gen_skills_match = re.search(r'\\section\{General Skills\}(.*?)\\section\{Wheel Chart\}', latex_content, re.DOTALL)
        if gen_skills_match:
            sections['general_skills'] = gen_skills_match.group(1)

        return sections

    def adapt_cv_to_job(self, cv_content: str, job_description: str) -> str:
        """
        Use Gemini to adapt the CV to match the job description.

        Args:
            cv_content: Original CV LaTeX content
            job_description: Target job description

        Returns:
            Adapted CV content
        """
        sections = self.extract_editable_sections(cv_content)

        prompt = f"""You are a professional CV optimization expert. Your task is to adapt a CV to match a specific job description while staying COMPLETELY GROUNDED on the existing content.

STRICT RULES:
1. DO NOT invent or add any skills, experiences, or qualifications that are not already in the CV
2. DO NOT exaggerate or lie about capabilities
3. ONLY reformulate, reorder, and highlight existing content to better match the job description
4. Keep the LaTeX formatting intact
5. Maintain professional tone and clarity

ORIGINAL CV SECTIONS:
---
Tagline:
{sections.get('tagline', 'N/A')}

Work History:
{sections.get('mainbar', 'N/A')}

Detailed Experiences:
{sections.get('experiences', 'N/A')}

General Skills:
{sections.get('general_skills', 'N/A')}

Skills Sidebar:
{sections.get('highlightbar', 'N/A')}
---

JOB DESCRIPTION:
---
{job_description}
---

TASK:
Analyze the job description and adapt the CV sections to better match it. Focus on:
1. Rewriting the tagline to highlight the most relevant experience for this role
2. Reordering or emphasizing work experiences that match the job requirements
3. Reformulating experience descriptions to use keywords from the job description
4. Highlighting relevant skills that match the job
5. Adjusting the general skills tags to prioritize relevant technologies

Return ONLY a JSON object with the following structure:
{{
    "tagline": "adapted tagline here",
    "mainbar": "adapted mainbar section here",
    "experiences": "adapted experiences section here",
    "general_skills": "adapted general skills section here",
    "highlightbar": "adapted highlightbar section here",
    "explanation": "Brief explanation of changes made"
}}

Make sure all LaTeX formatting is preserved exactly as in the original."""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error calling Gemini API: {e}", file=sys.stderr)
            raise

    def apply_adaptations(self, original_cv: str, adaptations_json: str) -> str:
        """
        Apply the adaptations to the original CV.

        Args:
            original_cv: Original LaTeX CV content
            adaptations_json: JSON string with adapted sections

        Returns:
            Updated CV content
        """
        import json

        # Extract JSON from the response (might be wrapped in markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', adaptations_json, re.DOTALL)
        if json_match:
            adaptations_json = json_match.group(1)

        try:
            adaptations = json.loads(adaptations_json)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}", file=sys.stderr)
            print(f"Response was: {adaptations_json}", file=sys.stderr)
            raise

        # Apply adaptations
        updated_cv = original_cv

        # Replace tagline
        if 'tagline' in adaptations:
            updated_cv = re.sub(
                r'\\tagline\{[^}]+\}',
                f'\\\\tagline{{{adaptations["tagline"]}}}',
                updated_cv,
                flags=re.DOTALL
            )

        # Replace highlightbar section
        if 'highlightbar' in adaptations:
            updated_cv = re.sub(
                r'(\\highlightbar\{)(.*?)(\n\})',
                f'\\1{adaptations["highlightbar"]}\\3',
                updated_cv,
                flags=re.DOTALL
            )

        # Replace mainbar section
        if 'mainbar' in adaptations:
            updated_cv = re.sub(
                r'(\\mainbar\{)(.*?)(\\makebody)',
                f'\\1{adaptations["mainbar"]}\\3',
                updated_cv,
                flags=re.DOTALL
            )

        # Replace experiences section
        if 'experiences' in adaptations:
            updated_cv = re.sub(
                r'(\\section\{Experiences description\})(.*?)(\\makebody)',
                f'\\1{adaptations["experiences"]}\\3',
                updated_cv,
                flags=re.DOTALL
            )

        # Replace general skills
        if 'general_skills' in adaptations:
            updated_cv = re.sub(
                r'(\\section\{General Skills\})(.*?)(\\section\{Wheel Chart\})',
                f'\\1{adaptations["general_skills"]}\\3',
                updated_cv,
                flags=re.DOTALL
            )

        return updated_cv

    def process(self, cv_path: str, job_description: str, output_path: str) -> None:
        """
        Main processing function to adapt CV to job description.

        Args:
            cv_path: Path to the original LaTeX CV
            job_description: Job description text or path to file
            output_path: Path to save the adapted CV
        """
        print("📄 Reading original CV...")
        original_cv = self.read_latex_cv(cv_path)

        # Check if job_description is a file path
        if os.path.isfile(job_description):
            print(f"📋 Reading job description from file: {job_description}")
            with open(job_description, 'r', encoding='utf-8') as f:
                job_description = f.read()
        else:
            print("📋 Using job description from command line argument")

        print("🤖 Analyzing CV and job description with Gemini...")
        adaptations = self.adapt_cv_to_job(original_cv, job_description)

        print("✏️  Applying adaptations to CV...")
        adapted_cv = self.apply_adaptations(original_cv, adaptations)

        print(f"💾 Saving adapted CV to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(adapted_cv)

        print("✅ CV adaptation complete!")

        # Extract and print explanation if available
        try:
            import json
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', adaptations, re.DOTALL)
            if json_match:
                adaptations_json = json_match.group(1)
            else:
                adaptations_json = adaptations
            parsed = json.loads(adaptations_json)
            if 'explanation' in parsed:
                print(f"\n📝 Changes made:\n{parsed['explanation']}")
        except:
            pass


def main():
    """Main entry point for the CV Matcher Agent."""
    parser = argparse.ArgumentParser(
        description='Adapt a LaTeX CV to match a job description using Gemini API'
    )
    parser.add_argument(
        '--cv',
        type=str,
        default='./LaTeX/resume.tex',
        help='Path to the LaTeX CV file (default: ./LaTeX/resume.tex)'
    )
    parser.add_argument(
        '--job-description',
        type=str,
        required=True,
        help='Job description text or path to a file containing the job description'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='./LaTeX/resume_adapted.tex',
        help='Path to save the adapted CV (default: ./LaTeX/resume_adapted.tex)'
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='Gemini API key (can also be set via GEMINI_API_KEY env var)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gemini-1.5-pro',
        help='Gemini model to use (default: gemini-1.5-pro)'
    )

    args = parser.parse_args()

    # Get API key from args or environment
    api_key = args.api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Error: Gemini API key not provided. Use --api-key or set GEMINI_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)

    # Initialize agent
    agent = CVMatcherAgent(api_key=api_key, model_name=args.model)

    # Process CV
    try:
        agent.process(args.cv, args.job_description, args.output)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
