"""
CV Job Matcher Agent
Uses Gemini API to adapt a LaTeX CV to match a specific job description.
"""

__version__ = "0.1.0"

from cv_matcher.config import AgentConfig
from cv_matcher.gemini_adapter import GeminiAdapter
from cv_matcher.latex_parser import LaTeXParser
from cv_matcher.latex_writer import LaTeXWriter

__all__ = [
    "AgentConfig",
    "GeminiAdapter",
    "LaTeXParser",
    "LaTeXWriter",
]
