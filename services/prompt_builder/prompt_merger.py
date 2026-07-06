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

_DESC_PRIORITY = (
    "These instructions are derived from the learner's historical behaviour and "
    "represent the highest-priority guidance for this response."
)

_DESC_CONTENT = (
    "These concepts should receive greater emphasis because previous learning "
    "sessions indicate they require additional attention or reinforcement."
)

_DESC_STRATEGY = (
    "These recommendations describe how today's learning session should be "
    "organized according to the learner's preferred learning behaviour."
)

_DESC_VISUAL = (
    "These instructions shape how educational content should be represented visually "
    "so the learner can understand it quickly and clearly."
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
        PromptType.VISUAL:      ["pedagogical", "content", "visual"],
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
        "visual":      _build_visual_block,
    }

    blocks: list[str] = []
    priority_block = _build_priority_block(prompt_type)
    if priority_block:
        blocks.append(priority_block)

    for name in _blocks_for(prompt_type):
        block = builders[name](filtered, prompt_type)
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

def _build_priority_block(prompt_type: PromptType) -> str:
    return (
        f"{SEP}\nADAPTIVE PERSONALIZATION PRIORITY\n{SEP}\n{_DESC_PRIORITY}\n\n"
        f"Treat these adaptive instructions as the highest-priority behavioural specification for this response. "
        f"These instructions are generated from the learner's historical learning behaviour. "
        f"Whenever any instruction below conflicts with the generic prompt, follow these adaptive instructions. "
        f"These recommendations override generic defaults and should be applied throughout the response. "
        f"Do not mention learner profiling, learner history, or personalization to the learner. "
        f"Silently adapt teaching behaviour based on these instructions and do not revert to generic behaviour later in the response."
    )


def _build_pedagogical_block(f: dict[str, Any], prompt_type: PromptType) -> str:
    lines: list[str] = []

    if f.get("teaching_style"):
        lines.append(
            f"Teaching behaviour: adapt the explanation to the learner's preferred style of {f['teaching_style']}."
        )
    if f.get("reading_level"):
        reading_level = str(f['reading_level']).lower()
        if reading_level == "easy":
            lines.append("Use vocabulary suitable for approximately a Grade-5 learner. Avoid technical jargon and explain unfamiliar terms immediately in simple language.")
        elif reading_level == "standard":
            lines.append("Use clear, accessible language suitable for a general learner. Keep explanations direct and avoid unnecessary complexity.")
        elif reading_level == "advanced":
            lines.append("Use appropriate technical terminology and assume the learner can follow moderately complex explanations.")
        else:
            lines.append(f"Write explanations at a {reading_level} reading level using clear, direct language.")
    if f.get("content_complexity"):
        lines.append(
            f"Adjust the complexity to {str(f['content_complexity']).lower()} so the explanation stays appropriately challenging."
        )
    if f.get("worked_examples"):
        worked_examples = str(f['worked_examples']).lower()
        if worked_examples == "many":
            lines.append("Provide several worked examples and concrete applications to reinforce the idea.")
        elif worked_examples == "moderate":
            lines.append("Provide a moderate number of worked examples so the learner sees enough support without overload.")
        else:
            lines.append("Provide a small number of worked examples and keep the explanation concise.")
    if "step_by_step" in f and f["step_by_step"]:
        lines.append("Present one concept at a time. Complete one explanation before introducing the next. Do not skip intermediate reasoning.")
    if "analogy_required" in f and f["analogy_required"]:
        lines.append("Introduce a familiar real-life analogy before explaining difficult concepts, then immediately connect it back to the academic idea.")
    if "revision_required" in f and f["revision_required"]:
        lines.append("Revisit earlier concepts briefly and reinforce revision points before advancing to new material.")

    if prompt_type == PromptType.NOTES:
        lines.append("Use plain, accessible language with short sentences, clear headings, and bullet points.")
    elif prompt_type == PromptType.VISUAL:
        lines.append("Organize information visually, use simple labels, and minimize dense text so the learner can quickly grasp relationships.")
    elif prompt_type == PromptType.QUIZ:
        lines.append("Frame the explanation in a way that supports assessment clarity and keeps the learner focused on the core idea.")
    elif prompt_type == PromptType.AI_TUTOR:
        lines.append("Respond conversationally, check understanding, and guide the learner with questions, examples, and encouragement.")

    lines.append("Silently adapt the behaviour without mentioning learner profiling or adaptive instructions.")
    lines.append("Apply these adaptive instructions consistently throughout the entire response and maintain the personalized teaching behaviour until the response is complete.")

    if not lines:
        return ""

    return f"{SEP}\nPEDAGOGICAL INSTRUCTIONS\n{SEP}\n{_DESC_PEDAGOGICAL}\n\n" + "\n".join(lines)


