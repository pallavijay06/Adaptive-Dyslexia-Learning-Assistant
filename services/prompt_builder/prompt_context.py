"""PromptContext — the single input contract for the Prompt Builder.

The caller constructs a PromptContext and passes it to build_prompt().
No other parameters are needed.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.prompt_builder.prompt_types import PromptType

# Import AdaptiveLearningPlan type for annotation only — no circular dependency
# because master_decision_engine does not import anything from prompt_builder.
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.master_decision_engine import AdaptiveLearningPlan


@dataclass(frozen=True)
class PromptContext:
    """All information the Prompt Builder needs to produce a personalized prompt.

    Attributes:
        prompt_type:     Which kind of prompt is being personalized.
        plan:            The AdaptiveLearningPlan produced by the Master Decision Engine.
        original_prompt: The existing prompt string, passed through unchanged.
    """
    prompt_type:     PromptType
    plan:            "AdaptiveLearningPlan"
    original_prompt: str
