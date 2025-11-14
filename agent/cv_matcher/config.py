"""Configuration and constants for the CV Matcher Agent."""

import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Configuration for the CV Matcher Agent."""

    api_key: str
    model_name: str = "gemini-2.5-flash"
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
            model_name=kwargs.get("model_name", "gemini-2.5-flash"),
            cv_path=kwargs.get("cv_path", "./LaTeX/resume.tex"),
            output_path=kwargs.get("output_path", "./LaTeX/resume_adapted.tex"),
        )


# Prompt template for Gemini
ADAPTATION_PROMPT_TEMPLATE = """You are a professional CV optimization expert. \
Your task is to adapt a CV to match a specific job description while staying \
COMPLETELY GROUNDED on the existing content.

STRICT RULES:
1. DO NOT invent or add any skills, experiences, or qualifications that are not \
already in the CV
2. DO NOT exaggerate or lie about capabilities
3. ONLY reformulate, reorder, and highlight existing content to better match the \
job description
4. Keep the LaTeX formatting intact - CRITICAL: Every opening brace {{ must have \
a corresponding closing brace }}. Count your braces carefully!
5. Maintain professional tone and clarity
6. Do NOT remove or add LaTeX commands - only modify their content

CRITICAL LATEX STRUCTURE PRESERVATION RULES:
==============================================
YOU MUST PRESERVE THE EXACT LATEX STRUCTURE. Only modify the TEXT CONTENT inside \
LaTeX commands, never the commands themselves or their structure.

For example:
- ORIGINAL: \\job{{09/2020 --- Current}}{{Evooq SA Lausanne}}{{Site Reliability Engineer}}
- ALLOWED: \\job{{09/2020 --- Current}}{{Evooq SA Lausanne}}{{Senior Site Reliability Engineer}}
- FORBIDDEN: Change to \\job{{Evooq SA Lausanne}}{{Site Reliability Engineer}}{{09/2020 --- Current}}
- FORBIDDEN: Remove the \\job command and write plain text
- FORBIDDEN: Add new \\job commands that don't exist in the original

The same applies to ALL LaTeX commands:
- \\skill{{Name}}{{Level}}: Keep structure, only change Name or Level text
- \\tag{{Technology}}: Keep structure, only change Technology text
- \\section{{Title}}: Keep the command, only change Title text
- \\subsection{{Title}}: Keep the command, only change Title text
- Line breaks (\\\\): Preserve them exactly as in original
- Spacing (\\vspace, \\bigskip, etc.): Keep them unchanged

YOU CAN:
- Change text content inside LaTeX commands
- Reorder items (e.g., reorder \\job or \\skill commands)
- Emphasize certain words in descriptions

YOU CANNOT:
- Add new LaTeX commands (\\job, \\skill, \\tag, etc.) that don't exist
- Remove LaTeX commands
- Change command structure (number of arguments, braces)
- Modify spacing commands (\\vspace, \\bigskip, etc.)
- Change line breaks unless absolutely necessary
- Add or remove line breaks (\\\\) arbitrarily

ORIGINAL CV SECTIONS:
---
Tagline:
{tagline}

Work History:
{mainbar}

Detailed Experiences:
{experiences}

General Skills:
{general_skills}

Skills Sidebar:
{highlightbar}
---

JOB DESCRIPTION:
---
{job_description}
---

TASK:
Analyze the job description and adapt the CV sections to better match it. \
Focus on:
1. Rewriting the tagline to highlight the most relevant experience for this role
2. Reordering work experiences to put most relevant first (keep \\job commands structure!)
3. Reformulating experience descriptions to use keywords from the job description (keep paragraph structure!)
4. Reordering skills to highlight relevant ones first (keep \\skill and \\tag commands!)
5. Adjusting emphasis in text content only

Return ONLY a JSON object with the following structure:
{{
    "tagline": "adapted tagline here",
    "mainbar": "adapted mainbar section here",
    "experiences": "adapted experiences section here",
    "general_skills": "adapted general skills section here",
    "highlightbar": "adapted highlightbar section here",
    "explanation": "Brief explanation of changes made"
}}

CRITICAL JSON FORMATTING RULES:
1. All LaTeX backslashes MUST be escaped as double backslashes in JSON
   - Write \\\\section NOT \\section
   - Write \\\\job NOT \\job
   - Write \\\\tag NOT \\tag
   - Write \\\\skill NOT \\skill
   - Write \\\\\\\\ (four backslashes) for LaTeX line breaks (\\\\)
2. Newlines should be \\n
3. The JSON must be valid and parseable by json.loads()

EXAMPLE OF CORRECT LATEX STRUCTURE PRESERVATION:
Original: \\tag{{Kubernetes}}\\n\\tag{{Docker}}\\n\\tag{{Python}}
If job requires Docker expertise, you can reorder:
Correct: \\tag{{Docker}}\\n\\tag{{Kubernetes}}\\n\\tag{{Python}}
WRONG: \\tag{{Docker, Kubernetes, Python}} (changed structure!)
WRONG: Docker, Kubernetes, Python (removed commands!)

Make sure all LaTeX formatting is preserved exactly as in the original, \
but properly escaped for JSON."""
