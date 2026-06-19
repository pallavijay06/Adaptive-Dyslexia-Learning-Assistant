"""Simplification service for dyslexia-friendly content generation."""

from __future__ import annotations

from services.llm_router import generate_content, LLMRouterError


class SimplificationError(RuntimeError):
    """Raised when simplification fails."""


def simplify_text(text: str) -> str:
    """Simplify text for students with dyslexia.
    
    Produces:
    - Short sentences
    - Bullet points
    - Simple vocabulary
    - Dyslexia-friendly formatting
    
    Args:
        text: Text to simplify
        
    Returns:
        Simplified content
        
    Raises:
        SimplificationError: If simplification fails
    """
    if not text or not text.strip():
        raise SimplificationError("Text cannot be empty.")
    
    prompt = (
        "Simplify this content for students with dyslexia.\n\n"
        "Rules:\n"
        "- Use SHORT sentences (10 words max per sentence)\n"
        "- Use bullet points for lists\n"
        "- Use SIMPLE vocabulary\n"
        "- Explain difficult concepts in simple terms\n"
        "- Keep all important information\n"
        "- Use clear headings written in plain text\n"
        "- Return plain text only\n"
        "- Do not use HTML tags\n"
        "- Do not use Markdown headings or formatting symbols\n"
        "- Do not use ` ``` `, `###`, `**`, or similar syntax\n"
        "- Add extra line breaks between sections\n"
        "- Make it engaging and encouraging\n\n"
        f"Content to simplify:\n\n{text.strip()}"
    )
    
    try:
        return generate_content(prompt)
    except Exception as exc:
        raise SimplificationError(f"Simplification failed: {exc}") from exc