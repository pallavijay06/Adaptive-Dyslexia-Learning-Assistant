"""Learning Strategy Engine.

Single responsibility: answer "How should today's learning session be organized?"

Generates an adaptive ordered learning sequence — NOT just a single mode
recommendation.

Inputs (read-only):
  - learning_mode_effectiveness_service → compute_mode_effectiveness
  - LearnerProfileRecord → LBA sub-scores (mode_engagement, mode_switching,
    feature_utilization, post_mode_improvement, mode_retention,
    learning_behaviour_analytics_score)

Outputs: LearningStrategyDecision dataclass.

Decision method: Evidence-Based Decision (EBD) framework.
  Each LBA signal contributes weighted evidence toward strategy decisions:
  primary mode selection, support mode inclusion, AI Tutor inclusion,
  quiz length, and session duration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# EBD evidence weights  (kept as module-level constants)
# ---------------------------------------------------------------------------

# Importance  : Very High  → weight 5
# Importance  : High       → weight 4
# Importance  : Medium     → weight 3
# Importance  : Supporting → weight 2

_W_MODE_EFFECTIVENESS = 5   # Very High
_W_MODE_RETENTION     = 4   # High
_W_POST_IMPROVEMENT   = 4   # High
_W_MODE_ENGAGEMENT    = 3   # Medium
_W_COMPLETION_RATE    = 3   # Medium  (feature_utilization is the closest existing metric)
_W_LBA_OVERALL        = 2   # Supporting


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALL_MODES = ("Simplified Notes", "Audio", "Visual", "AI Tutor")

# Minimum effectiveness score to include a mode in the candidate pool
_MIN_EFFECTIVENESS_FOR_PATH = 40.0

# Session duration bands (minutes)
_SHORT_SESSION  = 20
_MEDIUM_SESSION = 40
_LONG_SESSION   = 60

# Quiz length bands
_SHORT_QUIZ  = 5
_MEDIUM_QUIZ = 8
_LONG_QUIZ   = 12

# EBD soft-boundary centres for "learner readiness" on a 0-100 scale.
# Used to decide session duration and quiz length.
#   High readiness  → long session, long quiz
#   Medium readiness → medium session, medium quiz
#   Low readiness   → short session, short quiz
_READINESS_CANDIDATES = ("High", "Medium", "Low")
_READINESS_CENTRES: dict[str, float] = {"High": 80.0, "Medium": 55.0, "Low": 25.0}
_READINESS_HALF_WIDTH: dict[str, float] = {"High": 30.0, "Medium": 30.0, "Low": 30.0}

# EBD threshold for AI Tutor inclusion:
# if the "Low readiness" evidence exceeds this fraction of total evidence,
# include AI Tutor.
_TUTOR_LOW_READINESS_FRACTION = 0.35

# EBD threshold for support mode inclusion:
# include a support mode when the top-2 mode effectiveness scores are within
# this gap AND readiness evidence supports it.
_SUPPORT_MODE_GAP_THRESHOLD = 12.0


# ---------------------------------------------------------------------------
# Output contract  (strategy recommendations only)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LearningStrategyDecision:
    primary_learning_mode: str | None
    support_learning_mode: str | None
    ai_tutor_required: bool
    recommended_session_duration: int
    recommended_quiz_length: int
    recommended_quiz_timing: str
    confidence: float
    reasoning: list[str]


# ---------------------------------------------------------------------------
# Public API  (signatures unchanged)
# ---------------------------------------------------------------------------

def get_learning_strategy_decision(user_id: int) -> LearningStrategyDecision:
    """Compute and return the Learning Strategy Decision for a learner."""
    mode_effectiveness, lba_data = _load_inputs(user_id)
    return _decide(mode_effectiveness, lba_data)


def get_learning_strategy_decision_from_data(
    mode_effectiveness: dict[str, Any],
    lba_data: dict[str, Any],
) -> LearningStrategyDecision:
    """Pure-function variant — accepts pre-loaded data (for Master Decision Engine)."""
    return _decide(mode_effectiveness, lba_data)


# ---------------------------------------------------------------------------
# Data loading  (unchanged)
# ---------------------------------------------------------------------------

def _load_inputs(user_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    from database.db import get_learner_profile
    from services.learning_mode_effectiveness_service import compute_mode_effectiveness

    mode_effectiveness = compute_mode_effectiveness(user_id)

    profile = get_learner_profile(user_id)
    lba_data: dict[str, Any] = {}
    if profile:
        lba_data = {
            "learning_behaviour_analytics_score": profile.learning_behaviour_analytics_score,
            "mode_engagement_score":              profile.mode_engagement_score,
            "mode_switching_score":               profile.mode_switching_score,
            "feature_utilization_score":          profile.feature_utilization_score,
            "post_mode_improvement_score":        profile.post_mode_improvement_score,
            "mode_retention_score":               profile.mode_retention_score,
        }

    return mode_effectiveness, lba_data


# ---------------------------------------------------------------------------
# EBD core helpers
# ---------------------------------------------------------------------------

def _membership(value: float, centre: float, half_width: float) -> float:
    """Triangular membership: 1.0 at centre, 0.0 at ±half_width."""
    return round(max(0.0, 1.0 - abs(value - centre) / half_width), 4)


def _accumulate_readiness(
    value: float,
    weight: int,
    evidence: dict[str, float],
    contributions: dict[str, list[str]],
    label: str,
) -> None:
    """Accumulate evidence toward High / Medium / Low readiness candidates."""
    for candidate in _READINESS_CANDIDATES:
        m = _membership(value, _READINESS_CENTRES[candidate], _READINESS_HALF_WIDTH[candidate])
        contrib = weight * m
        evidence[candidate] = evidence.get(candidate, 0.0) + contrib
        if m > 0.05:
            contributions[candidate].append(
                f"{label} (value={value:.1f}, membership={m:.2f}, "
                f"weight={weight}, contribution={contrib:.2f})"
            )


def _readiness_evidence(lba_data: dict[str, Any]) -> tuple[dict[str, float], dict[str, list[str]], float]:
    """Build readiness evidence from all available LBA signals."""
    evidence: dict[str, float]          = {c: 0.0 for c in _READINESS_CANDIDATES}
    contributions: dict[str, list[str]] = {c: []  for c in _READINESS_CANDIDATES}

    signals = [
        ("mode_engagement_score",       _W_MODE_ENGAGEMENT,  "Mode engagement"),
        ("mode_retention_score",        _W_MODE_RETENTION,   "Mode retention"),
        ("post_mode_improvement_score", _W_POST_IMPROVEMENT, "Post-mode improvement"),
        ("feature_utilization_score",   _W_COMPLETION_RATE,  "Feature utilization (completion proxy)"),
        ("learning_behaviour_analytics_score", _W_LBA_OVERALL, "LBA overall score"),
    ]

    present = 0
    for key, weight, label in signals:
        val = _safe_float(lba_data.get(key))
        if val is not None:
            _accumulate_readiness(val, weight, evidence, contributions, label)
            present += 1

    completeness = present / len(signals)
    return evidence, contributions, completeness


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------

def _decide(
    mode_effectiveness: dict[str, Any],
    lba_data: dict[str, Any],
) -> LearningStrategyDecision:
    reasoning: list[str] = []

    rankings: list[dict[str, Any]] = mode_effectiveness.get("mode_rankings") or []
    recommended_mode: str | None   = mode_effectiveness.get("recommended_mode")

    # --- Build readiness evidence from LBA signals ---
    readiness_ev, readiness_contrib, lba_completeness = _readiness_evidence(lba_data)

    total_readiness = sum(readiness_ev.values())
    readiness_winner = max(readiness_ev, key=lambda c: readiness_ev[c]) if total_readiness > 0 else "Medium"

    # --- Confidence ---
    has_mode_data = bool(rankings)
    mode_completeness = 1.0 if has_mode_data else 0.0
    overall_completeness = (lba_completeness + mode_completeness) / 2.0

    sorted_rv = sorted(readiness_ev.values(), reverse=True)
    agreement = (readiness_ev[readiness_winner] / total_readiness) if total_readiness > 0 else 0.5
    runner_up_rv = sorted_rv[1] if len(sorted_rv) > 1 else 0.0
    conflict = (runner_up_rv / readiness_ev[readiness_winner]) if readiness_ev.get(readiness_winner, 0) > 0 else 0.0
    confidence = round(min(1.0, agreement * (1.0 - 0.4 * conflict) * (0.4 + 0.6 * overall_completeness)), 2)

    # --- Step 1: Build candidate mode list ---
    effective_modes: list[str] = [
        entry["mode"]
        for entry in rankings
        if float(entry.get("effectiveness") or 0.0) >= _MIN_EFFECTIVENESS_FOR_PATH
    ]

    if not effective_modes and recommended_mode:
        effective_modes = [recommended_mode]
        reasoning.append(
            f"No modes met the effectiveness threshold — using recommended mode '{recommended_mode}' only."
        )
    elif not effective_modes:
        effective_modes = list(_ALL_MODES)
        reasoning.append("No mode effectiveness data — using default sequence.")
    else:
        reasoning.append(
            f"Effective modes (score ≥ {_MIN_EFFECTIVENESS_FOR_PATH}): {effective_modes}."
        )

    # --- Step 2: Determine strategy recommendations (EBD-driven) ---
    rankings_map = {
        str(e.get("mode")): float(e.get("effectiveness") or 0.0)
        for e in rankings if e.get("mode")
    }

    primary_mode = _select_primary_mode(effective_modes, recommended_mode, rankings_map, reasoning)
    support_mode = _select_support_mode_ebd(
        effective_modes, primary_mode, rankings_map, readiness_ev, reasoning,
    )
    ai_tutor_required = _should_include_tutor_ebd(readiness_ev, reasoning)

    # --- Step 3: Session duration from readiness evidence ---
    estimated_duration = _estimate_duration_ebd(readiness_winner, readiness_ev, 2 if support_mode else 1, reasoning)

    # --- Step 4: Quiz length from readiness evidence ---
    quiz_length = _estimate_quiz_length_ebd(readiness_winner, readiness_ev, reasoning)

    # --- Step 5: Quiz timing recommendation ---
    quiz_timing = _recommend_quiz_timing(readiness_ev, reasoning)

    # --- Step 6: Confidence narrative ---
    reasoning.append(
        f"Confidence {confidence:.2f} — "
        f"LBA data completeness {lba_completeness:.0%}, "
        f"mode data {'available' if has_mode_data else 'unavailable'}, "
        f"readiness evidence agreement factored in."
    )

    return LearningStrategyDecision(
        primary_learning_mode=primary_mode,
        support_learning_mode=support_mode,
        ai_tutor_required=ai_tutor_required,
        recommended_session_duration=estimated_duration,
        recommended_quiz_length=quiz_length,
        recommended_quiz_timing=quiz_timing,
        confidence=confidence,
        reasoning=reasoning,
    )


# ---------------------------------------------------------------------------
# Strategy selection helpers (EBD-driven)
# ---------------------------------------------------------------------------

_CONTENT_MODES = {"Simplified Notes", "Audio", "Visual"}


def _select_primary_mode(
    effective_modes: list[str],
    recommended_mode: str | None,
    rankings_map: dict[str, float],
    reasoning: list[str],
) -> str:
    content_modes = [m for m in effective_modes if m in _CONTENT_MODES]

    # Promote recommended_mode to front if it is a content mode
    if recommended_mode and recommended_mode in _CONTENT_MODES:
        if recommended_mode in content_modes and content_modes[0] != recommended_mode:
            content_modes.remove(recommended_mode)
            content_modes.insert(0, recommended_mode)

    if content_modes:
        primary = content_modes[0]
        eff = rankings_map.get(primary, 0.0)
        reasoning.append(
            f"Primary mode '{primary}' selected — highest effectiveness "
            f"({eff:.1f}) among content modes."
        )
        return primary

    if recommended_mode:
        reasoning.append(f"No content modes available — falling back to '{recommended_mode}'.")
        return recommended_mode

    reasoning.append("No effective modes — defaulting to Simplified Notes.")
    return "Simplified Notes"


def _select_support_mode_ebd(
    effective_modes: list[str],
    primary_mode: str,
    rankings_map: dict[str, float],
    readiness_ev: dict[str, float],
    reasoning: list[str],
) -> str | None:
    """Include a support mode when evidence supports it."""
    candidates = [m for m in effective_modes if m in _CONTENT_MODES and m != primary_mode]
    if not candidates:
        return None

    support = candidates[0]
    primary_eff = rankings_map.get(primary_mode, 0.0)
    support_eff = rankings_map.get(support, 0.0)
    gap = primary_eff - support_eff

    total_ev = sum(readiness_ev.values())
    low_fraction  = (readiness_ev.get("Low", 0.0)  / total_ev) if total_ev > 0 else 0.0
    high_fraction = (readiness_ev.get("High", 0.0) / total_ev) if total_ev > 0 else 0.0

    # Severe low readiness → keep path minimal (avoid overload)
    if low_fraction > 0.55:
        reasoning.append(
            f"Low readiness evidence dominant ({low_fraction:.0%}) — "
            "omitting support mode to keep the session manageable."
        )
        return None

    # High readiness + close gap → add support mode for variety
    if gap <= _SUPPORT_MODE_GAP_THRESHOLD and high_fraction > 0.35:
        reasoning.append(
            f"Added support mode '{support}' — effectiveness gap {gap:.1f} is small "
            f"and high readiness evidence ({high_fraction:.0%}) supports a richer session."
        )
        return support

    # Medium readiness + close gap → add support mode for reinforcement
    if gap <= _SUPPORT_MODE_GAP_THRESHOLD and low_fraction < 0.35:
        reasoning.append(
            f"Added support mode '{support}' — effectiveness gap {gap:.1f} is small "
            "and readiness evidence supports a complementary step."
        )
        return support

    reasoning.append(
        f"Effectiveness gap between '{primary_mode}' ({primary_eff:.1f}) and "
        f"'{support}' ({support_eff:.1f}) is {gap:.1f} — omitting support mode."
    )
    return None


def _should_include_tutor_ebd(
    readiness_ev: dict[str, float],
    reasoning: list[str],
) -> bool:
    """Include AI Tutor when Low readiness evidence exceeds the threshold fraction."""
    total_ev = sum(readiness_ev.values())
    if total_ev == 0:
        reasoning.append("No readiness evidence — omitting AI Tutor by default.")
        return False

    low_fraction = readiness_ev.get("Low", 0.0) / total_ev

    if low_fraction >= _TUTOR_LOW_READINESS_FRACTION:
        reasoning.append(
            f"AI Tutor included — Low readiness evidence is {low_fraction:.0%} of total "
            f"(threshold {_TUTOR_LOW_READINESS_FRACTION:.0%}), indicating the learner needs guidance."
        )
        return True

    reasoning.append(
        f"AI Tutor omitted — Low readiness evidence is only {low_fraction:.0%} "
        f"(threshold {_TUTOR_LOW_READINESS_FRACTION:.0%}); learner is performing adequately."
    )
    return False


# ---------------------------------------------------------------------------
# Duration and quiz-length (EBD-driven)
# ---------------------------------------------------------------------------

def _estimate_duration_ebd(
    readiness_winner: str,
    readiness_ev: dict[str, float],
    path_length: int,
    reasoning: list[str],
) -> int:
    base = path_length * 8

    if readiness_winner == "High":
        duration = max(_LONG_SESSION, base)
        reasoning.append(
            f"High readiness evidence dominant → long session recommended: {duration} min."
        )
    elif readiness_winner == "Medium":
        duration = max(_MEDIUM_SESSION, base)
        reasoning.append(
            f"Medium readiness evidence dominant → standard session: {duration} min."
        )
    else:
        duration = max(_SHORT_SESSION, base)
        reasoning.append(
            f"Low readiness evidence dominant → shorter session to avoid overload: {duration} min."
        )

    return duration


def _recommend_quiz_timing(
    readiness_ev: dict[str, float],
    reasoning: list[str],
) -> str:
    total_ev = sum(readiness_ev.values())
    low_fraction = (readiness_ev.get("Low", 0.0) / total_ev) if total_ev > 0 else 0.0
    high_fraction = (readiness_ev.get("High", 0.0) / total_ev) if total_ev > 0 else 0.0

    if low_fraction >= 0.35:
        timing = "After Revision"
        reasoning.append(
            f"Low readiness evidence ({low_fraction:.0%}) suggests quiz timing: {timing}."
        )
        return timing

    if high_fraction >= 0.35:
        timing = "After Learning"
        reasoning.append(
            f"High readiness evidence ({high_fraction:.0%}) suggests quiz timing: {timing}."
        )
        return timing

    timing = "After Learning"
    reasoning.append(f"Default quiz timing recommendation: {timing}.")
    return timing


def _estimate_quiz_length_ebd(
    readiness_winner: str,
    readiness_ev: dict[str, float],
    reasoning: list[str],
) -> int:
    total_ev = sum(readiness_ev.values())
    low_fraction = (readiness_ev.get("Low", 0.0) / total_ev) if total_ev > 0 else 0.0

    if readiness_winner == "High":
        length = _LONG_QUIZ
        reasoning.append(
            f"High readiness → longer quiz ({length} questions) to challenge the learner."
        )
    elif readiness_winner == "Medium":
        length = _MEDIUM_QUIZ
        reasoning.append(
            f"Medium readiness → standard quiz ({length} questions)."
        )
    else:
        length = _SHORT_QUIZ
        reasoning.append(
            f"Low readiness → shorter quiz ({length} questions) to avoid cognitive overload."
        )

    # Reinforcement bonus: if Low readiness has meaningful evidence even when not dominant
    if readiness_winner != "Low" and low_fraction > 0.25:
        length = min(length + 2, _LONG_QUIZ)
        reasoning.append(
            f"Low readiness evidence ({low_fraction:.0%}) suggests reinforcement needed "
            f"— +2 questions added (total: {length})."
        )

    return length


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
