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
        # More flexible regex that handles nested braces
        highlightbar_match = re.search(
            r"\\highlightbar\{(.*?)\n\}\s*\\mainbar",
            cv_content,
            re.DOTALL
        )
        highlightbar = highlightbar_match.group(1) if highlightbar_match else ""

        # Match mainbar content - look for content between \mainbar{ and }\makebody
        # Need to handle nested braces properly
        mainbar_match = re.search(
            r"\\mainbar\{(.*?)\}\s*\\makebody",
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
            "description": "REQUIRED: Adapted tagline text (plain text, no LaTeX). Must not be empty.",
        },
        "job_titles": {
            "type": "array",
            "description": "REQUIRED: List of adapted job titles. MUST have the same number of items as original. Do NOT return empty array!",
            "items": {"type": "string"},
        },
        "achievements": {
            "type": "array",
            "description": "REQUIRED: List of adapted achievements. MUST have the same number of items as original. Do NOT return empty array!",
            "items": {"type": "string"},
        },
        "general_skills": {
            "type": "array",
            "description": "REQUIRED: List of adapted skill tags. MUST have the same count as original. Do NOT return empty array!",
            "items": {"type": "string"},
        },
        "experience_bullets": {
            "type": "array",
            "description": "REQUIRED: For each company, list of adapted bullet points. MUST include all companies!",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string", "description": "Company name (e.g. 'Evooq', 'CIC')"},
                    "bullets": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of adapted bullet points for this company",
                    },
                },
                "required": ["company", "bullets"],
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

        # Build explicit lists for the prompt
        job_titles_list = [job.title for job in extracted.jobs]
        achievements_list = extracted.achievements
        skills_list = extracted.general_skills

        return f"""You are adapting a CV to match a job description.

=== ORIGINAL CV CONTENT ===

TAGLINE (adapt this):
"{extracted.tagline}"

JOB TITLES (you MUST return exactly {len(job_titles_list)} titles):
{json.dumps(job_titles_list, indent=2)}

ACHIEVEMENTS (you MUST return exactly {len(achievements_list)} items):
{json.dumps(achievements_list, indent=2)}

GENERAL SKILLS (you MUST return exactly {len(skills_list)} skills):
{json.dumps(skills_list, indent=2)}

EXPERIENCE DETAILS (adapt the bullet points for each company):
{experiences_text}

=== TARGET JOB DESCRIPTION ===
{job_description}

=== YOUR TASK ===

Return a JSON object with these REQUIRED fields:

1. "tagline": Adapt the tagline to emphasize relevant skills
2. "job_titles": Return {len(job_titles_list)} adapted job titles (same order)
3. "achievements": Return {len(achievements_list)} adapted achievements (same order)
4. "general_skills": Return {len(skills_list)} adapted skills (can reorder)
5. "experience_bullets": For EACH company, return adapted bullet points
6. "explanation": Brief summary of changes

EXAMPLE OUTPUT STRUCTURE:
{{
  "tagline": "Adapted tagline here...",
  "job_titles": ["Title 1", "Title 2", "Title 3"],
  "achievements": ["Achievement 1", "Achievement 2"],
  "general_skills": ["Skill1", "Skill2", "Skill3", ...],
  "experience_bullets": [
    {{"company": "Evooq", "bullets": ["Bullet 1", "Bullet 2", ...]}},
    {{"company": "CIC (Credit Analyst)", "bullets": ["Bullet 1", ...]}},
    {{"company": "CIC (Financial Counsellor)", "bullets": ["Bullet 1", ...]}}
  ],
  "explanation": "Summary of changes..."
}}

CRITICAL:
- Do NOT return empty arrays!
- Return EXACTLY the number of items specified
- Use plain text only, no special characters like & or %"""


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

            # Use regex to match tagline with any content
            result = re.sub(
                r"\\tagline\{.*?\}",
                f"\\\\tagline{{{new_tagline}}}",
                result,
                flags=re.DOTALL
            )

        # 2. Replace job titles using regex for flexibility with whitespace
        if "job_titles" in adaptations:
            job_titles = adaptations["job_titles"]
            job_replacements = 0
            for i, (orig_job, new_title) in enumerate(zip(extracted.jobs, job_titles)):
                if i < len(job_titles):
                    escaped_title = self.safe_escape(new_title)
                    # Use regex to match job with flexible whitespace
                    # Match: \job{dates}{company}{title} with any whitespace between
                    pattern = (
                        r"\\job\{" + re.escape(orig_job.dates) + r"\}\s*"
                        r"\{" + re.escape(orig_job.company) + r"\}\s*"
                        r"\{" + re.escape(orig_job.title) + r"\}"
                    )
                    replacement = (
                        f"\\\\job{{{orig_job.dates}}}\n"
                        f"        {{{orig_job.company}}}\n"
                        f"        {{{escaped_title}}}"
                    )
                    new_result, n = re.subn(pattern, replacement, result)
                    if n > 0:
                        job_replacements += n
                        result = new_result
                    else:
                        print(f"   ⚠️ Could not find job: {orig_job.title}", file=sys.stderr)
            print(f"   📝 Replaced {job_replacements} job titles", file=sys.stderr)

        # 3. Replace achievements using regex
        if "achievements" in adaptations:
            ach_replacements = 0
            for orig_ach, new_ach in zip(extracted.achievements, adaptations["achievements"]):
                escaped_ach = self.safe_escape(new_ach)
                pattern = r"\\achievement\{" + re.escape(orig_ach) + r"\}"
                replacement = f"\\\\achievement{{{escaped_ach}}}"
                new_result, n = re.subn(pattern, replacement, result)
                if n > 0:
                    ach_replacements += n
                    result = new_result
                else:
                    print(f"   ⚠️ Could not find achievement: {orig_ach[:50]}...", file=sys.stderr)
            print(f"   📝 Replaced {ach_replacements} achievements", file=sys.stderr)

        # 4. Replace general skills tags using regex
        if "general_skills" in adaptations:
            tag_replacements = 0
            for orig_tag, new_tag in zip(extracted.general_skills, adaptations["general_skills"]):
                escaped_tag = self.safe_escape(new_tag)
                pattern = r"\\tag\{" + re.escape(orig_tag) + r"\}"
                replacement = f"\\\\tag{{{escaped_tag}}}"
                new_result, n = re.subn(pattern, replacement, result)
                if n > 0:
                    tag_replacements += n
                    result = new_result
                else:
                    print(f"   ⚠️ Could not find tag: {orig_tag}", file=sys.stderr)
            print(f"   📝 Replaced {tag_replacements} skill tags", file=sys.stderr)

        # 5. Replace experience bullets using regex
        if "experience_bullets" in adaptations:
            exp_replacements = 0
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
                    # Use regex to find the subsection and replace bullet content
                    # First, escape the company name for regex
                    escaped_company = re.escape(orig_exp.company)

                    # Find the subsection pattern and capture its content
                    subsection_pattern = (
                        r"(\\subsection\{" + escaped_company + r"\})"
                        r"(.*?)"
                        r"(?=\\subsection|\\vspace\{5mm\}\s*\\subsection|\}\s*\\makebody)"
                    )

                    def replace_subsection(match):
                        subsection_header = match.group(1)
                        # Build new content with bullets
                        escaped_bullets = [self.safe_escape(b) for b in new_bullets]
                        new_content = "\n    " + "\\\\\n    ".join(escaped_bullets) + "\\\\"
                        return subsection_header + new_content

                    new_result, n = re.subn(subsection_pattern, replace_subsection, result, flags=re.DOTALL)
                    if n > 0:
                        exp_replacements += n
                        result = new_result
                    else:
                        print(f"   ⚠️ Could not find experience section: {orig_exp.company}", file=sys.stderr)
                elif not orig_exp:
                    print(f"   ⚠️ No matching experience found for: {company}", file=sys.stderr)
            print(f"   📝 Replaced {exp_replacements} experience sections", file=sys.stderr)

        return result
