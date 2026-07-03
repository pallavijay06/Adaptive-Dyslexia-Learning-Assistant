"""Prompt merger.

Responsibility: convert a filtered personalization dict into structured
instruction blocks, then prepend them to the original prompt.

Two improvements over the previous version:
  1. Only the blocks relevant to the given PromptType are generated.
  2. Every block heading is followed by a short contextual description
     so the LLM understands why the instructions exist.

The original prompt is NEVER modified — it is appended verbatim at the end.

Block selection per PromptType:
    NOTES       → PEDAGOGICAL INSTRUCTIONS + CONTENT PRIORITIES
    VISUAL      → PEDAGOGICAL INSTRUCTIONS + CONTENT PRIORITIES
    QUIZ        → CONTENT PRIORITIES + QUIZ SETTINGS
    VOCABULARY  → CONTENT PRIORITIES
    AI_TUTOR    → PEDAGOGICAL INSTRUCTIONS + CONTENT PRIORITIES + LEARNING STRATEGY
    RAG_CHAT    → PEDAGOGICAL INSTRUCTIONS + CONTENT PRIORITIES
"""

from __future__ import annotations

from typing import Any

from services.prompt_builder.prompt_types import PromptType

SEP = "-" * 57

# ---------------------------------------------------------------------------
# Contextual descriptions — one per block heading
# ---------------------------------------------------------------------------

_DESC_PEDAGOGICAL = (
    "These instructions define how the educational content should be explained "
    "based on the learner's historical understanding, comprehension level, and "
    "learning needs."
)

_DESC_CONTENT = (
    "These concepts should receive greater emphasis because previous learning "
    "sessions indicate they require additional attention or reinforcement."
)

_DESC_STRATEGY = (
    "These recommendations describe how today's learning session should be "
    "organized according to the learner's preferred learning behaviour."
)

_DESC_QUIZ = (
    "These instructions personalize the quiz by adjusting its focus, length, "
    "and timing according to the learner's current learning state."
)

# ---------------------------------------------------------------------------
# Block selection rules per PromptType
# ---------------------------------------------------------------------------
# Each entry is an ordered list of block builder functions to call.
# Adding a new PromptType only requires adding one entry here.

def _blocks_for(prompt_type: PromptType) -> list[str]:
    """Return the ordered list of block names to generate for this prompt type."""
    rules: dict[PromptType, list[str]] = {
        PromptType.NOTES:       ["pedagogical", "content"],
        PromptType.VISUAL:      ["pedagogical", "content"],
        PromptType.QUIZ:        ["content", "quiz"],
        PromptType.VOCABULARY:  ["content"],
        PromptType.AI_TUTOR:    ["pedagogical", "content", "strategy"],
        PromptType.RAG_CHAT:    ["pedagogical", "content"],
    }
    return rules.get(prompt_type, ["pedagogical", "content"])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def merge(filtered: dict[str, Any], original_prompt: str, prompt_type: PromptType) -> str:
    """Prepend personalization blocks to the original prompt.

    Args:
        filtered:        Output of personalization.filter_plan() — only the
                         fields relevant to this prompt type.
        original_prompt: The existing prompt string, passed through unchanged.
        prompt_type:     Determines which blocks are generated.

    Returns:
        The final personalized prompt string.
    """
    builders = {
        "pedagogical": _build_pedagogical_block,
        "content":     _build_content_block,
        "strategy":    _build_strategy_block,
        "quiz":        _build_quiz_block,
    }

    blocks: list[str] = []
    for name in _blocks_for(prompt_type):
        block = builders[name](filtered)
        if block:
            blocks.append(block)

    if not blocks:
        return original_prompt

    personalization_section = "\n\n".join(blocks)
    return (
        f"{personalization_section}\n\n"
        f"{SEP}\n"
        f"ORIGINAL PROMPT\n"
        f"{SEP}\n"
        f"{original_prompt}"
    )


# ---------------------------------------------------------------------------
# Block builders
# ---------------------------------------------------------------------------

def _build_pedagogical_block(f: dict[str, Any]) -> str:
    lines: list[str] = []

    if f.get("teaching_style"):
        lines.append(f"Teaching Style: {f['teaching_style']}")
    if f.get("reading_level"):
        lines.append(f"Reading Level: {f['reading_level']}")
    if f.get("content_complexity"):
        lines.append(f"Content Complexity: {f['content_complexity']}")
    if f.get("worked_examples"):
        lines.append(f"Worked Examples: {f['worked_examples']}")
    if "step_by_step" in f:
        lines.append(f"Step-by-Step Explanation: {'Yes' if f['step_by_step'] else 'No'}")
    if "analogy_required" in f:
        lines.append(f"Use Analogies: {'Yes' if f['analogy_required'] else 'No'}")
    if "revision_required" in f:
        lines.append(f"Revision Required: {'Yes' if f['revision_required'] else 'No'}")

    if not lines:
        return ""

    return f"{SEP}\nPEDAGOGICAL INSTRUCTIONS\n{SEP}\n{_DESC_PEDAGOGICAL}\n\n" + "\n".join(lines)


def _build_content_block(f: dict[str, Any]) -> str:
    lines: list[str] = []

    high = f.get("high_priority_concepts") or []
    if high:
        lines.append("High Priority Concepts: " + ", ".join(high))

    medium = f.get("medium_priority_concepts") or []
    if medium:
        lines.append("Medium Priority Concepts: " + ", ".join(medium))

    extra = f.get("extra_examples") or []
    if extra:
        lines.append("Concepts Needing Extra Examples: " + ", ".join(extra))

    revision_focus = f.get("revision_focus") or []
    if revision_focus:
        lines.append("Revision Focus Concepts: " + ", ".join(revision_focus))

    if not lines:
        return ""

    return f"{SEP}\nCONTENT PRIORITIES\n{SEP}\n{_DESC_CONTENT}\n\n" + "\n".join(lines)


def _build_quiz_block(f: dict[str, Any]) -> str:
    """Dedicated QUIZ SETTINGS block — quiz-specific fields only."""
    lines: list[str] = []

    quiz_focus = f.get("quiz_focus") or []
    if quiz_focus:
        lines.append("Quiz Focus Concepts: " + ", ".join(quiz_focus))
    if f.get("quiz_length"):
        lines.append(f"Quiz Length: {f['quiz_length']} questions")
    if f.get("quiz_timing"):
        lines.append(f"Quiz Timing: {f['quiz_timing']}")

    if not lines:
        return ""

    return f"{SEP}\nQUIZ SETTINGS\n{SEP}\n{_DESC_QUIZ}\n\n" + "\n".join(lines)


def _build_strategy_block(f: dict[str, Any]) -> str:
    lines: list[str] = []

    if f.get("primary_learning_mode"):
        lines.append(f"Primary Learning Mode: {f['primary_learning_mode']}")
    if f.get("support_learning_mode"):
        lines.append(f"Support Learning Mode: {f['support_learning_mode']}")
    if f.get("session_duration"):
        lines.append(f"Session Duration: {f['session_duration']} minutes")
    if "ai_tutor_required" in f:
        lines.append(f"AI Tutor Required: {'Yes' if f['ai_tutor_required'] else 'No'}")

    if not lines:
        return ""

    return f"{SEP}\nLEARNING STRATEGY\n{SEP}\n{_DESC_STRATEGY}\n\n" + "\n".join(lines)
