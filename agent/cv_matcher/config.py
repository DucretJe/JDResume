"""Configuration and constants for the CV Matcher Agent."""

import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Configuration for the CV Matcher Agent."""

    api_key: str
    model_name: str = "gemini-3-pro-preview"
    cv_path: str = "./LaTeX/resume.tex"
    output_path: str = "./LaTeX/resume_adapted.tex"

    @classmethod
    def from_env(cls, **kwargs) -> "AgentConfig":
        """
        Create configuration from environment variables.

        Args:
            **kwargs: Override specific configuration values

        Returns:
            AgentConfig instance
        """
        api_key = kwargs.get("api_key")
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "Gemini API key not provided. "
                "Use --api-key or set GEMINI_API_KEY environment variable."
            )

        return cls(
            api_key=api_key,
            model_name=kwargs.get("model_name", "gemini-3-pro-preview"),
            cv_path=kwargs.get("cv_path", "./LaTeX/resume.tex"),
            output_path=kwargs.get("output_path", "./LaTeX/resume_adapted.tex"),
        )


# Prompt template for Gemini
ADAPTATION_PROMPT_TEMPLATE = """You are a professional CV optimization expert.
Your task is to adapt a CV to match a specific job description.

CRITICAL: You must PRESERVE the EXACT LaTeX structure. Only modify TEXT CONTENT.

WHAT YOU CAN CHANGE:
- Text inside commands (e.g., the words in \\job{{dates}}{{company}}{{title}})
- Order of items (reorder jobs, skills, etc.)
- Wording of descriptions and bullet points

WHAT YOU MUST NOT CHANGE:
- LaTeX commands (\\job, \\section, \\tag, \\subsection, \\skill, etc.)
- Brace structure {{ and }}
- Line break commands \\\\
- Special formatting (\\vspace, \\smallskip, etc.)
- The overall document structure

=== THIS IS A 2-PAGE CV - PAGES MUST BE DIFFERENT ===

PAGE 1 = "mainbar" field:
- \\section{{Work history}} with \\job{{dates}}{{company}}{{title}} - SHORT summaries only
- \\section{{Education}} with \\job commands
- \\section{{Achievements, honours and awards}} with \\achievement commands
- \\section{{General Skills}} with \\tag{{skill}} commands
- \\section{{Wheel Chart}}
- NO detailed bullet points here - just job titles and dates!

PAGE 2 = "experiences" field:
- \\section{{Experiences description}}
- \\subsection{{Company Name}} for each company
- DETAILED bullet points with \\\\ showing responsibilities
- This is where job DESCRIPTIONS go (not in mainbar!)

STRICT RULES:
1. DO NOT invent skills or experiences not in the original CV
2. DO NOT add or remove LaTeX commands
3. COPY the LaTeX structure EXACTLY from the original
4. Only change the TEXT words, not the LaTeX syntax
5. mainbar = summaries (job titles), experiences = detailed descriptions
6. NEVER put detailed job descriptions in mainbar
7. NEVER put \\job commands in experiences

ORIGINAL CV SECTIONS:
---
Tagline:
{tagline}

PAGE 1 - mainbar (SHORT summaries with \\job commands):
{mainbar}

PAGE 2 - experiences (DETAILED descriptions with \\subsection and bullets):
{experiences}

General Skills:
{general_skills}

Skills Sidebar:
{highlightbar}
---

JOB DESCRIPTION TO MATCH:
---
{job_description}
---

TASK: Adapt the CV by:
1. Reformulating text to use keywords from the job description
2. Reordering items to prioritize relevant experience
3. Emphasizing skills that match the job requirements

Return each section with the EXACT SAME LaTeX structure as the original,
with only the text content modified to better match the job description.

REMEMBER: mainbar and experiences are SEPARATE PAGES - keep them distinct!"""
