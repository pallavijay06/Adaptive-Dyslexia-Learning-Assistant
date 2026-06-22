"""Data models for Step Solver module."""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional


class ProblemType(Enum):
    """Enum for problem types that Step Solver can handle."""

    ARITHMETIC = "arithmetic"
    ALGEBRA = "algebra"
    SUBSTITUTION = "substitution"
    REARRANGEMENT = "rearrangement"
    UNKNOWN = "unknown"


@dataclass
class StepSolverResult:
    """Result of step-by-step problem solving."""

    problem_type: ProblemType
    input_expression: str
    steps: List[str] = field(default_factory=list)
    final_answer: Optional[str] = None
    success: bool = False

    def to_dict(self):
        """Convert result to dictionary."""
        return {
            "problem_type": self.problem_type.value,
            "input_expression": self.input_expression,
            "steps": self.steps,
            "final_answer": self.final_answer,
            "success": self.success,
        }