def _build_content_block(f: dict[str, Any], prompt_type: PromptType) -> str:
    lines: list[str] = []

    high = f.get("high_priority_concepts") or []
    if high:
        lines.append(
            "Spend significantly more explanation time on weak concepts and explain them in simpler, more concrete language: " + ", ".join(high)
        )

    medium = f.get("medium_priority_concepts") or []
    if medium:
        lines.append("Give moderate attention to these concepts and connect them to the main ideas: " + ", ".join(medium))

    extra = f.get("extra_examples") or []
    if extra:
        lines.append("Generate additional examples for weak concepts and make the examples explicit: " + ", ".join(extra))

    revision_focus = f.get("revision_focus") or []
    if revision_focus:
        lines.append("Generate additional revision questions around weak concepts and revisit them deliberately: " + ", ".join(revision_focus))

    lines.append("Refer back to weak concepts when introducing related ideas.")
    lines.append("Reduce emphasis on mastered concepts without ignoring them, and briefly reinforce them before moving to weaker areas.")

    if not lines:
        return ""

    return f"{SEP}\nCONTENT PRIORITIES\n{SEP}\n{_DESC_CONTENT}\n\n" + "\n".join(lines)


def _build_visual_block(f: dict[str, Any], prompt_type: PromptType) -> str:
    if prompt_type != PromptType.VISUAL:
        return ""

    lines = [
        "Represent concepts graphically whenever possible.",
        "Prefer diagrams and hierarchical organization over long paragraphs.",
        "Keep node labels short, meaningful, and easy to scan.",
        "Minimize unnecessary descriptive text and reduce visual clutter.",
        "Group closely related concepts together and maintain a shallow, readable hierarchy.",
        "Clearly show relationships between concepts and highlight the most important ideas.",
        "Keep the visual representation easy to understand at a glance.",
    ]

    return f"{SEP}\nVISUAL PRESENTATION\n{SEP}\n{_DESC_VISUAL}\n\n" + "\n".join(lines)


def _build_quiz_block(f: dict[str, Any], prompt_type: PromptType) -> str:
    """Dedicated QUIZ SETTINGS block — quiz-specific fields only."""
    lines: list[str] = []

    quiz_focus = f.get("quiz_focus") or []
    if quiz_focus:
        lines.append("Prioritize weak concepts and emphasize these quiz-focus concepts: " + ", ".join(quiz_focus))
    if f.get("quiz_length"):
        lines.append(f"Approximately follow the recommended quiz length of {f['quiz_length']} questions instead of overwhelming the learner.")
    if f.get("quiz_timing"):
        lines.append(f"Use the recommended quiz timing of {f['quiz_timing']} and keep the assessment well-paced.")
    lines.append("Gradually increase difficulty across the quiz so the learner is challenged without becoming discouraged.")
    lines.append("Keep questions clear, targeted, and aligned to the learner's needs.")

    if not lines:
        return ""

    return f"{SEP}\nQUIZ SETTINGS\n{SEP}\n{_DESC_QUIZ}\n\n" + "\n".join(lines)


def _build_strategy_block(f: dict[str, Any], prompt_type: PromptType) -> str:
    lines: list[str] = []

    if f.get("primary_learning_mode"):
        primary = str(f['primary_learning_mode']).lower()
        if primary == "visual":
            lines.append("Organize information visually, encourage visual thinking, and minimize long text.")
        elif primary == "auditory":
            lines.append("Use spoken explanation cues, repetition, and verbal scaffolding to support learning.")
        elif primary == "kinaesthetic":
            lines.append("Use hands-on examples, movement cues, and practical activities to reinforce understanding.")
        else:
            lines.append(f"Prefer a {primary} learning approach and make the teaching style consistent with it.")
    if f.get("support_learning_mode"):
        lines.append(f"Use the support mode of {f['support_learning_mode']} for reinforcement and clarification.")
    if f.get("session_duration"):
        lines.append(f"Keep the session pacing appropriate for a {f['session_duration']}-minute learning session.")
    if "ai_tutor_required" in f and f["ai_tutor_required"]:
        lines.append("Do not immediately reveal answers. Guide the learner using questions, encourage active thinking, and confirm understanding before progressing.")
        lines.append("If confusion persists, explain the idea through a different approach rather than repeating the same explanation.")
        lines.append("Encourage curiosity and follow-up questions while keeping the tutoring supportive and focused.")

    if not lines:
        return ""

    return f"{SEP}\nAI TUTOR BEHAVIOUR\n{SEP}\n{_DESC_STRATEGY}\n\n" + "\n".join(lines)
