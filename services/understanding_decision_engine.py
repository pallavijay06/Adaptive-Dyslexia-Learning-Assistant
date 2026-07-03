"""Understanding Decision Engine.

Single responsibility: answer "How should this content be explained to this learner?"

Inputs (read-only):
  - LearnerProfileRecord  → comprehension_score, quiz_accuracy_score
  - learning_progress_analytics_service → retention_score, learning_improvement_trend

Outputs: UnderstandingDecision dataclass.

Decision method: Evidence-Based Decision (EBD) framework.
  Each learner metric contributes weighted evidence toward candidate complexity
  levels. The candidate with the highest accumulated evidence wins.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Output contract  (unchanged)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UnderstandingDecision:
    content_complexity: str       # Very Simple / Simple / Moderate / Advanced
    reading_level: str            # Easy / Standard / Advanced
    worked_examples: str          # Few / Moderate / Many
    analogy_required: bool
    step_by_step: bool
    revision_required: bool
    confidence: float             # 0.0 – 1.0
    reasoning: list[str]


# ---------------------------------------------------------------------------
# EBD evidence weights  (kept as module-level constants)
# ---------------------------------------------------------------------------

# Importance  : Very High  → weight 5
# Importance  : High       → weight 4
# Importance  : Medium     → weight 3
# Importance  : Supporting → weight 2

_W_COMPREHENSION = 5   # Very High
_W_QUIZ_ACCURACY = 4   # High
_W_RETENTION     = 3   # Medium
_W_TREND         = 2   # Supporting

# Candidate complexity levels (ordered from lowest to highest)
_CANDIDATES = ("Very Simple", "Simple", "Moderate", "Advanced")

# Soft boundary centres for each candidate on a 0-100 scale.
# Evidence contribution is highest when the metric is near the centre and
# falls off linearly toward the adjacent boundaries.
#
#   Very Simple  centre = 20   range [0,  40]
#   Simple       centre = 45   range [20, 65]
#   Moderate     centre = 67   range [45, 85]
#   Advanced     centre = 90   range [70, 100]
#
_CENTRES: dict[str, float] = {
    "Very Simple": 20.0,
    "Simple":      45.0,
    "Moderate":    67.0,
    "Advanced":    90.0,
}

# Half-width of the triangular membership function for each candidate.
_HALF_WIDTH: dict[str, float] = {
    "Very Simple": 25.0,
    "Simple":      25.0,
    "Moderate":    22.0,
    "Advanced":    25.0,
}

# Trend → evidence direction mapping
# Improving  → pushes evidence toward higher complexity (learner is ready for more)
# Declining  → pushes evidence toward lower complexity (learner needs support)
# Stable     → neutral (small push toward current centre)
_TREND_SHIFT: dict[str, float] = {
    "Improving": +15.0,   # shift metric value up before computing membership
    "Declining": -15.0,
    "Stable":     0.0,
}

# Revision thresholds (still needed for the binary revision_required flag)
_REVISION_RETENTION_THRESHOLD = 65.0
_REVISION_TREND_TRIGGER       = "Declining"


# ---------------------------------------------------------------------------
# Public API  (signatures unchanged)
# ---------------------------------------------------------------------------

def get_understanding_decision(user_id: int) -> UnderstandingDecision:
    """Compute and return the Understanding Decision for a learner."""
    profile_data, retention_data, trend_data = _load_inputs(user_id)
    return _decide(profile_data, retention_data, trend_data)


def get_understanding_decision_from_data(
    *,
    comprehension_score: float | None,
    quiz_accuracy_score: float | None,
    retention_score: float | None,
    learning_trend: str | None,
) -> UnderstandingDecision:
    """Pure-function variant — accepts pre-loaded values (for Master Decision Engine)."""
    return _decide(
        {
            "comprehension_score": comprehension_score,
            "quiz_accuracy_score": quiz_accuracy_score,
        },
        {"score": retention_score, "has_data": retention_score is not None},
        {"status": learning_trend or "Stable", "has_data": learning_trend is not None},
    )


# ---------------------------------------------------------------------------
# Data loading  (unchanged)
# ---------------------------------------------------------------------------

def _load_inputs(
    user_id: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    from database.db import get_learner_profile, get_quiz_history, get_quiz_question_responses
    from services.learning_progress_analytics_service import (
        compute_retention_score,
        compute_learning_improvement_trend,
    )

    profile = get_learner_profile(user_id)
    profile_data: dict[str, Any] = {
        "comprehension_score": float(profile.comprehension_score) if profile and profile.comprehension_score is not None else None,
        "quiz_accuracy_score": float(profile.quiz_accuracy_score) if profile and profile.quiz_accuracy_score is not None else None,
    }

    quizzes = get_quiz_history(user_id, limit=200)
    responses = get_quiz_question_responses(user_id, limit=1000)
    retention_data = compute_retention_score(responses, quizzes)
    trend_data = compute_learning_improvement_trend(quizzes)

    return profile_data, retention_data, trend_data


# ---------------------------------------------------------------------------
# EBD core helpers
# ---------------------------------------------------------------------------

def _membership(value: float, candidate: str) -> float:
    """Triangular membership: 1.0 at centre, 0.0 at ±half_width, clamped to [0, 1]."""
    centre = _CENTRES[candidate]
    half   = _HALF_WIDTH[candidate]
    raw    = max(0.0, 1.0 - abs(value - centre) / half)
    return round(raw, 4)


def _accumulate_evidence(
    metric_value: float,
    weight: int,
    evidence: dict[str, float],
    contributions: dict[str, list[str]],
    metric_label: str,
) -> None:
    """Add weighted membership scores to every candidate's evidence bucket."""
    for candidate in _CANDIDATES:
        m = _membership(metric_value, candidate)
        contribution = weight * m
        evidence[candidate] = evidence.get(candidate, 0.0) + contribution
        if m > 0.05:   # only record meaningful contributions
            contributions[candidate].append(
                f"{metric_label} (value={metric_value:.1f}, "
                f"membership={m:.2f}, weight={weight}, "
                f"contribution={contribution:.2f})"
            )


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------

