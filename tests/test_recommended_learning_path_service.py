from services.master_decision_engine import (
    AdaptiveLearningPlan,
    ConceptInstruction,
    ContentInstruction,
    DecisionSummary,
    LearningFlowStep,
    LearningStrategy,
    PromptInstructionSet,
)
from services.recommended_learning_path_service import get_recommended_learning_path


def _make_plan(primary_mode: str, revision_required: bool = False, ai_tutor_required: bool = False) -> AdaptiveLearningPlan:
    return AdaptiveLearningPlan(
        content_instruction=ContentInstruction(
            content_complexity="Simple",
            reading_level="Easy",
            worked_examples="Many",
            analogy_required=True,
            step_by_step=True,
            revision_required=revision_required,
            high_priority_concepts=["photosynthesis"],
            extra_examples=["examples"],
            quiz_focus=["quiz"],
            revision_focus=["revision"],
        ),
        concept_instruction=ConceptInstruction(
            high_priority_concepts=["photosynthesis"],
            medium_priority_concepts=["cells"],
            low_priority_concepts=["atoms"],
            extra_examples=["examples"],
            quiz_focus=["quiz"],
            revision_focus=["revision"],
        ),
        learning_strategy=LearningStrategy(
            primary_learning_mode=primary_mode,
            support_learning_mode="Notes",
            session_duration=40,
            quiz_length=4,
            quiz_timing="After Learning",
            ai_tutor_required=ai_tutor_required,
        ),
        adaptive_learning_flow=[
            LearningFlowStep(step=1, action="learning_mode", mode=primary_mode),
            LearningFlowStep(step=2, action="extra_examples"),
            LearningFlowStep(step=3, action="quiz", quiz_length=4, quiz_timing="After Learning"),
        ],
        overall_confidence=0.92,
        decision_summary=DecisionSummary(
            teaching_style="Simple",
            focus_concepts=["photosynthesis"],
            learning_strategy=primary_mode,
            revision_required=revision_required,
            session_duration="40 minutes",
            overall_confidence=0.92,
        ),
        prompt_instruction_set=PromptInstructionSet(
            content_instruction={},
            concept_instruction={},
            learning_strategy={},
            quiz_instruction={},
            revision_instruction={},
            session_instruction={},
        ),
    )


def test_recommended_path_for_advanced_learner():
    plan = _make_plan("Visual")
    path = get_recommended_learning_path(plan)
    assert path.title.startswith("Recommended learning path")
    assert path.current_recommendation == "Visual Learning"
    assert path.recommended_steps[0].display_order == 1
    assert path.recommended_steps[0].mode_id == "visual"
    assert path.recommended_steps[0].icon == "🧠"
    assert path.recommended_steps[0].status == "RECOMMENDED"
    assert path.recommended_steps[0].completed is False
    assert path.recommended_steps[0].start_condition == "Immediate"
    assert path.recommended_steps[0].action_button_text == "Start Visual Learning"
    assert path.recommended_steps[0].completion_message is not None
    assert path.recommended_steps[0].priority == "High"
    assert path.estimated_total_duration > 0


def test_recommended_path_for_average_learner():
    plan = _make_plan("Text")
    path = get_recommended_learning_path(plan)
    assert path.recommended_steps[0].mode == "Text Learning"
    assert path.recommended_steps[0].mode_id == "text"
    assert len(path.recommended_steps) >= 3


def test_recommended_path_for_struggling_learner():
    plan = _make_plan("Visual", revision_required=True, ai_tutor_required=True)
    path = get_recommended_learning_path(plan)
    revision_step = next(step for step in path.recommended_steps if step.mode_id == "revision")
    ai_tutor_step = next(step for step in path.recommended_steps if step.mode_id == "ai_tutor")
    assert revision_step.status == "RECOMMENDED"
    assert ai_tutor_step.status == "OPTIONAL"
    assert revision_step.start_condition == "After Quiz"
    assert ai_tutor_step.action_button_text == "Ask AI Tutor"
    assert ai_tutor_step.icon == "🤖"
    assert path.current_recommendation == "Visual Learning"
