"""Text-based CV adapter using position-based replacement.

This approach extracts text AND their positions from LaTeX commands,
sends text to Gemini, then replaces by direct string slicing (no regex matching).
"""

import json
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import google.generativeai as genai
from google.generativeai.types import GenerationConfig


@dataclass
class TextSpan:
    """A piece of text with its position in the original file."""
    text: str
    start: int  # Start position in original file
    end: int    # End position in original file


@dataclass
class JobSpan:
    """A job entry with position of the title."""
    dates: str
    company: str
    title: TextSpan  # Only the title is replaceable


@dataclass
class ExtractedCV:
    """All text content extracted from the CV with positions."""
    tagline: TextSpan = None
    jobs: List[JobSpan] = field(default_factory=list)
    achievements: List[TextSpan] = field(default_factory=list)
    general_skills: List[TextSpan] = field(default_factory=list)


class PositionExtractor:
    """Extracts text content with positions from LaTeX CV."""

    def extract_tagline(self, content: str) -> TextSpan:
        """Extract tagline text with position."""
        match = re.search(r"\\tagline\{([^}]+)\}", content, re.DOTALL)
        if match:
            return TextSpan(
                text=match.group(1).strip(),
                start=match.start(1),
                end=match.end(1)
            )
        return None

    def extract_jobs(self, content: str) -> List[JobSpan]:
        """Extract job entries with title positions."""
        jobs = []
        # Find all \job{dates}{company}{title} entries
        # We need to capture the position of the title specifically
        pattern = r"\\job\{([^}]*)\}\s*\{([^}]*)\}\s*\{([^}]*)\}"
        for match in re.finditer(pattern, content):
            jobs.append(JobSpan(
                dates=match.group(1).strip(),
                company=match.group(2).strip(),
                title=TextSpan(
                    text=match.group(3).strip(),
                    start=match.start(3),
                    end=match.end(3)
                )
            ))
        return jobs

    def extract_achievements(self, content: str) -> List[TextSpan]:
        """Extract achievement texts with positions."""
        achievements = []
        for match in re.finditer(r"\\achievement\{([^}]+)\}", content):
            achievements.append(TextSpan(
                text=match.group(1).strip(),
                start=match.start(1),
                end=match.end(1)
            ))
        return achievements

    def extract_tags(self, content: str) -> List[TextSpan]:
        """Extract general skill tags with positions."""
        tags = []
        # Find all \tag{} commands
        for match in re.finditer(r"\\tag\{([^}]+)\}", content):
            tags.append(TextSpan(
                text=match.group(1).strip(),
                start=match.start(1),
                end=match.end(1)
            ))
        return tags

    def extract_all(self, cv_content: str) -> ExtractedCV:
        """Extract all text content with positions."""
        return ExtractedCV(
            tagline=self.extract_tagline(cv_content),
            jobs=self.extract_jobs(cv_content),
            achievements=self.extract_achievements(cv_content),
            general_skills=self.extract_tags(cv_content),
        )


# JSON Schema for text-only adaptation
TEXT_ADAPTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "tagline": {
            "type": "string",
            "description": "Adapted tagline text (plain text, no LaTeX).",
        },
        "job_titles": {
            "type": "array",
            "description": "List of adapted job titles. MUST have same count as original.",
            "items": {"type": "string"},
        },
        "achievements": {
            "type": "array",
            "description": "List of adapted achievements. MUST have same count as original.",
            "items": {"type": "string"},
        },
        "general_skills": {
            "type": "array",
            "description": "List of adapted skill tags. MUST have same count as original.",
            "items": {"type": "string"},
        },
        "explanation": {
            "type": "string",
            "description": "Brief explanation of changes made",
        },
    },
    "required": ["tagline", "job_titles", "achievements", "general_skills", "explanation"],
}


