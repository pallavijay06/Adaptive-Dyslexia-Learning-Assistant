"""Main solver service that orchestrates problem solving."""

from .models import StepSolverResult, ProblemType
from .detector import detect_problem_type
from .arithmetic_solver import solve_arithmetic
from .algebra_solver import solve_algebra
from .substitution_solver import solve_substitution
from .rearrangement_solver import solve_rearrangement


def solve_problem(problem: str) -> StepSolverResult:
    """
    Solve a STEM problem step-by-step.

    Workflow:
        1. Detect the problem type from input text
        2. Route to appropriate solver
        3. Return step-by-step solution

    Args:
        problem: The problem text to solve

    Returns:
        StepSolverResult containing problem type, steps, and final answer

    Note:
        Currently returns placeholder results. Full implementation pending.
    """
    # Detect problem type
    problem_type = detect_problem_type(problem)

    # Route to appropriate solver based on problem type
    if problem_type == ProblemType.ARITHMETIC:
        return solve_arithmetic(problem)
    elif problem_type == ProblemType.ALGEBRA:
        return solve_algebra(problem)
    elif problem_type == ProblemType.SUBSTITUTION:
        return solve_substitution(problem)
    elif problem_type == ProblemType.REARRANGEMENT:
        return solve_rearrangement(problem)
    else:
        return StepSolverResult(
            problem_type=ProblemType.UNKNOWN,
            input_expression=problem,
            steps=[],
            final_answer="Unsupported problem type",
            success=False,
        )
