"""Gemini API adapter for CV adaptation."""

import json
import re
import sys
from typing import Dict, Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from cv_matcher.config import ADAPTATION_PROMPT_TEMPLATE
from cv_matcher.latex_parser import CVSections

# JSON Schema for structured CV adaptation response
CV_ADAPTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "tagline": {
            "type": "string",
            "description": "The adapted tagline/career summary in LaTeX format",
        },
        "mainbar": {
            "type": "string",
            "description": (
                "PAGE 1 CONTENT: Work history with job TITLES ONLY (using \\job command), "
                "Education section, Achievements, General Skills tags, and Wheel Chart. "
                "This is the SUMMARY page - NO detailed job descriptions here."
            ),
        },
        "experiences": {
            "type": "string",
            "description": (
                "PAGE 2 CONTENT: DETAILED job descriptions with bullet points for each role. "
                "Uses \\subsection for each job title followed by detailed accomplishments. "
                "This is separate from mainbar - contains the DETAILS, not the summary."
            ),
        },
        "general_skills": {
            "type": "string",
            "description": "The adapted general skills tags in LaTeX format (\\tag commands)",
        },
        "highlightbar": {
            "type": "string",
            "description": "The adapted sidebar skills section in LaTeX format",
        },
        "explanation": {
            "type": "string",
            "description": "Brief explanation of changes made to adapt the CV",
        },
    },
    "required": [
        "tagline",
        "mainbar",
        "experiences",
        "general_skills",
        "highlightbar",
        "explanation",
    ],
}


