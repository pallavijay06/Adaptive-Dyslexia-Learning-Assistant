"""Master Decision Engine.

Purpose: Decision Orchestration — NOT evidence recomputation.

Answers one question:
  "Considering all learner decisions, what is the best complete personalized
   learning experience for this learner right now?"

Inputs:  outputs of the three sub-engines (already decided).
Output:  one AdaptiveLearningPlan dataclass.

The Master NEVER:
  - recomputes learner metrics
  - recomputes EBD evidence
  - generates prompts or adaptive content
  - modifies individual sub-engine decisions

The Master ONLY:
  1. Merges the three decisions into one unified plan
  2. Computes overall confidence from sub-engine confidences
  3. Resolves conflicts between sub-engine decisions
  4. Builds a structured ContentInstruction object
  5. Builds the adaptive learning flow (ordered step sequence)
  6. Builds a structured PromptInstructionSet for the future Prompt Builder
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from services.understanding_decision_engine import (
    UnderstandingDecision,
    get_understanding_decision,
)
from services.content_personalization_engine import (
    ContentPersonalizationDecision,
    get_content_personalization_decision,
)
from services.learning_strategy_engine import (
    LearningStrategyDecision,
    get_learning_strategy_decision,
)
from services.recommendation_engine import RecommendationEngine
from database.db import get_learner_profile


# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContentInstruction:
    """Structured instructions for how the uploaded document should be adapted."""
    content_complexity: str          # Very Simple / Simple / Moderate / Advanced
    reading_level: str               # Easy / Standard / Advanced
    worked_examples: str             # Few / Moderate / Many
    analogy_required: bool
    step_by_step: bool
    revision_required: bool
    high_priority_concepts: list[str]
    extra_examples: list[str]        # concepts that need extra worked examples
    quiz_focus: list[str]            # concepts that need additional quiz questions
    revision_focus: list[str]        # concepts that require revision emphasis


@dataclass(frozen=True)
class ConceptInstruction:
    """Structured concept emphasis instructions derived from the document."""
    high_priority_concepts: list[str]
    medium_priority_concepts: list[str]
    low_priority_concepts: list[str]
    extra_examples: list[str]
    quiz_focus: list[str]
    revision_focus: list[str]


@dataclass(frozen=True)
class LearningStrategy:
    """Structured session strategy derived from the Learning Strategy Engine."""
    primary_learning_mode: str | None
    support_learning_mode: str | None
    session_duration: int            # minutes
    quiz_length: int                 # number of questions
    quiz_timing: str                 # e.g. "After Learning", "After Revision"
    ai_tutor_required: bool


@dataclass(frozen=True)
class LearningFlowStep:
    """One structured step in the adaptive learning flow."""
    step: int
    action: str                              # revision | learning_mode | extra_examples | quiz | ai_tutor | stem_support
    mode: Optional[str] = None               # learning_mode steps
    concepts: Optional[list[str]] = None     # revision / extra_examples steps
    revision_topics: Optional[list[str]] = None  # revision step — topics to revise
    reason: Optional[str] = None             # revision step — why revision is required
    quiz_length: Optional[int] = None        # quiz step
    quiz_timing: Optional[str] = None        # quiz step
    focus_concepts: Optional[list[str]] = None  # quiz step
    enabled: Optional[bool] = None           # ai_tutor step


@dataclass(frozen=True)
class DecisionSummary:
    """Concise learner-plan summary derived from the Master Decision output."""
    teaching_style: str          # e.g. "Very Simple, Step-by-Step, Many Examples"
    focus_concepts: list[str]    # high-priority concepts
    learning_strategy: str       # primary learning mode
    revision_required: bool
    session_duration: str        # e.g. "20 minutes"
    overall_confidence: float
    comprehension_level: str | None
    recommended_learning_mode: str | None


@dataclass(frozen=True)
class PromptInstructionSet:
    """Structured data consumed by the future Prompt Builder. No natural language."""
    content_instruction: dict[str, Any]
    concept_instruction: dict[str, Any]
    learning_strategy: dict[str, Any]
    quiz_instruction: dict[str, Any]
    revision_instruction: dict[str, Any]
    session_instruction: dict[str, Any]


@dataclass(frozen=True)
class AdaptiveLearningPlan:
    """The single unified output of the Master Decision Engine."""
    content_instruction: ContentInstruction
    concept_instruction: ConceptInstruction
    learning_strategy: LearningStrategy
    adaptive_learning_flow: list[LearningFlowStep]  # ordered step sequence
    overall_confidence: float            # 0.0 – 1.0
    decision_summary: DecisionSummary
    prompt_instruction_set: PromptInstructionSet


# ---------------------------------------------------------------------------
# Conflict resolution rule constants
# ---------------------------------------------------------------------------

# When revision_required=True, a Revision step is always inserted BEFORE
# the primary learning mode, regardless of what the strategy engine decided.
_REVISION_STEP = "Revision"

# Quiz timing labels that trigger pre-quiz revision insertion
_QUIZ_TIMING_AFTER_REVISION = "After Revision"

# Confidence weight for each sub-engine when computing overall confidence.
# Understanding is weighted highest because it drives content adaptation.
_CONF_WEIGHT_UNDERSTANDING   = 0.40
_CONF_WEIGHT_CONTENT         = 0.30
_CONF_WEIGHT_STRATEGY        = 0.30

# A sub-engine whose confidence is below this threshold is considered
# "low confidence" and its weight is halved in the overall calculation.
_LOW_CONFIDENCE_THRESHOLD = 0.30


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_adaptive_learning_plan(
    user_id: int,
    document_concepts: list[str],
    is_stem_document: bool = False,
) -> AdaptiveLearningPlan:
    """Orchestrate all three sub-engines and return one unified AdaptiveLearningPlan.

    Args:
        user_id: The authenticated learner's ID.
        document_concepts: Concept names extracted from the uploaded document
            by the parser pipeline. Passed directly to the Content
            Personalization Engine — the Master does not extract concepts.
        is_stem_document: When True, a STEM Support step is automatically
            inserted into the adaptive flow. Determined by the existing
            STEM detector (backend/stem/detector.py) — never by the frontend.
    """
    understanding = get_understanding_decision(user_id, document_concepts=document_concepts)
    content       = get_content_personalization_decision(user_id, document_concepts)
    strategy      = get_learning_strategy_decision(user_id)
    return _orchestrate(user_id, understanding, content, strategy, is_stem_document=is_stem_document)


def get_adaptive_learning_plan_from_decisions(
    understanding: UnderstandingDecision,
    content: ContentPersonalizationDecision,
    strategy: LearningStrategyDecision,
    is_stem_document: bool = False,
) -> AdaptiveLearningPlan:
    """Pure-function variant — accepts pre-computed sub-engine decisions.

    Use this when the caller has already loaded the three decisions
    (e.g. to avoid redundant DB reads in a batch pipeline).
    """
    return _orchestrate(
        None,
        understanding,
        content,
        strategy,
        is_stem_document=is_stem_document,
    )


# ---------------------------------------------------------------------------
# Orchestration core
# ---------------------------------------------------------------------------

def _orchestrate(
    user_id: int | None,
    understanding: UnderstandingDecision,
    content: ContentPersonalizationDecision,
    strategy: LearningStrategyDecision,
    is_stem_document: bool = False,
) -> AdaptiveLearningPlan:
    """Six-step orchestration. No evidence recomputation."""

    # 1. Merge — collect all fields needed downstream
    merged = _merge(understanding, content, strategy)

    # 2. Overall confidence
    overall_confidence = _compute_overall_confidence(
        understanding.confidence,
        content.confidence,
        strategy.confidence,
    )

    # 3. Resolve conflicts — returns a conflict resolution context
    conflict_ctx = _resolve_conflicts(understanding, content, strategy)

    # 4. Build ContentInstruction
    content_instruction = _build_content_instruction(understanding, content)

    # 5. Build ConceptInstruction
    concept_instruction = _build_concept_instruction(content)

    # 6. Build LearningStrategy
    learning_strategy = _build_learning_strategy(strategy)

    # 7. Build adaptive learning flow (uses conflict context)
    adaptive_flow = _build_adaptive_flow(understanding, content, strategy, conflict_ctx, is_stem_document)

    # 8. Build DecisionSummary
    decision_summary = _build_decision_summary(
        user_id,
        understanding,
        content,
        strategy,
        overall_confidence,
    )

    # 9. Build PromptInstructionSet
    prompt_instruction_set = _build_prompt_instruction_set(
        content_instruction, concept_instruction, learning_strategy,
        understanding, content, strategy, adaptive_flow,
    )

    return AdaptiveLearningPlan(
        content_instruction=content_instruction,
        concept_instruction=concept_instruction,
        learning_strategy=learning_strategy,
        adaptive_learning_flow=adaptive_flow,
        overall_confidence=overall_confidence,
        decision_summary=decision_summary,
        prompt_instruction_set=prompt_instruction_set,
    )


# ---------------------------------------------------------------------------
# Step 1 — Merge
# ---------------------------------------------------------------------------

def _merge(
    understanding: UnderstandingDecision,
    content: ContentPersonalizationDecision,
    strategy: LearningStrategyDecision,
) -> dict[str, Any]:
    """Collect all sub-engine fields into one flat dict for downstream steps.
    No modification of any individual decision value.
    """
    return {
        # Understanding
        "content_complexity":    understanding.content_complexity,
        "reading_level":         understanding.reading_level,
        "worked_examples":       understanding.worked_examples,
        "analogy_required":      understanding.analogy_required,
        "step_by_step":          understanding.step_by_step,
        "revision_required":     understanding.revision_required,
        # Content
        "high_priority_concepts":   content.high_priority_concepts,
        "medium_priority_concepts": content.medium_priority_concepts,
        "low_priority_concepts":    content.low_priority_concepts,
        "extra_examples":           content.extra_examples,
        "quiz_focus":               content.quiz_focus,
        "revision_focus":           content.revision_focus,
        # Strategy
        "primary_learning_mode":       strategy.primary_learning_mode,
        "support_learning_mode":       strategy.support_learning_mode,
        "ai_tutor_required":           strategy.ai_tutor_required,
        "recommended_session_duration": strategy.recommended_session_duration,
        "recommended_quiz_length":     strategy.recommended_quiz_length,
        "recommended_quiz_timing":     strategy.recommended_quiz_timing,
    }


# ---------------------------------------------------------------------------
# Step 2 — Overall confidence
# ---------------------------------------------------------------------------

def _compute_overall_confidence(
    understanding_conf: float,
    content_conf: float,
    strategy_conf: float,
) -> float:
    """Weighted average of sub-engine confidences.

    A sub-engine with confidence below _LOW_CONFIDENCE_THRESHOLD has its
    weight halved so it does not drag down the overall score unfairly when
    it simply lacks data (e.g. new learner with no quiz history).
    """
    weights = {
        "understanding": _CONF_WEIGHT_UNDERSTANDING,
        "content":       _CONF_WEIGHT_CONTENT,
        "strategy":      _CONF_WEIGHT_STRATEGY,
    }
    values = {
        "understanding": understanding_conf,
        "content":       content_conf,
        "strategy":      strategy_conf,
    }

    # Halve weight for low-confidence engines
    for key, val in values.items():
        if val < _LOW_CONFIDENCE_THRESHOLD:
            weights[key] *= 0.5

    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0

    weighted_sum = sum(values[k] * weights[k] for k in weights)
    return round(weighted_sum / total_weight, 2)


# ---------------------------------------------------------------------------
# Step 3 — Conflict resolution
# ---------------------------------------------------------------------------

def _resolve_conflicts(
    understanding: UnderstandingDecision,
    content: ContentPersonalizationDecision,
    strategy: LearningStrategyDecision,
) -> dict[str, Any]:
    """Apply deterministic conflict resolution rules.

    Returns a context dict consumed by _build_adaptive_flow.
    Does NOT modify any sub-engine decision object.

    Rules (in priority order):
      R1. If revision_required=True AND quiz_timing != "After Revision"
          → insert Revision step before primary mode.
      R2. If revision_required=True AND revision_focus is non-empty
          → apply revision emphasis only to revision_focus concepts.
      R3. If extra_examples is non-empty
          → insert Extra Examples step after primary mode.
      R4. If worked_examples="Many" AND extra_examples is empty
          → apply "Many" examples globally (no concept-specific step needed).
      R5. If ai_tutor_required=True
          → AI Tutor step is placed AFTER quiz (post-quiz clarification).
      R6. If support_learning_mode is None AND content has high_priority_concepts
          → no structural change; high-priority concepts are handled via
             content_instruction emphasis only.
    """
    ctx: dict[str, Any] = {
        "insert_revision_step":    False,
        "revision_concepts":       [],
        "global_many_examples":    False,
        "ai_tutor_after_quiz":     False,
        "conflict_notes":          [],
    }

    # R1 — Revision step insertion
    if understanding.revision_required:
        ctx["insert_revision_step"] = True
        if strategy.recommended_quiz_timing != _QUIZ_TIMING_AFTER_REVISION:
            ctx["conflict_notes"].append(
                "CONFLICT R1 resolved: revision_required=True but quiz_timing was "
                f"'{strategy.recommended_quiz_timing}' — Revision step inserted before "
                "primary mode and quiz_timing treated as After Revision."
            )
        else:
            ctx["conflict_notes"].append(
                "R1: revision_required=True and quiz_timing='After Revision' — consistent."
            )

    # R2 — Revision concept scoping
    if understanding.revision_required and content.revision_focus:
        ctx["revision_concepts"] = list(content.revision_focus)
        ctx["conflict_notes"].append(
            f"R2: Revision emphasis scoped to {len(content.revision_focus)} concept(s): "
            f"{content.revision_focus}."
        )
    elif understanding.revision_required:
        ctx["conflict_notes"].append(
            "R2: revision_required=True but no revision_focus concepts — "
            "revision applies globally."
        )

    # R4 — Global many-examples flag (no concept-specific step needed)
    if understanding.worked_examples == "Many" and not content.extra_examples:
        ctx["global_many_examples"] = True
        ctx["conflict_notes"].append(
            "R4: worked_examples='Many' with no specific extra_examples — "
            "many examples applied globally via content_instruction."
        )

    # R5 — AI Tutor placement
    if strategy.ai_tutor_required:
        ctx["ai_tutor_after_quiz"] = True
        ctx["conflict_notes"].append(
            "R5: ai_tutor_required=True — AI Tutor placed after Quiz for post-quiz clarification."
        )

    return ctx


# ---------------------------------------------------------------------------
# Step 4 — ContentInstruction
# ---------------------------------------------------------------------------

def _build_content_instruction(
    understanding: UnderstandingDecision,
    content: ContentPersonalizationDecision,
) -> ContentInstruction:
    """Combine understanding and content decisions into one structured object.
    No modification of individual decision values.
    """
    return ContentInstruction(
        content_complexity=understanding.content_complexity,
        reading_level=understanding.reading_level,
        worked_examples=understanding.worked_examples,
        analogy_required=understanding.analogy_required,
        step_by_step=understanding.step_by_step,
        revision_required=understanding.revision_required,
        high_priority_concepts=list(content.high_priority_concepts),
        extra_examples=list(content.extra_examples),
        quiz_focus=list(content.quiz_focus),
        revision_focus=list(content.revision_focus),
    )


# ---------------------------------------------------------------------------
# Step 4b — ConceptInstruction
# ---------------------------------------------------------------------------

def _build_concept_instruction(
    content: ContentPersonalizationDecision,
) -> ConceptInstruction:
    return ConceptInstruction(
        high_priority_concepts=list(content.high_priority_concepts),
        medium_priority_concepts=list(content.medium_priority_concepts),
        low_priority_concepts=list(content.low_priority_concepts),
        extra_examples=list(content.extra_examples),
        quiz_focus=list(content.quiz_focus),
        revision_focus=list(content.revision_focus),
    )


# ---------------------------------------------------------------------------
# Step 4c — LearningStrategy
# ---------------------------------------------------------------------------

def _build_learning_strategy(strategy: LearningStrategyDecision) -> LearningStrategy:
    return LearningStrategy(
        primary_learning_mode=strategy.primary_learning_mode,
        support_learning_mode=strategy.support_learning_mode,
        session_duration=strategy.recommended_session_duration,
        quiz_length=strategy.recommended_quiz_length,
        quiz_timing=strategy.recommended_quiz_timing,
        ai_tutor_required=strategy.ai_tutor_required,
    )


# ---------------------------------------------------------------------------
# Step 5 — Adaptive learning flow
# ---------------------------------------------------------------------------

def _build_adaptive_flow(
    understanding: UnderstandingDecision,
    content: ContentPersonalizationDecision,
    strategy: LearningStrategyDecision,
    conflict_ctx: dict[str, Any],
    is_stem_document: bool = False,
) -> list[LearningFlowStep]:
    """Construct the complete ordered learning sequence as structured step objects.

    Base template (all steps optional except Primary Mode and Quiz):

        [Revision]                  ← only if revision_required=True
        Primary Learning Mode       ← always present
        [Support Learning Mode]     ← only if support_learning_mode is set
        [STEM Support]              ← only if is_stem_document=True
        Quiz                        ← always present
        [AI Tutor]                  ← only if ai_tutor_required=True

    The conflict context (from _resolve_conflicts) drives which optional
    steps are included and in what order.
    """
    flow: list[LearningFlowStep] = []
    step_num = 1

    # Step 1 — Revision (before everything else if required)
    # Rule 3: only add a Revision step when revision_required=True AND
    # revision_topics is non-empty.  The Understanding Decision Engine already
    # enforces this (Rule 2), but we guard here as well so the flow can never
    # contain a Revision step with an empty topic list.
    if conflict_ctx["insert_revision_step"] and understanding.revision_topics:
        revision_topics = list(understanding.revision_topics)
        revision_reason = next(
            (line for line in understanding.reasoning if line.startswith("Revision required:")),
            None,
        )
        flow.append(LearningFlowStep(
            step=step_num,
            action="revision",
            concepts=list(conflict_ctx["revision_concepts"]) or None,
            revision_topics=revision_topics,
            reason=revision_reason,
        ))
        step_num += 1

    # Step 2 — Primary learning mode (always present)
    primary = strategy.primary_learning_mode or "Simplified Notes"
    flow.append(LearningFlowStep(
        step=step_num,
        action="learning_mode",
        mode=primary,
    ))
    step_num += 1

    # Step 3 — Support learning mode (if available)
    if strategy.support_learning_mode:
        flow.append(LearningFlowStep(
            step=step_num,
            action="learning_mode",
            mode=strategy.support_learning_mode,
        ))
        step_num += 1

    # Step 4 — STEM Support (only when the document contains STEM content)
    if is_stem_document:
        flow.append(LearningFlowStep(
            step=step_num,
            action="stem_support",
            mode="STEM Support",
        ))
        step_num += 1

    # Step 5 — Quiz (always present)
    flow.append(LearningFlowStep(
        step=step_num,
        action="quiz",
        quiz_length=strategy.recommended_quiz_length,
        quiz_timing=strategy.recommended_quiz_timing,
        focus_concepts=list(content.quiz_focus) if content.quiz_focus else None,
    ))
    step_num += 1

    # Step 6 — AI Tutor (after quiz, for post-quiz clarification)
    if conflict_ctx["ai_tutor_after_quiz"]:
        flow.append(LearningFlowStep(
            step=step_num,
            action="ai_tutor",
            enabled=True,
        ))

    return flow


# ---------------------------------------------------------------------------
# Step 6 — DecisionSummary
# ---------------------------------------------------------------------------

def _build_decision_summary(
    user_id: int | None,
    understanding: UnderstandingDecision,
    content: ContentPersonalizationDecision,
    strategy: LearningStrategyDecision,
    overall_confidence: float,
) -> DecisionSummary:
    """Concise learner-plan summary. All values sourced from existing decisions."""
    style_parts = [understanding.content_complexity]
    if understanding.step_by_step:
        style_parts.append("Step-by-Step")
    if understanding.worked_examples == "Many":
        style_parts.append("Many Examples")
    elif understanding.analogy_required:
        style_parts.append("Analogy-Based")

    comprehension_level = None
    recommended_learning_mode = None
    if user_id is not None:
        profile = get_learner_profile(user_id)
        comprehension_level = profile.comprehension_level if profile else None
        recommended_learning_mode = RecommendationEngine.recommend_learning_mode(user_id)

    return DecisionSummary(
        teaching_style=", ".join(style_parts),
        focus_concepts=list(content.high_priority_concepts),
        learning_strategy=strategy.primary_learning_mode or "Simplified Notes",
        revision_required=understanding.revision_required,
        session_duration=f"{strategy.recommended_session_duration} minutes",
        overall_confidence=overall_confidence,
        comprehension_level=comprehension_level,
        recommended_learning_mode=recommended_learning_mode,
    )


# ---------------------------------------------------------------------------
# Step 6 — PromptInstructionSet
# ---------------------------------------------------------------------------

def _build_prompt_instruction_set(
    content_instruction: ContentInstruction,
    concept_instruction: ConceptInstruction,
    learning_strategy: LearningStrategy,
    understanding: UnderstandingDecision,
    content: ContentPersonalizationDecision,
    strategy: LearningStrategyDecision,
    adaptive_flow: list[str],
) -> PromptInstructionSet:
    """Build a structured data object for the future Prompt Builder.

    All values are structured data — no natural language, no prompt text.
    The Prompt Builder will later convert these into LLM prompt instructions.
    """
    return PromptInstructionSet(
        content_instruction={
            "content_complexity":  content_instruction.content_complexity,
            "reading_level":       content_instruction.reading_level,
            "worked_examples":     content_instruction.worked_examples,
            "analogy_required":    content_instruction.analogy_required,
            "step_by_step":        content_instruction.step_by_step,
            "revision_required":   content_instruction.revision_required,
        },
        concept_instruction={
            "high_priority_concepts":   concept_instruction.high_priority_concepts,
            "medium_priority_concepts": concept_instruction.medium_priority_concepts,
            "low_priority_concepts":    concept_instruction.low_priority_concepts,
            "extra_examples":           concept_instruction.extra_examples,
            "quiz_focus":               concept_instruction.quiz_focus,
            "revision_focus":           concept_instruction.revision_focus,
        },
        learning_strategy={
            "primary_learning_mode": learning_strategy.primary_learning_mode,
            "support_learning_mode": learning_strategy.support_learning_mode,
            "session_duration":      learning_strategy.session_duration,
            "ai_tutor_required":     learning_strategy.ai_tutor_required,
        },
        quiz_instruction={
            "quiz_length":           learning_strategy.quiz_length,
            "quiz_timing":           learning_strategy.quiz_timing,
            "quiz_focus_concepts":   concept_instruction.quiz_focus,
            "difficulty_emphasis":   content_instruction.high_priority_concepts,
        },
        revision_instruction={
            "revision_required":     content_instruction.revision_required,
            "revision_focus":        content_instruction.revision_focus,
            "revision_scope":        "concept-specific" if content_instruction.revision_focus else "global",
            "revision_topics":       list(understanding.revision_topics) if understanding.revision_topics else [],
        },
        session_instruction={
            "adaptive_learning_flow":  [vars(s) for s in adaptive_flow],
            "session_duration":        learning_strategy.session_duration,
            "primary_mode":            learning_strategy.primary_learning_mode,
            "support_mode":            learning_strategy.support_learning_mode,
            "ai_tutor_required":       learning_strategy.ai_tutor_required,
        },
    )
