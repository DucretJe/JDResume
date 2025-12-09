"""Text-based CV adapter that separates structure from content.

This approach extracts only TEXT from LaTeX commands, sends text to Gemini,
and reconstructs LaTeX with adapted text. The LaTeX structure is NEVER modified.
"""

import json
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import google.generativeai as genai
from google.generativeai.types import GenerationConfig


@dataclass
class Job:
    """Represents a job entry."""
    dates: str
    company: str
    title: str


@dataclass
class Skill:
    """Represents a skill with rating."""
    name: str
    level: int


@dataclass
class Experience:
    """Represents detailed experience description."""
    company: str  # From \subsection{...@Company}
    bullets: List[str]  # Lines separated by \\


@dataclass
class ExtractedCV:
    """All text content extracted from the CV."""
    tagline: str = ""
    jobs: List[Job] = field(default_factory=list)
    education: List[Job] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    general_skills: List[str] = field(default_factory=list)  # From \tag{}
    programming_skills: List[Skill] = field(default_factory=list)
    os_skills: List[Skill] = field(default_factory=list)
    software_skills: List[Skill] = field(default_factory=list)
    language_skills: List[Skill] = field(default_factory=list)
    hobbies: str = ""
    experiences: List[Experience] = field(default_factory=list)


class TextExtractor:
    """Extracts text content from LaTeX CV."""

    @staticmethod
    def extract_tagline(content: str) -> str:
        """Extract tagline text."""
        match = re.search(r"\\tagline\{(.+?)\}", content, re.DOTALL)
        if match:
            # Clean up line breaks
            return match.group(1).replace("\\\\ ", " ").replace("\\\\", " ").strip()
        return ""

    @staticmethod
    def extract_jobs(content: str, section_name: str = "Work history") -> List[Job]:
        """Extract job entries from a section."""
        jobs = []
        # Find the section
        section_pattern = rf"\\section.*?\{{{section_name}\}}(.*?)(?=\\section|$)"
        section_match = re.search(section_pattern, content, re.DOTALL)
        if not section_match:
            return jobs

        section_content = section_match.group(1)

        # Find all \job{dates}{company}{title} entries
        job_pattern = r"\\job\{([^}]*)\}\s*\{([^}]*)\}\s*\{([^}]*)\}"
        for match in re.finditer(job_pattern, section_content):
            jobs.append(Job(
                dates=match.group(1).strip(),
                company=match.group(2).strip(),
                title=match.group(3).strip()
            ))
        return jobs

    @staticmethod
    def extract_achievements(content: str) -> List[str]:
        """Extract achievement texts."""
        achievements = []
        for match in re.finditer(r"\\achievement\{([^}]+)\}", content):
            achievements.append(match.group(1).strip())
        return achievements

    @staticmethod
    def extract_tags(content: str) -> List[str]:
        """Extract general skill tags."""
        tags = []
        # Find General Skills section
        section_match = re.search(
            r"\\section\{General Skills\}(.*?)(?=\\section|$)",
            content,
            re.DOTALL
        )
        if section_match:
            section_content = section_match.group(1)
            for match in re.finditer(r"\\tag\{([^}]+)\}", section_content):
                tags.append(match.group(1).strip())
        return tags

    @staticmethod
    def extract_skills(content: str, section_name: str) -> List[Skill]:
        """Extract skills with ratings from a skillsection."""
        skills = []
        # Find the skillsection
        # Handle escaped & in section names
        escaped_name = section_name.replace("&", r"\\?&")
        pattern = rf"\\skillsection\{{{escaped_name}\}}(.*?)(?=\\skillsection|\\vspace|\\bigskip|$)"
        section_match = re.search(pattern, content, re.DOTALL)
        if not section_match:
            return skills

        section_content = section_match.group(1)
        for match in re.finditer(r"\\skill\{([^}]+)\}\{(\d+)\}", section_content):
            skills.append(Skill(
                name=match.group(1).strip(),
                level=int(match.group(2))
            ))
        return skills

    @staticmethod
    def extract_hobbies(content: str) -> str:
        """Extract hobbies text."""
        pattern = r"\\skillsection\{Hobbies\}(.*?)(?=\\vspace|\\skillsection|$)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            # Clean up the text
            text = match.group(1).strip()
            # Remove any remaining LaTeX commands
            text = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", "", text)
            return text.strip()
        return ""

    @staticmethod
    def extract_experiences(content: str) -> List[Experience]:
        """Extract detailed experience descriptions from Page 2."""
        experiences = []

        # Find Experiences description section
        section_match = re.search(
            r"\\section\{Experiences description\}(.*?)(?=\}\\makebody|$)",
            content,
            re.DOTALL
        )
        if not section_match:
            return experiences

        section_content = section_match.group(1)

        # Split by \subsection
        subsections = re.split(r"\\subsection\{", section_content)
        for subsection in subsections[1:]:  # Skip first empty part
            # Extract company name (everything before })
            company_match = re.match(r"([^}]+)\}", subsection)
            if not company_match:
                continue

            company = company_match.group(1).strip()
            rest = subsection[company_match.end():]

            # Extract bullet points (separated by \\)
            # Clean up the text first
            rest = re.sub(r"\\vspace\{[^}]+\}", "", rest)  # Remove \vspace
            rest = rest.strip()

            # Split by \\ and clean
            bullets = []
            for line in re.split(r"\\\\", rest):
                line = line.strip()
                if line and not line.startswith("%"):
                    # Clean up LaTeX artifacts
                    line = line.replace("\\@", "@")
                    bullets.append(line)

            if bullets:
                experiences.append(Experience(company=company, bullets=bullets))

        return experiences

    def extract_all(self, cv_content: str) -> ExtractedCV:
        """Extract all text content from CV."""
        # Split into highlightbar and mainbar sections
        highlightbar_match = re.search(
            r"\\highlightbar\{(.*?)\n\}",
            cv_content,
            re.DOTALL
        )
        highlightbar = highlightbar_match.group(1) if highlightbar_match else ""

        mainbar_match = re.search(
            r"\\mainbar\{(.*?)\}\\makebody",
            cv_content,
            re.DOTALL
        )
        mainbar = mainbar_match.group(1) if mainbar_match else ""

        return ExtractedCV(
            tagline=self.extract_tagline(cv_content),
            jobs=self.extract_jobs(mainbar, "Work history"),
            education=self.extract_jobs(mainbar, "Education"),
            achievements=self.extract_achievements(mainbar),
            general_skills=self.extract_tags(mainbar),
            programming_skills=self.extract_skills(highlightbar, "Programming"),
            os_skills=self.extract_skills(highlightbar, "Operating Systems"),
            software_skills=self.extract_skills(highlightbar, "Software & Tools"),
            language_skills=self.extract_skills(highlightbar, "Languages"),
            hobbies=self.extract_hobbies(highlightbar),
            experiences=self.extract_experiences(cv_content),
        )


