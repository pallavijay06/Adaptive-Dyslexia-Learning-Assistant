"""Simplification service for dyslexia-friendly content generation."""

from __future__ import annotations

import logging

from services.llm_router import generate_content, LLMRouterError

logger = logging.getLogger(__name__)


class SimplificationError(RuntimeError):
    """Raised when simplification fails."""


def simplify_text(text: str, user_id: int | None = None) -> str:
    """Simplify text for students with dyslexia.

    When user_id is provided, retrieves the AdaptiveLearningPlan for that
    learner and uses the Prompt Builder to prepend a personalization layer
    before the original prompt. If personalization fails for any reason,
    the original prompt is used unchanged — the learner always receives
    Simplified Notes.

    Produces:
    - Short sentences
    - Bullet points
    - Simple vocabulary
    - Dyslexia-friendly formatting

    Args:
        text:    Text to simplify.
        user_id: Authenticated learner ID. Optional — omit for anonymous use.

    Returns:
        Simplified content.

    Raises:
        SimplificationError: If simplification fails.
    """
    if not text or not text.strip():
        raise SimplificationError("Text cannot be empty.")

    # ------------------------------------------------------------------ #
    # Step 1 — Build the original prompt (UNCHANGED — never modified)     #
    # ------------------------------------------------------------------ #
    original_prompt = (
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

    logger.info("[Simplification] Original prompt (first 120 chars): %s", original_prompt[:120])

    # ------------------------------------------------------------------ #
    # Step 2 — Attempt Prompt Builder personalization                     #
    # Fallback to original_prompt on ANY failure — never blocks the user  #
    # ------------------------------------------------------------------ #
    prompt_to_send = _build_personalized_prompt(original_prompt, user_id)

    logger.info(
        "[Simplification] Sending %s prompt to LLM (%d chars)",
        "personalized" if prompt_to_send is not original_prompt else "original",
        len(prompt_to_send),
    )
    print("\n" + "=" * 80)
    print("SIMPLIFIED NOTES PERSONALIZED PROMPT")
    print("=" * 80)
    print(prompt_to_send)
    print("=" * 80 + "\n")

    try:
        # Simplification can be longer — allow up to 1200 tokens
        return generate_content(prompt_to_send, max_tokens=1200)
    except Exception as exc:
        raise SimplificationError(f"Simplification failed: {exc}") from exc


def _build_personalized_prompt(original_prompt: str, user_id: int | None) -> str:
    """Retrieve AdaptiveLearningPlan and call build_prompt().

    Returns the personalized prompt on success, or original_prompt on any
    failure so the caller is always guaranteed a usable prompt string.
    """
    if user_id is None:
        logger.info("[Simplification] No user_id — skipping personalization.")
        return original_prompt

    try:
        # Step 3 — Retrieve AdaptiveLearningPlan via Master Decision Engine
        from services.master_decision_engine import get_adaptive_learning_plan
        plan = get_adaptive_learning_plan(user_id, document_concepts=[])

        # Step 4 — Construct PromptContext
        from services.prompt_builder import build_prompt, PromptContext, PromptType
        context = PromptContext(
            prompt_type=PromptType.NOTES,
            plan=plan,
            original_prompt=original_prompt,
        )

        # Step 5 — Call build_prompt() and receive the personalized prompt
        personalized = build_prompt(context)

        logger.info(
            "[Simplification] Personalization succeeded for user_id=%s "
            "(overall_confidence=%.2f, teaching_style=%s)",
            user_id,
            plan.overall_confidence,
            plan.decision_summary.teaching_style,
        )
        return personalized

    except Exception as exc:
        # Graceful fallback — personalization must never break simplification
        logger.warning(
            "[Simplification] Personalization failed for user_id=%s — "
            "falling back to original prompt. Reason: %s",
            user_id,
            exc,
        )
        return original_prompt