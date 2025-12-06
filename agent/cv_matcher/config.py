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
Your task is to adapt a CV to match a specific job description while staying
COMPLETELY GROUNDED on the existing content.

STRICT RULES:
1. DO NOT invent or add any skills, experiences, or qualifications not in the CV
2. DO NOT exaggerate or lie about capabilities
3. ONLY reformulate, reorder, and highlight existing content
4. Keep LaTeX formatting intact - every {{ must have a matching }}
5. Maintain professional tone and clarity
6. Do NOT remove or add LaTeX commands - only modify their content

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
Analyze the job description and adapt the CV sections to better match it.
Focus on:
1. Rewriting the tagline to highlight relevant experience for this role
2. Reordering or emphasizing work experiences matching job requirements
3. Reformulating experience descriptions using keywords from the job description
4. Highlighting relevant skills that match the job
5. Adjusting general skills tags to prioritize relevant technologies

LATEX FORMATTING RULES:
1. Preserve all LaTeX commands exactly (\\section, \\job, \\tag, \\skill, etc.)
2. Every opening brace {{ must have a closing brace }}
3. Use \\\\ for line breaks in LaTeX
4. Special characters: use \\& for &, \\% for %, \\$ for $, \\# for #

Provide adapted content for each section, keeping the original LaTeX structure."""
