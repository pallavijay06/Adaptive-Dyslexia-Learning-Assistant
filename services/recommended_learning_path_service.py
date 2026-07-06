"""Recommended Learning Path Service.

This service is a pure interpreter of an AdaptiveLearningPlan produced by the
Master Decision Engine. It does not make decisions, compute evidence, or call
any external services. It converts the plan into a UI-friendly structure that
can be rendered directly by the frontend.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.master_decision_engine import AdaptiveLearningPlan, LearningFlowStep


@dataclass(frozen=True)
class LearningPathStep:
    """A single UI-ready step in the recommended learning journey."""

    display_order: int
    mode: str
    mode_id: str
    title: str
    description: str
    reason: str
    estimated_duration: int
    priority: str
    status: str
    icon: str
    completed: bool = False
    start_condition: str = "Immediate"
    action_button_text: str = ""
    decision_source: str = "Adaptive Learning Flow"
    completion_message: str | None = None


@dataclass(frozen=True)
class RecommendedLearningPath:
    """A fully structured learning journey suitable for direct frontend rendering."""

    title: str
    description: str
    estimated_total_duration: int
    confidence: float
    current_recommendation: str
    recommended_steps: list[LearningPathStep]


def get_recommended_learning_path(adaptive_learning_plan: AdaptiveLearningPlan) -> RecommendedLearningPath:
    """Convert an AdaptiveLearningPlan into a UI-friendly learning path.

    This function is a deterministic interpreter of the plan. It never makes new
    decisions and only reorganizes the existing guidance into a frontend-ready
    structure.
    """

    if not isinstance(adaptive_learning_plan, AdaptiveLearningPlan):
        raise TypeError("adaptive_learning_plan must be an AdaptiveLearningPlan")

    steps: list[LearningPathStep] = []
    flow_steps = list(adaptive_learning_plan.adaptive_learning_flow or [])

    if not flow_steps:
        flow_steps = _default_flow_steps(adaptive_learning_plan)

    flow_steps = _expand_flow_steps(flow_steps, adaptive_learning_plan)

    for index, flow_step in enumerate(flow_steps, start=1):
        step = _build_step(index, flow_step, adaptive_learning_plan)
        if step is not None:
            steps.append(step)

    total_duration = max(1, sum(step.estimated_duration for step in steps))
    title = _build_title(adaptive_learning_plan)
    description = _build_description(adaptive_learning_plan)
    current_recommendation = steps[0].mode if steps else ""

    return RecommendedLearningPath(
        title=title,
        description=description,
        estimated_total_duration=total_duration,
        confidence=float(adaptive_learning_plan.overall_confidence),
        current_recommendation=current_recommendation,
        recommended_steps=steps,
    )


def _default_flow_steps(plan: AdaptiveLearningPlan) -> list[LearningFlowStep]:
    primary_mode = plan.learning_strategy.primary_learning_mode or "Guided Learning"
    return [
        LearningFlowStep(step=1, action="learning_mode", mode=primary_mode),
        LearningFlowStep(step=2, action="quiz", quiz_length=plan.learning_strategy.quiz_length),
    ]


def _expand_flow_steps(flow_steps: list[LearningFlowStep], plan: AdaptiveLearningPlan) -> list[LearningFlowStep]:
    expanded: list[LearningFlowStep] = []
    for flow_step in flow_steps:
        expanded.append(flow_step)

    if getattr(plan.content_instruction, "revision_required", False):
        expanded.append(LearningFlowStep(step=len(expanded) + 1, action="revision"))

    if getattr(plan.learning_strategy, "ai_tutor_required", False):
        expanded.append(LearningFlowStep(step=len(expanded) + 1, action="ai_tutor", enabled=True))

    return expanded


def _build_step(index: int, flow_step: LearningFlowStep, plan: AdaptiveLearningPlan) -> LearningPathStep | None:
    action = flow_step.action or "learning_mode"
    total_steps = max(1, len(plan.adaptive_learning_flow or []) + (1 if getattr(plan.content_instruction, "revision_required", False) else 0) + (1 if getattr(plan.learning_strategy, "ai_tutor_required", False) else 0))

    if action == "revision":
        mode_name = "Revision"
        return LearningPathStep(
            display_order=index,
            mode=mode_name,
            mode_id="revision",
            title="Review and reinforce key ideas",
            description="Revisit the most important concepts before moving on.",
            reason="Revision has been recommended by the adaptive plan.",
            estimated_duration=_estimate_duration(index, total_steps, plan.learning_strategy.session_duration, action),
            priority="High",
            status="RECOMMENDED",
            icon="🔄",
            start_condition="After Quiz",
            action_button_text="Start Revision",
            decision_source="Master Decision",
            completion_message="Great job! You are now ready to discuss any remaining doubts with the AI Tutor.",
        )

    if action == "learning_mode":
        mode_name = _display_mode_name(flow_step.mode or plan.learning_strategy.primary_learning_mode or "Guided Learning")
        mode_id = _mode_id(mode_name)
        title = _mode_title(mode_name)
        description = _mode_description(mode_name)
        reason = _mode_reason(mode_name, plan)
        return LearningPathStep(
            display_order=index,
            mode=mode_name,
            mode_id=mode_id,
            title=title,
            description=description,
            reason=reason,
            estimated_duration=_estimate_duration(index, total_steps, plan.learning_strategy.session_duration, action),
            priority="High",
            status="RECOMMENDED",
            icon=_icon_for_mode(mode_id),
            start_condition="Immediate",
            action_button_text=_action_button_text(mode_name),
            decision_source="Learning Strategy",
            completion_message=_completion_message(mode_name, action),
        )

    if action == "extra_examples":
        return LearningPathStep(
            display_order=index,
            mode="Extra Examples",
            mode_id="examples",
            title="Work through extra examples",
            description="Spend time on additional examples for areas that need more support.",
            reason="The adaptive plan highlights concepts that need extra worked examples.",
            estimated_duration=_estimate_duration(index, total_steps, plan.learning_strategy.session_duration, action),
            priority="Medium",
            status="RECOMMENDED",
            icon="🧩",
            start_condition="After Learning",
            action_button_text="Continue with Examples",
            decision_source="Adaptive Learning Flow",
            completion_message="Nice progress! Keep going and build confidence with another example.",
        )

    if action == "quiz":
        return LearningPathStep(
            display_order=index,
            mode="Quiz",
            mode_id="quiz",
            title="Check understanding with a short quiz",
            description="Test the learner's grasp of the current topic with a short assessment.",
            reason="Quiz practice has been scheduled according to the adaptive plan.",
            estimated_duration=_estimate_duration(index, total_steps, plan.learning_strategy.session_duration, action),
            priority="Medium",
            status="RECOMMENDED",
            icon="📝",
            start_condition="After Learning",
            action_button_text="Take Quiz",
            decision_source="Adaptive Learning Flow",
            completion_message="Great job! You are now ready to discuss any remaining doubts with the AI Tutor.",
        )

    if action == "ai_tutor":
        status = "OPTIONAL"
        return LearningPathStep(
            display_order=index,
            mode="AI Tutor",
            mode_id="ai_tutor",
            title="Ask the tutor for help",
            description="Use the tutor for guided explanations, examples, and follow-up support.",
            reason="The adaptive plan recommends AI tutor support for this session.",
            estimated_duration=_estimate_duration(index, total_steps, plan.learning_strategy.session_duration, action),
            priority="Medium",
            status=status,
            icon="🤖",
            start_condition="After Quiz",
            action_button_text="Ask AI Tutor",
            decision_source="Learning Strategy",
            completion_message="You are doing well. Ask for another explanation whenever you need support.",
        )

    return None


def _display_mode_name(mode_name: str) -> str:
    mapping = {
        "Visual": "Visual Learning",
        "Auditory": "Auditory Learning",
        "Kinaesthetic": "Kinaesthetic Learning",
        "Text": "Text Learning",
        "Simplified Notes": "Simplified Notes",
    }
    return mapping.get(mode_name, mode_name)


def _mode_id(mode_name: str) -> str:
    mapping = {
        "Visual Learning": "visual",
        "Auditory Learning": "auditory",
        "Kinaesthetic Learning": "kinaesthetic",
        "Text Learning": "text",
        "Simplified Notes": "notes",
        "Quiz": "quiz",
        "AI Tutor": "ai_tutor",
        "Revision": "revision",
        "Extra Examples": "examples",
    }
    return mapping.get(mode_name, mode_name.lower().replace(" ", "_"))


def _icon_for_mode(mode_id: str) -> str:
    mapping = {
        "visual": "🧠",
        "notes": "📄",
        "quiz": "📝",
        "ai_tutor": "🤖",
        "revision": "🔄",
        "examples": "🧩",
    }
    return mapping.get(mode_id, "📚")


def _mode_title(mode_name: str) -> str:
    mapping = {
        "Visual Learning": "Understand the topic visually",
        "Auditory Learning": "Learn through guided explanation",
        "Kinaesthetic Learning": "Explore the concept through practice",
        "Text Learning": "Read and review the material",
        "Simplified Notes": "Read the simplified notes",
    }
    return mapping.get(mode_name, f"Follow the {mode_name} learning path")


def _mode_description(mode_name: str) -> str:
    mapping = {
        "Visual Learning": "Begin today's learning using visual relationships, concept organization, and simple structure.",
        "Auditory Learning": "Use spoken explanation and guided narration to reinforce understanding.",
        "Kinaesthetic Learning": "Use hands-on examples and practical activities to build confidence.",
        "Text Learning": "Read the key points carefully and connect them to the main topic.",
        "Simplified Notes": "Read the simplified notes to strengthen understanding before the next step.",
    }
    return mapping.get(mode_name, "Begin today's learning with the recommended learning mode.")


def _mode_reason(mode_name: str, plan: AdaptiveLearningPlan) -> str:
    mode_text = mode_name.lower()
    if "visual" in mode_text:
        return "Visual learning has been identified as the most effective learning mode for this learner."
    if "auditory" in mode_text:
        return "Auditory support has been recommended to reinforce explanation and memory."
    if "kinaesthetic" in mode_text:
        return "Hands-on practice has been recommended to support deeper understanding."
    return f"The adaptive plan recommends {mode_name} as the primary learning mode."


def _action_button_text(mode_name: str) -> str:
    mapping = {
        "Visual Learning": "Start Visual Learning",
        "Auditory Learning": "Start Auditory Learning",
        "Kinaesthetic Learning": "Start Kinaesthetic Learning",
        "Text Learning": "Read Simplified Notes",
        "Simplified Notes": "Read Simplified Notes",
    }
    return mapping.get(mode_name, f"Start {mode_name}")


def _completion_message(mode_name: str, action: str) -> str | None:
    if action == "learning_mode" and "Visual" in mode_name:
        return "Excellent! Continue with the recommended notes to reinforce today's concepts."
    if action == "learning_mode":
        return "Well done! Continue with the next step to strengthen your understanding."
    return None


def _estimate_duration(index: int, total_steps: int, session_duration: int, action: str) -> int:
    if session_duration <= 0:
        session_duration = 40

    if total_steps <= 1:
        return max(5, session_duration)

    base = max(5, int(session_duration / max(1, total_steps)))
    if action == "quiz":
        return max(5, int(base * 0.8))
    if action == "ai_tutor":
        return max(5, int(base * 0.7))
    if action == "revision":
        return max(5, int(base * 1.0))
    if action == "extra_examples":
        return max(5, int(base * 1.1))
    return base


def _build_title(plan: AdaptiveLearningPlan) -> str:
    primary_mode = plan.learning_strategy.primary_learning_mode or "Guided Learning"
    return f"Recommended learning path for {primary_mode}"


def _build_description(plan: AdaptiveLearningPlan) -> str:
    return (
        "A UI-ready learning journey derived from the adaptive learning plan. "
        "Each step is ordered to match the learner's recommended session flow."
    )
