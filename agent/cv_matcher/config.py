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
4. Keep the LaTeX formatting intact
5. Maintain professional tone and clarity

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
2. Reordering or emphasizing work experiences that match the job requirements
3. Reformulating experience descriptions to use keywords from the job description
4. Highlighting relevant skills that match the job
5. Adjusting the general skills tags to prioritize relevant technologies

Return ONLY a JSON object with the following structure:
{{
    "tagline": "adapted tagline here",
    "mainbar": "adapted mainbar section here",
    "experiences": "adapted experiences section here",
    "general_skills": "adapted general skills section here",
    "highlightbar": "adapted highlightbar section here",
    "explanation": "Brief explanation of changes made"
}}

Make sure all LaTeX formatting is preserved exactly as in the original."""