def _decide(
    profile_data: dict[str, Any],
    retention_data: dict[str, Any],
    trend_data: dict[str, Any],
) -> UnderstandingDecision:

    comprehension  = profile_data.get("comprehension_score")
    quiz_accuracy  = profile_data.get("quiz_accuracy_score")
    retention_val  = float(retention_data.get("score") or 0.0) if retention_data.get("has_data") else None
    trend_status   = str(trend_data.get("status") or "Stable")
    trend_has_data = bool(trend_data.get("has_data"))

    # Track which metrics are present for completeness calculation
    metrics_present = [comprehension, quiz_accuracy, retention_val]
    completeness = sum(v is not None for v in metrics_present) / 3.0

    evidence: dict[str, float]              = {c: 0.0 for c in _CANDIDATES}
    contributions: dict[str, list[str]]     = {c: []  for c in _CANDIDATES}

    # --- Comprehension score (weight 5, Very High) ---
    if comprehension is not None:
        _accumulate_evidence(comprehension, _W_COMPREHENSION, evidence, contributions, "Comprehension score")

    # --- Quiz accuracy (weight 4, High) ---
    if quiz_accuracy is not None:
        _accumulate_evidence(quiz_accuracy, _W_QUIZ_ACCURACY, evidence, contributions, "Quiz accuracy")

    # --- Retention score (weight 3, Medium) ---
    if retention_val is not None:
        _accumulate_evidence(retention_val, _W_RETENTION, evidence, contributions, "Retention score")

    # --- Learning trend (weight 2, Supporting) ---
    # Trend has no numeric value of its own; instead it shifts the effective
    # value of the primary signal (comprehension) before computing membership.
    if trend_has_data and comprehension is not None:
        shift = _TREND_SHIFT.get(trend_status, 0.0)
        if shift != 0.0:
            shifted = max(0.0, min(100.0, comprehension + shift))
            _accumulate_evidence(shifted, _W_TREND, evidence, contributions,
                                 f"Learning trend ({trend_status}, shifted comprehension to {shifted:.1f})")

    # --- Cold-start fallback ---
    if all(v == 0.0 for v in evidence.values()):
        evidence["Simple"] = 1.0
        contributions["Simple"].append("No learner data available — defaulting to Simple.")

    # --- Winner ---
    winner = max(evidence, key=lambda c: evidence[c])
    winner_score = evidence[winner]

    # --- Confidence: agreement × completeness ---
    total_evidence = sum(evidence.values())
    agreement = (evidence[winner] / total_evidence) if total_evidence > 0 else 0.0
    # Penalise conflict: if runner-up is close, agreement drops
    sorted_scores = sorted(evidence.values(), reverse=True)
    runner_up = sorted_scores[1] if len(sorted_scores) > 1 else 0.0
    conflict_ratio = (runner_up / winner_score) if winner_score > 0 else 0.0
    agreement_adjusted = agreement * (1.0 - 0.4 * conflict_ratio)
    confidence = round(min(1.0, agreement_adjusted * (0.4 + 0.6 * completeness)), 2)

    # --- Derived attributes from winner ---
    complexity     = winner
    reading_level  = _reading_level(complexity)
    worked_examples = _worked_examples(complexity)
    analogy_required = complexity in ("Very Simple", "Simple")
    step_by_step     = complexity in ("Very Simple", "Simple", "Moderate")

    # --- Revision required (binary flag, separate from complexity) ---
    revision_required = False
    revision_reason   = ""
    if retention_val is not None and retention_val < _REVISION_RETENTION_THRESHOLD:
        revision_required = True
        revision_reason = f"Retention score {retention_val:.1f} is below {_REVISION_RETENTION_THRESHOLD} — prior material needs reinforcement."
    elif trend_status == _REVISION_TREND_TRIGGER:
        revision_required = True
        revision_reason = "Learning trend is Declining — revision is recommended before advancing."

    # --- Reasoning (EBD-style narrative) ---
    reasoning = _build_reasoning(
        winner, winner_score, evidence, contributions,
        complexity, revision_required, revision_reason,
        trend_status, trend_has_data, completeness, confidence,
    )

    return UnderstandingDecision(
        content_complexity=complexity,
        reading_level=reading_level,
        worked_examples=worked_examples,
        analogy_required=analogy_required,
        step_by_step=step_by_step,
        revision_required=revision_required,
        confidence=confidence,
        reasoning=reasoning,
    )