class TextBasedAdapter:
    """Adapter that works with text only, never touching LaTeX structure."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """Initialize the adapter."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name,
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                response_schema=TEXT_ADAPTATION_SCHEMA,
            ),
        )
        self.extractor = PositionExtractor()

    def adapt_cv(self, cv_content: str, job_description: str) -> Dict:
        """Adapt CV text to match job description."""
        extracted = self.extractor.extract_all(cv_content)
        prompt = self._build_prompt(extracted, job_description)

        print("📤 Sending text adaptation request to Gemini...", file=sys.stderr)

        try:
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            return result
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            raise

    def _build_prompt(self, extracted: ExtractedCV, job_description: str) -> str:
        """Build prompt with extracted text."""
        job_titles = [job.title.text for job in extracted.jobs]
        achievements = [ach.text for ach in extracted.achievements]
        skills = [tag.text for tag in extracted.general_skills]
        tagline = extracted.tagline.text if extracted.tagline else ""

        return f"""You are adapting a CV to match a job description.

=== ORIGINAL CV CONTENT ===

TAGLINE:
"{tagline}"

JOB TITLES ({len(job_titles)} items - return exactly this many):
{json.dumps(job_titles, indent=2)}

ACHIEVEMENTS ({len(achievements)} items - return exactly this many):
{json.dumps(achievements, indent=2)}

GENERAL SKILLS ({len(skills)} items - return exactly this many):
{json.dumps(skills, indent=2)}

=== TARGET JOB DESCRIPTION ===
{job_description}

=== YOUR TASK ===

Adapt the CV content to better match the job description.
Return a JSON with:

1. "tagline": Adapted tagline emphasizing relevant skills
2. "job_titles": {len(job_titles)} adapted job titles (same order as input)
3. "achievements": {len(achievements)} adapted achievements (same order)
4. "general_skills": {len(skills)} adapted skills
5. "explanation": Brief summary of changes

CRITICAL RULES:
- Return EXACTLY the same number of items as input
- Do NOT return empty arrays
- Use plain text only (no & % $ # characters)
- Make meaningful adaptations to match the job"""


class PositionBasedReconstructor:
    """Reconstructs LaTeX by direct position-based replacement."""

    @staticmethod
    def safe_escape(text: str) -> str:
        """Escape special LaTeX characters."""
        text = text.replace("&", "\\&")
        text = text.replace("%", "\\%")
        text = text.replace("$", "\\$")
        text = text.replace("#", "\\#")
        return text

    def apply_adaptations(
        self,
        original_cv: str,
        adaptations: Dict,
        extracted: ExtractedCV
    ) -> str:
        """
        Apply text adaptations using position-based replacement.

        This works by collecting all replacements, sorting them by position
        (reverse order), and applying them from end to start so positions
        don't shift.
        """
        # Collect all replacements as (start, end, new_text) tuples
        replacements: List[Tuple[int, int, str]] = []

        # 1. Tagline
        if extracted.tagline and "tagline" in adaptations:
            new_tagline = self.safe_escape(adaptations["tagline"])
            replacements.append((
                extracted.tagline.start,
                extracted.tagline.end,
                new_tagline
            ))
            print(f"   📝 Tagline: '{extracted.tagline.text[:30]}...' -> '{new_tagline[:30]}...'", file=sys.stderr)

        # 2. Job titles
        if "job_titles" in adaptations:
            job_titles = adaptations["job_titles"]
            for i, (job, new_title) in enumerate(zip(extracted.jobs, job_titles)):
                escaped_title = self.safe_escape(new_title)
                replacements.append((
                    job.title.start,
                    job.title.end,
                    escaped_title
                ))
                print(f"   📝 Job {i+1}: '{job.title.text}' -> '{escaped_title}'", file=sys.stderr)

        # 3. Achievements
        if "achievements" in adaptations:
            for i, (ach, new_ach) in enumerate(zip(extracted.achievements, adaptations["achievements"])):
                escaped_ach = self.safe_escape(new_ach)
                replacements.append((
                    ach.start,
                    ach.end,
                    escaped_ach
                ))
                print(f"   📝 Achievement {i+1}: '{ach.text[:30]}...' -> '{escaped_ach[:30]}...'", file=sys.stderr)

        # 4. General skills
        if "general_skills" in adaptations:
            for i, (tag, new_tag) in enumerate(zip(extracted.general_skills, adaptations["general_skills"])):
                escaped_tag = self.safe_escape(new_tag)
                replacements.append((
                    tag.start,
                    tag.end,
                    escaped_tag
                ))
                if tag.text != new_tag:
                    print(f"   📝 Skill: '{tag.text}' -> '{escaped_tag}'", file=sys.stderr)

        # Sort replacements by position (reverse order - end to start)
        replacements.sort(key=lambda x: x[0], reverse=True)

        # Apply replacements from end to start
        result = original_cv
        for start, end, new_text in replacements:
            result = result[:start] + new_text + result[end:]

        print(f"\n   ✅ Applied {len(replacements)} replacements", file=sys.stderr)
        return result


# Backwards compatibility alias
class LaTeXReconstructor(PositionBasedReconstructor):
    """Alias for backwards compatibility."""
    pass