class GeminiAdapter:
    """Adapter for using Gemini API to adapt CV content."""

    def __init__(self, api_key: str, model_name: str = "gemini-3-pro-preview"):
        """
        Initialize the Gemini adapter.

        Args:
            api_key: Google Gemini API key
            model_name: Gemini model to use
        """
        genai.configure(api_key=api_key)
        self.model_name = model_name
        # Create model with structured output configuration
        self.model = genai.GenerativeModel(
            model_name,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                response_schema=CV_ADAPTATION_SCHEMA,
            ),
        )

    def adapt_cv(self, sections: CVSections, job_description: str) -> Dict[str, str]:
        """
        Use Gemini to adapt the CV to match the job description.

        Uses structured output with JSON schema for reliable parsing.

        Args:
            sections: Extracted CV sections
            job_description: Target job description

        Returns:
            Dictionary with adapted sections
        """
        from cv_matcher.latex_parser import LaTeXParser

        sections_dict = LaTeXParser.sections_to_dict(sections)
        sections_dict["job_description"] = job_description

        prompt = ADAPTATION_PROMPT_TEMPLATE.format(**sections_dict)

        # Call Gemini API with structured output
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text

            if not response_text:
                raise ValueError("Empty response received from Gemini")

            # With structured output, the response should be valid JSON
            return json.loads(response_text)

        except json.JSONDecodeError as e:
            # Fallback: try to parse with legacy method if structured output fails
            print(
                f"Structured JSON parsing failed: {e}. Trying fallback...",
                file=sys.stderr,
            )
            return self._parse_response(response_text)
        except Exception as e:
            print(f"Error calling Gemini API: {e}", file=sys.stderr)
            raise

    def fix_adaptation_errors(
        self,
        sections: CVSections,
        job_description: str,
        previous_adaptations: Dict[str, str],
        validation_error: str,
        failed_section: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Ask Gemini to fix validation errors in previous adaptation attempt.

        Uses structured output for reliable JSON response.

        Args:
            sections: Original CV sections
            job_description: Target job description
            previous_adaptations: Previous adaptation that failed validation
            validation_error: The validation error message
            failed_section: Optional name of the specific section that failed

        Returns:
            Dictionary with corrected adapted sections
        """
        from cv_matcher.latex_parser import LaTeXParser

        sections_dict = LaTeXParser.sections_to_dict(sections)

        # Identify the problematic section from error if not provided
        if not failed_section:
            for section_name in [
                "tagline",
                "mainbar",
                "experiences",
                "general_skills",
                "highlightbar",
            ]:
                if section_name.lower() in validation_error.lower():
                    failed_section = section_name
                    break

        # Build context about the specific section that failed
        section_context = ""
        if failed_section and failed_section in previous_adaptations:
            section_context = f"""
THE PROBLEMATIC SECTION ({failed_section}):
---
{previous_adaptations[failed_section][:1000]}
---

ORIGINAL {failed_section.upper()} (for reference):
---
{sections_dict.get(failed_section, 'N/A')[:1000]}
---
"""

        feedback_prompt = f"""Your previous CV adaptation failed LaTeX compilation.

COMPILATION ERROR:
{validation_error}
{section_context}

PREVIOUS FULL ADAPTATION (with error):
{json.dumps(previous_adaptations, indent=2, ensure_ascii=False)}

ORIGINAL CV SECTIONS (for reference):
---
Tagline: {sections_dict['tagline']}
Work History (truncated): {sections_dict['mainbar'][:800]}...
Detailed Experiences (truncated): {sections_dict['experiences'][:800]}...
General Skills: {sections_dict['general_skills'][:500]}
---

JOB DESCRIPTION:
{job_description[:1000]}

TASK:
Fix the LaTeX compilation error. The error message shows exactly what went wrong.

COMMON LATEX ERRORS TO CHECK:
1. Unmatched braces - every {{ must have a matching }}
2. Unmatched environments - \\begin{{X}} must have \\end{{X}}
3. Invalid characters in LaTeX (use \\& for &, \\% for %, \\$ for $, \\# for #)
4. Missing or extra backslashes in commands
5. Broken \\job, \\tag, \\skill, or \\section commands

CRITICAL RULES:
1. Return the COMPLETE corrected adaptation
2. Ensure all LaTeX braces are balanced
3. Keep the same structure as the original CV
4. Do NOT add any new information - only fix the formatting errors
"""

        # Call Gemini API with structured output
        try:
            response = self.model.generate_content(feedback_prompt)
            response_text = response.text

            if not response_text:
                raise ValueError("Empty response received from Gemini")

            return json.loads(response_text)

        except json.JSONDecodeError as e:
            print(f"JSON parsing failed in fix attempt: {e}", file=sys.stderr)
            return self._parse_response(response_text)
        except Exception as e:
            print(f"Error calling Gemini API for fix: {e}", file=sys.stderr)
            raise

    @staticmethod
    def _fix_json_escaping(json_text: str) -> str:
        r"""
        Attempt to fix common JSON escaping issues with LaTeX backslashes.

        This handles cases where Gemini returns LaTeX commands with unescaped
        backslashes (e.g., \section instead of \\section) and unescaped newlines.

        Args:
            json_text: JSON string with potential escaping issues

        Returns:
            JSON string with fixed escaping
        """
        # Step 1: Fix literal newlines, tabs, and other control characters in strings
        # We need to be careful to only fix these inside JSON string values
        # Use a more robust approach: parse character by character inside strings

        fixed_chars = []
        in_string = False
        escape_next = False

        for i, char in enumerate(json_text):
            if escape_next:
                fixed_chars.append(char)
                escape_next = False
                continue

            if char == "\\":
                fixed_chars.append(char)
                escape_next = True
                continue

            if char == '"':
                in_string = not in_string
                fixed_chars.append(char)
                continue

            if in_string:
                # Inside a string - escape control characters
                if char == "\n":
                    fixed_chars.append("\\n")
                elif char == "\r":
                    fixed_chars.append("\\r")
                elif char == "\t":
                    fixed_chars.append("\\t")
                else:
                    fixed_chars.append(char)
            else:
                fixed_chars.append(char)

        json_text = "".join(fixed_chars)

        # Step 2: Fix LaTeX backslashes
        # Now handle backslash escaping for LaTeX commands
        # First, temporarily mark already-escaped backslashes
        json_text = json_text.replace("\\\\", "\x00ESCAPED_BACKSLASH\x00")

        # Fix unescaped backslashes followed by letters (LaTeX commands)
        # This regex finds backslash followed by a character that's not part of valid JSON escapes
        json_text = re.sub(r'\\(?![nrtbfu"\\/\x00])', r"\\\\", json_text)

        # Restore the escaped backslashes
        json_text = json_text.replace("\x00ESCAPED_BACKSLASH\x00", "\\\\")

        return json_text

    @staticmethod
    def _parse_response(response_text: str) -> Dict[str, str]:
        """
        Parse the JSON response from Gemini.

        Args:
            response_text: Raw response text from Gemini

        Returns:
            Dictionary with adapted sections

        Raises:
            ValueError: If JSON parsing fails
        """
        # Extract JSON from the response (might be wrapped in markdown code blocks)
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL
        )
        if json_match:
            response_text = json_match.group(1)

        try:
            adaptations = json.loads(response_text)
        except json.JSONDecodeError as e:
            # Try to fix common JSON escaping issues with LaTeX backslashes
            print(
                f"Initial JSON parse failed: {e}. Attempting to repair...",
                file=sys.stderr,
            )
            try:
                fixed_text = GeminiAdapter._fix_json_escaping(response_text)
                adaptations = json.loads(fixed_text)
                print("✓ JSON repair successful", file=sys.stderr)
            except json.JSONDecodeError as e2:
                print(
                    f"Error parsing JSON response after repair: {e2}", file=sys.stderr
                )
                print(
                    f"Original response was: {response_text[:500]}...", file=sys.stderr
                )
                raise ValueError(f"Failed to parse Gemini response: {e2}")

        return adaptations