# ---------------------------------------------------------------------------
# Attribute derivation helpers
# ---------------------------------------------------------------------------

def _reading_level(complexity: str) -> str:
    return {
        "Very Simple": "Easy",
        "Simple":      "Easy",
        "Moderate":    "Standard",
        "Advanced":    "Advanced",
    }[complexity]


def _worked_examples(complexity: str) -> str:
    return {
        "Very Simple": "Many",
        "Simple":      "Many",
        "Moderate":    "Moderate",
        "Advanced":    "Few",
    }[complexity]


# ---------------------------------------------------------------------------
# Reasoning builder
# ---------------------------------------------------------------------------

def _build_reasoning(
    winner: str,
    winner_score: float,
    evidence: dict[str, float],
    contributions: dict[str, list[str]],
    complexity: str,
    revision_required: bool,
    revision_reason: str,
    trend_status: str,
    trend_has_data: bool,
    completeness: float,
    confidence: float,
) -> list[str]:
    lines: list[str] = []

    lines.append(
        f"'{winner}' explanation received the strongest accumulated evidence "
        f"(score {winner_score:.2f}):"
    )
    for contrib in contributions[winner]:
        lines.append(f"  • {contrib}")

    # Show competing candidates for transparency
    runners = sorted(
        [(c, s) for c, s in evidence.items() if c != winner and s > 0.0],
        key=lambda x: x[1], reverse=True,
    )
    if runners:
        runner_summary = ", ".join(f"{c} ({s:.2f})" for c, s in runners[:2])
        lines.append(f"Competing candidates: {runner_summary}.")

    # Trend note
    if trend_has_data:
        lines.append(f"Learning trend is '{trend_status}' — factored in as supporting evidence.")

    # Revision
    if revision_required:
        lines.append(f"Revision required: {revision_reason}")
    else:
        lines.append("No revision flagged — retention and trend are acceptable.")

    # Derived attributes
    lines.append(
        f"Derived attributes: reading_level='{_reading_level(complexity)}', "
        f"worked_examples='{_worked_examples(complexity)}', "
        f"analogy_required={complexity in ('Very Simple', 'Simple')}, "
        f"step_by_step={complexity in ('Very Simple', 'Simple', 'Moderate')}."
    )

    # Confidence explanation
    lines.append(
        f"Confidence {confidence:.2f} — "
        f"data completeness {completeness:.0%}, "
        f"evidence agreement factored in."
    )

    return lines
