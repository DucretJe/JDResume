"""Gemini API adapter for CV adaptation."""

import json
import re
import sys
from typing import Dict

import google.generativeai as genai
from cv_matcher.config import ADAPTATION_PROMPT_TEMPLATE
from cv_matcher.latex_parser import CVSections


class GeminiAdapter:
    """Adapter for using Gemini API to adapt CV content."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize the Gemini adapter.

        Args:
            api_key: Google Gemini API key
            model_name: Gemini model to use
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def adapt_cv(self, sections: CVSections, job_description: str) -> Dict[str, str]:
        """
        Use Gemini to adapt the CV to match the job description.

        Args:
            sections: Extracted CV sections
            job_description: Target job description

        Returns:
            Dictionary with adapted sections
        """
        # Prepare the prompt
        from cv_matcher.latex_parser import LaTeXParser

        sections_dict = LaTeXParser.sections_to_dict(sections)
        sections_dict["job_description"] = job_description

        prompt = ADAPTATION_PROMPT_TEMPLATE.format(**sections_dict)

        # Call Gemini API
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
        except Exception as e:
            print(f"Error calling Gemini API: {e}", file=sys.stderr)
            raise

        # Parse the JSON response
        return self._parse_response(response_text)

    def fix_adaptation_errors(
        self,
        sections: CVSections,
        job_description: str,
        previous_adaptations: Dict[str, str],
        validation_error: str,
    ) -> Dict[str, str]:
        """
        Ask Gemini to fix validation errors in previous adaptation attempt.

        Args:
            sections: Original CV sections
            job_description: Target job description
            previous_adaptations: Previous adaptation that failed validation
            validation_error: The validation error message

        Returns:
            Dictionary with corrected adapted sections
        """
        from cv_matcher.latex_parser import LaTeXParser

        sections_dict = LaTeXParser.sections_to_dict(sections)

        # Create feedback prompt
        feedback_prompt = f"""Your previous CV adaptation had a LaTeX structure error.

VALIDATION ERROR:
{validation_error}

PREVIOUS ADAPTATION (with error):
{json.dumps(previous_adaptations, indent=2)}

ORIGINAL CV SECTIONS:
---
Tagline: {sections_dict['tagline']}
Work History: {sections_dict['mainbar'][:500]}...
Detailed Experiences: {sections_dict['experiences'][:500]}...
---

JOB DESCRIPTION:
{job_description}

TASK:
Fix the LaTeX structure error in your previous adaptation. The error message indicates the problem.
Common issues:
- Unmatched braces (every {{ must have a }})
- Missing or extra LaTeX commands
- Improperly escaped backslashes in JSON
- Changed LaTeX command structure (e.g., modified \\job{{}}{{}}{{}} format)
- Added or removed LaTeX commands that were/weren't in the original

CRITICAL LATEX STRUCTURE RULES:
================================
You MUST preserve the EXACT LaTeX structure from the original:
- Keep ALL LaTeX commands (\\job, \\skill, \\tag, \\section, \\subsection, etc.)
- Keep the SAME NUMBER of arguments for each command
- Keep line breaks (\\\\) in the same places
- Keep spacing commands (\\vspace, \\bigskip) unchanged
- Only modify TEXT CONTENT inside commands, never the commands themselves

Example:
- Original: \\job{{2020}}{{Company}}{{Title}}
- Correct: \\job{{2020}}{{Company}}{{Senior Title}}  (only text changed)
- WRONG: \\job{{Company}}{{Title}}{{2020}}  (argument order changed)
- WRONG: \\textbf{{Company}} - Title  (command structure changed)

Return ONLY a corrected JSON object with the SAME structure, but with the errors fixed:
{{
    "tagline": "corrected tagline",
    "mainbar": "corrected mainbar",
    "experiences": "corrected experiences",
    "general_skills": "corrected general_skills",
    "highlightbar": "corrected highlightbar",
    "explanation": "Brief explanation of what was fixed"
}}

CRITICAL:
1. Ensure all LaTeX braces are properly matched
2. Preserve ALL LaTeX commands from the original with their exact structure
3. Escape all backslashes properly for JSON (\\\\section, not \\section)
4. Do NOT add, remove, or restructure any LaTeX commands
5. Only fix the specific error while maintaining all original structure
"""

        # Call Gemini API
        try:
            response = self.model.generate_content(feedback_prompt)
            response_text = response.text
        except Exception as e:
            print(f"Error calling Gemini API for fix: {e}", file=sys.stderr)
            raise

        # Parse the response
        return self._parse_response(response_text)

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
