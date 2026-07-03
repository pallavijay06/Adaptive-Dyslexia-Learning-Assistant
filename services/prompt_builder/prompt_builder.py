"""Prompt Builder — Personalization Layer.

Public API:
    build_prompt(context: PromptContext) -> str

Architecture:
    AdaptiveLearningPlan
        ↓
    PromptContext
        ↓
    personalization.filter_plan()   ← extracts only relevant fields
        ↓
    prompt_merger.merge()           ← builds only the blocks needed for this
                                       prompt type, then appends original
        ↓
    personalized prompt string

Guarantees:
    - The original prompt is NEVER modified.
    - No learner modelling is performed here.
    - No decisions are made here.
    - No LLM calls are made here.
    - Only structured personalization blocks are prepended.
"""

from __future__ import annotations

from services.prompt_builder.prompt_context import PromptContext
from services.prompt_builder.personalization import filter_plan
from services.prompt_builder.prompt_merger import merge


def build_prompt(context: PromptContext) -> str:
    """Personalize an existing prompt using the AdaptiveLearningPlan.

    Args:
        context: A PromptContext containing the prompt type, the
                 AdaptiveLearningPlan, and the original prompt string.

    Returns:
        The personalized prompt string — structured instruction blocks
        prepended to the original prompt, which is passed through unchanged.
    """
    filtered = filter_plan(context.plan, context.prompt_type)
    return merge(filtered, context.original_prompt, context.prompt_type)