# JSON Schema for text-only adaptation
TEXT_ADAPTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "tagline": {
            "type": "string",
            "description": "Adapted tagline (plain text, no LaTeX)",
        },
        "job_titles": {
            "type": "array",
            "description": "Adapted job titles in same order as original",
            "items": {"type": "string"},
        },
        "achievements": {
            "type": "array",
            "description": "Adapted achievement texts in same order",
            "items": {"type": "string"},
        },
        "general_skills": {
            "type": "array",
            "description": "Adapted skill tags (same count as original!)",
            "items": {"type": "string"},
        },
        "experience_bullets": {
            "type": "array",
            "description": "For each experience, list of adapted bullet points",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
        "explanation": {
            "type": "string",
            "description": "Brief explanation of changes made",
        },
    },
    "required": ["tagline", "job_titles", "achievements", "general_skills", "experience_bullets", "explanation"],
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
        self.extractor = TextExtractor()

    def adapt_cv(self, cv_content: str, job_description: str) -> Dict:
        """
        Adapt CV text to match job description.

        Args:
            cv_content: Original CV LaTeX content
            job_description: Target job description

        Returns:
            Dictionary with adapted text fields
        """
        # Extract text content
        extracted = self.extractor.extract_all(cv_content)

        # Build prompt with ONLY text
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
        jobs_text = "\n".join([
            f"  {i+1}. {job.title} at {job.company} ({job.dates})"
            for i, job in enumerate(extracted.jobs)
        ])

        achievements_text = "\n".join([
            f"  {i+1}. {ach}"
            for i, ach in enumerate(extracted.achievements)
        ])

        skills_text = ", ".join(extracted.general_skills)

        experiences_text = ""
        for exp in extracted.experiences:
            experiences_text += f"\n  {exp.company}:\n"
            for bullet in exp.bullets:
                experiences_text += f"    - {bullet}\n"

        return f"""You are adapting a CV to match a job description.

IMPORTANT: You must return the EXACT SAME NUMBER of items for each list.
Do NOT add or remove items - only modify the TEXT.

=== ORIGINAL CV TEXT ===

Tagline:
{extracted.tagline}

Job Positions (return {len(extracted.jobs)} titles in same order):
{jobs_text}

Achievements (return {len(extracted.achievements)} items in same order):
{achievements_text}

General Skills (return EXACTLY {len(extracted.general_skills)} tags):
{skills_text}

Experience Details (preserve company names, adapt bullet points):
{experiences_text}

=== JOB DESCRIPTION ===
{job_description}

=== INSTRUCTIONS ===
1. Adapt the TAGLINE to emphasize relevant skills for this job
2. You may slightly modify JOB TITLES to better match (e.g., "SRE" -> "Cloud Engineer")
3. Rephrase ACHIEVEMENTS to highlight relevant qualities
4. Reorder and rephrase GENERAL SKILLS to prioritize job-relevant ones
5. Adapt EXPERIENCE BULLETS to use keywords from the job description

CRITICAL RULES:
- Return EXACTLY {len(extracted.jobs)} job titles
- Return EXACTLY {len(extracted.achievements)} achievements
- Return EXACTLY {len(extracted.general_skills)} general skills
- Keep the SAME NUMBER of bullet points for each experience
- Do NOT invent new experiences or skills not in the original
- Use PLAIN TEXT only - no LaTeX commands, no special characters like & or %

Return your adaptation as JSON."""


