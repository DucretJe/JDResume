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

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-pro"):
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
            print(f"Error parsing JSON response: {e}", file=sys.stderr)
            print(f"Response was: {response_text}", file=sys.stderr)
            raise ValueError(f"Failed to parse Gemini response: {e}")

        return adaptations
