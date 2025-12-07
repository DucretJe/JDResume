"""PDF visual validator using Gemini multimodal capabilities."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Tuple

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
        with tempfile.TemporaryDirectory() as tmpdir:
            # Convert PDFs to images
            print("📸 Converting PDFs to images...", file=sys.stderr)
            try:
                original_images = self.convert_pdf_to_images(original_pdf, tmpdir)
                adapted_images = self.convert_pdf_to_images(adapted_pdf, tmpdir)
            except RuntimeError as e:
                return False, str(e)

            if len(original_images) != len(adapted_images):
                return False, (
                    f"Page count mismatch: original has {len(original_images)} pages, "
                    f"adapted has {len(adapted_images)} pages"
                )

            if len(adapted_images) < 2:
                return False, "Expected at least 2 pages in the CV"

            # Upload images to Gemini
            print("🔍 Analyzing pages with Gemini...", file=sys.stderr)

            # Load images
            original_page1 = genai.upload_file(original_images[0])
            original_page2 = genai.upload_file(original_images[1])
            adapted_page1 = genai.upload_file(adapted_images[0])
            adapted_page2 = genai.upload_file(adapted_images[1])

            prompt = """You are validating an adapted CV. I'm showing you 4 images:
1. Original CV Page 1
2. Original CV Page 2
3. Adapted CV Page 1
4. Adapted CV Page 2

VALIDATION CRITERIA:
1. Page 1 should contain: Job titles, Education, Skills tags, Wheel chart
2. Page 2 should contain: DETAILED job descriptions with bullet points
3. Page 1 and Page 2 should have DIFFERENT content (not duplicated)
4. The adapted version should maintain the same STRUCTURE as original
5. Text content can change but layout should be similar

CRITICAL CHECK: Are the two pages of the ADAPTED CV showing DIFFERENT content?
- Page 1 = Summary (job titles, education, skills)
- Page 2 = Details (job descriptions with bullet points)

If both pages of the adapted CV show the same content, that's a FAILURE.

Respond with JSON:
{
    "is_valid": true/false,
    "pages_are_different": true/false,
    "structure_preserved": true/false,
    "issues": ["list of issues if any"],
    "explanation": "brief explanation"
}"""

            try:
                response = self.model.generate_content(
                    [prompt, original_page1, original_page2, adapted_page1, adapted_page2]
                )
                result_text = response.text

                # Parse response
                import json
                import re

                # Extract JSON from response
                json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    is_valid = result.get("is_valid", False)
                    explanation = result.get("explanation", "No explanation provided")

                    if not result.get("pages_are_different", True):
                        return False, "FAILURE: Both pages have the same content"

                    if not result.get("structure_preserved", True):
                        return False, f"Structure not preserved: {explanation}"

                    return is_valid, explanation
                else:
                    return False, f"Could not parse validation response: {result_text}"

            except Exception as e:
                return False, f"Validation error: {str(e)}"

            finally:
                # Clean up uploaded files
                try:
                    original_page1.delete()
                    original_page2.delete()
                    adapted_page1.delete()
                    adapted_page2.delete()
                except Exception:
                    pass  # Ignore cleanup errors
