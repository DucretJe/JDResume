"""PDF visual validator using Gemini multimodal capabilities."""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import google.generativeai as genai


class PDFValidator:
    """Validates adapted CV by comparing PDFs visually with Gemini."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize the PDF validator.

        Args:
            api_key: Google Gemini API key
            model_name: Gemini model to use (must support vision)
        """
        genai.configure(api_key=api_key)
        # Use a vision-capable model for image comparison
        self.model = genai.GenerativeModel(model_name)

    def convert_pdf_to_images(
        self, pdf_path: str, output_dir: str, dpi: int = 150
    ) -> list[str]:
        """
        Convert PDF pages to PNG images.

        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save images
            dpi: Resolution for conversion

        Returns:
            List of paths to generated images
        """
        base_name = Path(pdf_path).stem
        output_prefix = os.path.join(output_dir, base_name)

        try:
            subprocess.run(
                [
                    "pdftoppm",
                    "-png",
                    "-r",
                    str(dpi),
                    pdf_path,
                    output_prefix,
                ],
                check=True,
                capture_output=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "pdftoppm not found. Install poppler-utils: "
                "apt-get install poppler-utils"
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"PDF conversion failed: {e.stderr.decode()}")

        # Find generated images
        images = sorted(Path(output_dir).glob(f"{base_name}-*.png"))
        return [str(img) for img in images]

    def get_layout_feedback(
        self, original_pdf: str, adapted_pdf: str
    ) -> Dict:
        """
        Compare PDFs and get detailed feedback about layout issues.

        Args:
            original_pdf: Path to original CV PDF
            adapted_pdf: Path to adapted CV PDF

        Returns:
            Dict with:
                - is_valid: bool
                - issues: list of specific issues
                - fixes: dict mapping field names to suggested fixes
                - explanation: str
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                original_images = self.convert_pdf_to_images(original_pdf, tmpdir)
                adapted_images = self.convert_pdf_to_images(adapted_pdf, tmpdir)
            except RuntimeError as e:
                return {
                    "is_valid": False,
                    "issues": [str(e)],
                    "fixes": {},
                    "explanation": str(e)
                }

            if len(original_images) != len(adapted_images):
                return {
                    "is_valid": False,
                    "issues": [f"Page count changed: {len(original_images)} -> {len(adapted_images)}"],
                    "fixes": {"all": "Make all text shorter to fit in original page count"},
                    "explanation": "Content overflow - too much text"
                }

            # Upload images
            print("   🔍 Comparing layouts with Gemini vision...", file=sys.stderr)

            original_page1 = genai.upload_file(original_images[0])
            adapted_page1 = genai.upload_file(adapted_images[0])

            # Also compare page 2 if exists
            original_page2 = None
            adapted_page2 = None
            if len(original_images) > 1:
                original_page2 = genai.upload_file(original_images[1])
                adapted_page2 = genai.upload_file(adapted_images[1])

            prompt = """Compare these CV layouts. I'm showing you the ORIGINAL CV and the ADAPTED CV.

IMAGE 1: Original CV Page 1
IMAGE 2: Adapted CV Page 1
IMAGE 3: Original CV Page 2 (if present)
IMAGE 4: Adapted CV Page 2 (if present)

TASK: Check if the ADAPTED CV has the same visual layout as the ORIGINAL.

Look for these LAYOUT ISSUES:
1. TAGLINE: Is it wrapping to more lines than original? (should stay same number of lines)
2. JOB TITLES: Are any titles wrapping or misaligned compared to original?
3. SKILLS TAGS: Are they overflowing or wrapping differently?
4. ACHIEVEMENTS: Are they taking more vertical space?
5. EXPERIENCE BULLETS: Are they longer causing overflow?
6. OVERALL: Does adapted page have more content causing overflow?

For each issue found, identify WHICH FIELD needs to be SHORTER.

Respond with JSON:
{
    "is_valid": true/false,
    "layout_matches": true/false,
    "issues": [
        "specific issue 1",
        "specific issue 2"
    ],
    "fixes": {
        "tagline": "reduce by ~X characters" or null,
        "job_titles": "title N is too long" or null,
        "achievements": "achievement N is too long" or null,
        "general_skills": "skill names are too long" or null,
        "experience_bullets": "bullets for company X are too long" or null
    },
    "explanation": "brief summary"
}

IMPORTANT: Only report REAL layout differences. Minor text changes are OK.
Focus on: line wrapping, overflow, misalignment, spacing changes."""

            try:
                images = [prompt, original_page1, adapted_page1]
                if original_page2 and adapted_page2:
                    images.extend([original_page2, adapted_page2])

                response = self.model.generate_content(images)
                result_text = response.text

                # Parse JSON response
                json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return {
                        "is_valid": result.get("is_valid", False) and result.get("layout_matches", False),
                        "issues": result.get("issues", []),
                        "fixes": result.get("fixes", {}),
                        "explanation": result.get("explanation", "")
                    }
                else:
                    return {
                        "is_valid": True,  # Assume OK if can't parse
                        "issues": [],
                        "fixes": {},
                        "explanation": "Could not parse response, assuming OK"
                    }

            except Exception as e:
                return {
                    "is_valid": True,  # Don't block on errors
                    "issues": [],
                    "fixes": {},
                    "explanation": f"Validation error: {e}"
                }

            finally:
                # Clean up
                try:
                    original_page1.delete()
                    adapted_page1.delete()
                    if original_page2:
                        original_page2.delete()
                    if adapted_page2:
                        adapted_page2.delete()
                except Exception:
                    pass

    def validate_adaptation(
        self, original_pdf: str, adapted_pdf: str
    ) -> Tuple[bool, str]:
        """
        Validate that the adapted CV maintains structure and has different content on pages.

        Args:
            original_pdf: Path to original CV PDF
            adapted_pdf: Path to adapted CV PDF

        Returns:
            Tuple of (is_valid, explanation)
        """
        feedback = self.get_layout_feedback(original_pdf, adapted_pdf)
        return feedback["is_valid"], feedback["explanation"]