class LaTeXReconstructor:
    """Reconstructs LaTeX with adapted text while preserving structure."""

    @staticmethod
    def escape_latex(text: str) -> str:
        """Escape special LaTeX characters."""
        # Escape in order to avoid double-escaping
        text = text.replace("\\", "\\textbackslash{}")
        text = text.replace("&", "\\&")
        text = text.replace("%", "\\%")
        text = text.replace("$", "\\$")
        text = text.replace("#", "\\#")
        text = text.replace("_", "\\_")
        text = text.replace("{", "\\{")
        text = text.replace("}", "\\}")
        text = text.replace("~", "\\textasciitilde{}")
        text = text.replace("^", "\\textasciicircum{}")
        # Restore textbackslash
        text = text.replace("\\textbackslash{}", "\\textbackslash{}")
        return text

    @staticmethod
    def safe_escape(text: str) -> str:
        """Escape only & % $ # for use inside LaTeX commands."""
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
        Apply text adaptations to the original CV.

        Args:
            original_cv: Original LaTeX content
            adaptations: Adapted text from Gemini
            extracted: Original extracted content

        Returns:
            Updated CV with adapted text
        """
        result = original_cv

        # 1. Replace tagline
        if "tagline" in adaptations:
            new_tagline = self.safe_escape(adaptations["tagline"])
            # Add line breaks for long taglines
            if len(new_tagline) > 80:
                words = new_tagline.split()
                lines = []
                current_line = []
                current_len = 0
                for word in words:
                    if current_len + len(word) > 80:
                        lines.append(" ".join(current_line))
                        current_line = [word]
                        current_len = len(word)
                    else:
                        current_line.append(word)
                        current_len += len(word) + 1
                if current_line:
                    lines.append(" ".join(current_line))
                new_tagline = "\\\\ ".join(lines)

            result = re.sub(
                r"\\tagline\{[^}]+\}",
                f"\\\\tagline{{{new_tagline}}}",
                result,
                flags=re.DOTALL
            )

        # 2. Replace job titles (only the title part, preserve dates and company)
        if "job_titles" in adaptations:
            job_titles = adaptations["job_titles"]
            for i, (orig_job, new_title) in enumerate(zip(extracted.jobs, job_titles)):
                if i < len(job_titles):
                    escaped_title = self.safe_escape(new_title)
                    # Find and replace only the title in \job{dates}{company}{title}
                    pattern = re.escape(f"\\job{{{orig_job.dates}}}\n        {{{orig_job.company}}}\n        {{{orig_job.title}}}")
                    replacement = f"\\\\job{{{orig_job.dates}}}\n        {{{orig_job.company}}}\n        {{{escaped_title}}}"
                    result = result.replace(
                        f"\\job{{{orig_job.dates}}}\n        {{{orig_job.company}}}\n        {{{orig_job.title}}}",
                        f"\\job{{{orig_job.dates}}}\n        {{{orig_job.company}}}\n        {{{escaped_title}}}"
                    )

        # 3. Replace achievements
        if "achievements" in adaptations:
            for orig_ach, new_ach in zip(extracted.achievements, adaptations["achievements"]):
                escaped_ach = self.safe_escape(new_ach)
                result = result.replace(
                    f"\\achievement{{{orig_ach}}}",
                    f"\\achievement{{{escaped_ach}}}"
                )

        # 4. Replace general skills tags
        if "general_skills" in adaptations:
            for orig_tag, new_tag in zip(extracted.general_skills, adaptations["general_skills"]):
                escaped_tag = self.safe_escape(new_tag)
                result = result.replace(
                    f"\\tag{{{orig_tag}}}",
                    f"\\tag{{{escaped_tag}}}"
                )

        # 5. Replace experience bullets
        if "experience_bullets" in adaptations:
            for exp_data in adaptations["experience_bullets"]:
                company = exp_data.get("company", "")
                new_bullets = exp_data.get("bullets", [])

                # Find matching original experience
                orig_exp = None
                for exp in extracted.experiences:
                    if company in exp.company or exp.company in company:
                        orig_exp = exp
                        break

                if orig_exp and new_bullets:
                    # Build original bullet text
                    orig_bullet_text = "\\\\\n    ".join(orig_exp.bullets) + "\\\\"

                    # Build new bullet text
                    escaped_bullets = [self.safe_escape(b) for b in new_bullets]
                    new_bullet_text = "\\\\\n    ".join(escaped_bullets) + "\\\\"

                    result = result.replace(orig_bullet_text, new_bullet_text)

        return result
