"""Revision Service.

Single responsibility: given a list of revision topics, generate
dyslexia-friendly revision notes via the LLM router.

Input:  revision_topics (list[str])
Output: revision notes (str)

This service does NOT:
  - decide which topics need revision
  - compute learner confidence
  - modify learner profiles
  - perform adaptive decisions

Those responsibilities belong to the Understanding Decision Engine and the
Master Decision Engine.
"""

from __future__ import annotations

from services.llm_router import generate_content, LLMRouterError


class RevisionServiceError(RuntimeError):
    """Raised when revision note generation fails."""


def generate_revision_notes(revision_topics: list[str]) -> str:
    """Generate dyslexia-friendly revision notes for the given topics.

    Args:
        revision_topics: Non-empty list of concept names to revise.

    Returns:
        Plain-text revision notes, one section per topic.

    Raises:
        ValueError: If revision_topics is empty.
        RevisionServiceError: If the LLM fails to generate notes.
    """
    if not revision_topics:
        raise ValueError("revision_topics cannot be empty.")

    prompt = _build_prompt(revision_topics)
    try:
        return generate_content(prompt, max_tokens=1200)
    except LLMRouterError as exc:
        raise RevisionServiceError(f"Revision note generation failed: {exc}") from exc
    except Exception as exc:
        raise RevisionServiceError(f"Revision note generation failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(topics: list[str]) -> str:
    topic_list = "\n".join(f"- {t}" for t in topics)
    return (
        "You are a dyslexia-friendly learning assistant.\n"
        "Generate revision notes for the following topics.\n\n"
        "Rules:\n"
        "- Explain ONLY the topics listed below. Do not introduce new concepts.\n"
        "- Use simple, clear language. Short sentences (10 words max).\n"
        "- Write 3 to 5 sentences per topic.\n"
        "- Refresh the learner's memory. Do not teach from scratch.\n"
        "- Use a plain example only if it helps understanding.\n"
        "- Keep each topic section concise.\n"
        "- Separate topics with a line of dashes: --------------------------------\n"
        "- Return plain text only. No HTML. No Markdown symbols.\n"
        "- Start each section with the topic name on its own line.\n\n"
        f"Topics to revise:\n{topic_list}\n\n"
        "Revision Notes:"
    )
