from services.prompt_builder.prompt_merger import merge
from services.prompt_builder.prompt_types import PromptType


def test_merge_includes_priority_and_actionable_notes_guidance():
    filtered = {
        "teaching_style": "Very Simple, Step-by-Step",
        "reading_level": "Easy",
        "content_complexity": "Simple",
        "worked_examples": "Many",
        "step_by_step": True,
        "analogy_required": True,
        "revision_required": True,
        "high_priority_concepts": ["photosynthesis", "cells"],
        "revision_focus": ["mitosis"],
    }

    output = merge(filtered, "Original prompt", PromptType.NOTES)

    assert "highest-priority behavioural specification" in output
    assert "Use plain, accessible language" in output
    assert "Provide several worked examples" in output
    assert "Spend significantly more explanation time on weak concepts" in output
    assert "Generate additional revision questions" in output
    assert "Original prompt" in output


def test_merge_includes_visual_and_quiz_guidance():
    filtered = {
        "teaching_style": "Visual",
        "high_priority_concepts": ["energy"],
        "quiz_focus": ["force"],
        "quiz_length": 6,
        "quiz_timing": "After Learning",
    }

    visual_output = merge(filtered, "Original prompt", PromptType.VISUAL)
    quiz_output = merge(filtered, "Original prompt", PromptType.QUIZ)

    assert "organize information visually" in visual_output.lower()
    assert "minimize dense text" in visual_output.lower()
    assert "Prioritize weak concepts" in quiz_output
    assert "Gradually increase difficulty" in quiz_output
    assert "Approximately follow the recommended quiz length" in quiz_output
