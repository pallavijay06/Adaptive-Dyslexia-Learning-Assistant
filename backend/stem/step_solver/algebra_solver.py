"""Algebra problem solver."""

import logging
import re
from typing import List, Optional

from sympy import Eq, Symbol, Poly, solve, simplify
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor

from .models import StepSolverResult, ProblemType

logger = logging.getLogger(__name__)


def _clean_input(problem: str) -> str:
    """Normalize algebra input for SymPy parsing."""
    if not isinstance(problem, str):
        return ""

    cleaned = problem.strip()
    cleaned = cleaned.replace("²", "**2")
    return cleaned


def _parse_expression(expr_str: str) -> Optional[object]:
    """Parse a mathematical expression string into a SymPy expression."""
    try:
        return parse_expr(
            expr_str,
            transformations=(standard_transformations + (implicit_multiplication_application, convert_xor)),
            evaluate=False,
        )
    except Exception as e:
        logger.debug(f"Unable to parse expression '{expr_str}': {e}")
        return None


def _extract_equation_parts(problem: str) -> Optional[tuple]:
    """Split the input into left-hand side and right-hand side."""
    if not problem or "=" not in problem:
        return None

    parts = problem.split("=", 1)
    if len(parts) != 2:
        return None

    lhs = parts[0].strip()
    rhs = parts[1].strip()
    if not lhs or not rhs:
        return None

    return lhs, rhs


def _identify_variable(lhs_expr, rhs_expr) -> Optional[Symbol]:
    """Identify the single variable in the equation."""
    symbols = lhs_expr.free_symbols.union(rhs_expr.free_symbols)
    if len(symbols) != 1:
        return None
    return symbols.pop()


def _format_solution_value(value) -> str:
    """Format a SymPy solution value for display."""
    try:
        simplified = simplify(value)
        if simplified.is_real and simplified.is_integer:
            return str(int(simplified))
        result = str(simplified)
        if result.endswith('.0000000000000'):
            return result[:-16]
        return result
    except Exception:
        return str(value)


def _generate_linear_steps(problem: str, lhs_expr, rhs_expr, variable: Symbol) -> (List[str], str):
    """Generate educational steps for a linear equation."""
    equation = Eq(lhs_expr, rhs_expr)
    constant_part = lhs_expr.subs(variable, 0)
    moved_lhs = simplify(lhs_expr - constant_part)
    moved_rhs = simplify(rhs_expr - constant_part)

    if constant_part == 0:
        step2_description = "Isolate the variable."
    elif constant_part.is_negative:
        step2_description = f"Add {abs(constant_part)} to both sides."
    else:
        step2_description = f"Subtract {constant_part} from both sides."

    solutions = solve(equation, variable)
    if not solutions:
        raise ValueError("No solution found for the linear equation.")

    coefficient = moved_lhs.coeff(variable)
    if coefficient == 1:
        step3_description = "Calculate."
    else:
        step3_description = f"Divide by {coefficient}."

    solution_value = _format_solution_value(solutions[0])
    final_answer = f"{variable} = {solution_value}"

    steps = [
        f"Step 1: Identify the equation\n{problem}",
        f"Step 2: {step2_description}\n{moved_lhs} = {moved_rhs}",
        f"Step 3: {step3_description}\n{final_answer}",
    ]
    return steps, final_answer


def _generate_quadratic_steps(problem: str, lhs_expr, rhs_expr, variable: Symbol) -> (List[str], str):
    """Generate educational steps for a quadratic equation."""
    equation = Eq(lhs_expr, rhs_expr)
    solutions = solve(equation, variable)
    if not solutions:
        raise ValueError("No roots found for the quadratic equation.")

    formatted_roots = [_format_solution_value(root) for root in solutions]
    root_lines = [f"{variable} = {value}" for value in formatted_roots]
    final_answer = f"{variable} = {', '.join(formatted_roots)}"
    roots_display = "\n".join(root_lines)

    steps = [
        f"Step 1: Identify the quadratic equation\n{problem}",
        f"Step 2: Solve for the variable\n{roots_display}",
        f"Step 3: Final answer\n{final_answer}",
    ]
    return steps, final_answer


def solve_algebra(problem: str) -> StepSolverResult:
    """Solve algebra equations step-by-step."""
    cleaned_problem = _clean_input(problem)
    if not cleaned_problem:
        return StepSolverResult(
            problem_type=ProblemType.ALGEBRA,
            input_expression=str(problem),
            steps=[],
            final_answer="Invalid algebra input",
            success=False,
        )

    equation_parts = _extract_equation_parts(cleaned_problem)
    if equation_parts is None:
        return StepSolverResult(
            problem_type=ProblemType.ALGEBRA,
            input_expression=problem,
            steps=[],
            final_answer="Please provide an equation with one '=' sign.",
            success=False,
        )

    lhs, rhs = equation_parts
    lhs_expr = _parse_expression(lhs)
    rhs_expr = _parse_expression(rhs)

    if lhs_expr is None or rhs_expr is None:
        return StepSolverResult(
            problem_type=ProblemType.ALGEBRA,
            input_expression=problem,
            steps=[],
            final_answer="Unable to parse the equation.",
            success=False,
        )

    variable = _identify_variable(lhs_expr, rhs_expr)
    if variable is None:
        return StepSolverResult(
            problem_type=ProblemType.ALGEBRA,
            input_expression=problem,
            steps=[],
            final_answer="Unable to identify a single variable to solve for.",
            success=False,
        )

    try:
        polynomial = Poly(lhs_expr - rhs_expr, variable)
        degree = polynomial.degree()
    except Exception:
        return StepSolverResult(
            problem_type=ProblemType.ALGEBRA,
            input_expression=problem,
            steps=[],
            final_answer="Equation type not supported. Only linear and quadratic equations are supported.",
            success=False,
        )

    try:
        if degree == 1:
            steps, final_answer = _generate_linear_steps(problem, lhs_expr, rhs_expr, variable)
        elif degree == 2:
            steps, final_answer = _generate_quadratic_steps(problem, lhs_expr, rhs_expr, variable)
        else:
            return StepSolverResult(
                problem_type=ProblemType.ALGEBRA,
                input_expression=problem,
                steps=[],
                final_answer="Equation type not supported. Only linear and quadratic equations are supported.",
                success=False,
            )

        return StepSolverResult(
            problem_type=ProblemType.ALGEBRA,
            input_expression=problem,
            steps=steps,
            final_answer=final_answer,
            success=True,
        )
    except Exception as e:
        logger.debug(f"Algebra solver error: {e}")
        return StepSolverResult(
            problem_type=ProblemType.ALGEBRA,
            input_expression=problem,
            steps=[],
            final_answer="Unable to solve the algebra equation.",
            success=False,
        )
