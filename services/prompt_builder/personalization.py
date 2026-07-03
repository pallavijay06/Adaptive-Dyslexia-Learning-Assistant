"""Personalization filtering.

Responsibility: given an AdaptiveLearningPlan and a PromptType, extract
ONLY the fields that are relevant to that prompt type.

The Prompt Builder never injects every field into every prompt.
Each prompt type has its own filter rule defined here.

Adding a new prompt type requires only adding one entry to _FILTER_RULES.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from services.prompt_builder.prompt_types import PromptType

if TYPE_CHECKING:
    from services.master_decision_engine import AdaptiveLearningPlan


# ---------------------------------------------------------------------------
# Filter rule registry
# Each entry maps a PromptType to the set of field keys that are relevant.
# Keys match the flat dict produced by _flatten_plan() below.
# ---------------------------------------------------------------------------

_FILTER_RULES: dict[PromptType, set[str]] = {
    PromptType.NOTES: {
        "content_complexity",
        "reading_level",
        "worked_examples",
        "analogy_required",
        "step_by_step",
        "high_priority_concepts",
        "extra_examples",
        "revision_focus",
    },
    PromptType.VISUAL: {
        "reading_level",
        "content_complexity",
        "high_priority_concepts",
    },
    PromptType.QUIZ: {
        "quiz_length",
        "quiz_focus",
        "reading_level",
        "high_priority_concepts",
    },
    PromptType.VOCABULARY: {
        "reading_level",
        "high_priority_concepts",
    },
    PromptType.AI_TUTOR: {
        # AI Tutor is conversational — uses almost the complete plan
        "content_complexity",
        "reading_level",
        "worked_examples",
        "analogy_required",
        "step_by_step",
        "revision_required",
        "high_priority_concepts",
        "medium_priority_concepts",
        "extra_examples",
        "quiz_focus",
        "revision_focus",
        "primary_learning_mode",
        "support_learning_mode",
        "session_duration",
        "quiz_length",
        "quiz_timing",
        "ai_tutor_required",
        "teaching_style",
    },
    PromptType.RAG_CHAT: {
        "teaching_style",
        "reading_level",
        "step_by_step",
        "analogy_required",
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def filter_plan(plan: "AdaptiveLearningPlan", prompt_type: PromptType) -> dict[str, Any]:
    """Return only the AdaptiveLearningPlan fields relevant to prompt_type.

    Args:
        plan:        The full AdaptiveLearningPlan from the Master Decision Engine.
        prompt_type: The type of prompt being personalized.

    Returns:
        A flat dict containing only the fields needed for this prompt type.
    """
    flat = _flatten_plan(plan)
    allowed_keys = _FILTER_RULES.get(prompt_type, set())
    return {k: v for k, v in flat.items() if k in allowed_keys}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _flatten_plan(plan: "AdaptiveLearningPlan") -> dict[str, Any]:
    """Flatten the nested AdaptiveLearningPlan into a single-level dict.

    All field names are taken directly from the existing dataclass attributes
    in master_decision_engine.py — nothing is renamed or recomputed.
    """
    ci = plan.content_instruction
    co = plan.concept_instruction
    ls = plan.learning_strategy
    ds = plan.decision_summary

    return {
        # ContentInstruction fields
        "content_complexity":       ci.content_complexity,
        "reading_level":            ci.reading_level,
        "worked_examples":          ci.worked_examples,
        "analogy_required":         ci.analogy_required,
        "step_by_step":             ci.step_by_step,
        "revision_required":        ci.revision_required,
        "high_priority_concepts":   ci.high_priority_concepts,
        "extra_examples":           ci.extra_examples,
        "quiz_focus":               ci.quiz_focus,
        "revision_focus":           ci.revision_focus,
        # ConceptInstruction fields
        "medium_priority_concepts": co.medium_priority_concepts,
        "low_priority_concepts":    co.low_priority_concepts,
        # LearningStrategy fields
        "primary_learning_mode":    ls.primary_learning_mode,
        "support_learning_mode":    ls.support_learning_mode,
        "session_duration":         ls.session_duration,
        "quiz_length":              ls.quiz_length,
        "quiz_timing":              ls.quiz_timing,
        "ai_tutor_required":        ls.ai_tutor_required,
        # DecisionSummary fields
        "teaching_style":           ds.teaching_style,
    }
