"""Step Solver module for STEM support.

Provides step-by-step problem solving for:
- Arithmetic
- Algebra
- Formula Substitution
- Formula Rearrangement
"""

from .models import ProblemType, StepSolverResult
from .solver_service import solve_problem

__all__ = [
    "ProblemType",
    "StepSolverResult",
    "solve_problem",
]
