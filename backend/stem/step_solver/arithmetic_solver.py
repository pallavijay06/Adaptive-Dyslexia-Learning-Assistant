"""Arithmetic problem solver with step-by-step educational output.

Solves arithmetic expressions following order of operations (PEMDAS):
1. Parentheses
2. Exponents
3. Multiplication / Division
4. Addition / Subtraction

Uses SymPy for safe expression parsing and evaluation.
"""

import re
import logging
from typing import List, Tuple, Optional

from sympy import sympify, simplify, expand
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
from sympy.core.sympify import SympifyError

from .models import StepSolverResult, ProblemType

logger = logging.getLogger(__name__)


def _clean_expression(expr_str: str) -> str:
    """
    Clean and normalize arithmetic expression.

    Conversions:
    - ^ to ** (exponent operator)
    - Removes extra whitespace
    - Maintains parentheses

    Args:
        expr_str: Raw expression string

    Returns:
        Cleaned expression string
    """
    # Replace ^ with ** for exponentiation
    cleaned = expr_str.replace("^", "**")
    # Remove extra whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned


def _safe_parse_expression(expr_str: str):
    """
    Safely parse an arithmetic expression using SymPy.

    Args:
        expr_str: Expression to parse

    Returns:
        Parsed SymPy expression or None if parsing fails
    """
    try:
        # Use parse_expr with transformations for implicit multiplication
        transformations = (standard_transformations + (implicit_multiplication_application,))
        expr = parse_expr(expr_str, transformations=transformations)
        return expr
    except Exception:
        try:
            # Fallback to sympify for simple expressions
            expr = sympify(expr_str)
            return expr
        except Exception as e:
            logger.warning(f"Failed to parse expression '{expr_str}': {e}")
            return None


def _generate_arithmetic_steps(problem: str) -> Tuple[List[str], Optional[str], bool]:
    """
    Generate step-by-step solution for arithmetic expression.

    Args:
        problem: Arithmetic expression

    Returns:
        Tuple of (steps, final_answer, success)
    """
    steps = []
    current_expr = _clean_expression(problem)
    original_expr = current_expr

    try:
        # Validate expression can be parsed
        original_parsed = _safe_parse_expression(current_expr)
        if original_parsed is None:
            return [], f"Unable to parse expression: {problem}", False

        steps.append(f"Original expression: {original_expr}")

        # Handle parentheses step by step
        while "(" in current_expr and ")" in current_expr:
            # Find innermost parentheses
            innermost = None
            start_idx = -1

            for i, char in enumerate(current_expr):
                if char == "(":
                    start_idx = i
                elif char == ")":
                    if start_idx != -1:
                        innermost = current_expr[start_idx + 1 : i]
                        break

            if innermost is None:
                break

            try:
                # Evaluate the innermost expression
                result = _safe_parse_expression(innermost)
                if result is None:
                    break

                result_simplified = simplify(result)
                step = f"Evaluate parentheses: ({innermost}) = {result_simplified}"
                if step not in steps:
                    steps.append(step)

                # Replace the parenthesized expression with its result
                new_expr = (
                    current_expr[:start_idx]
                    + str(result_simplified)
                    + current_expr[current_expr.find(")", start_idx) + 1 :]
                )
                current_expr = new_expr.strip()
            except Exception as e:
                logger.warning(f"Error evaluating parentheses: {e}")
                break

        # Handle exponents
        exponent_pattern = r"(\d+)\*\*(\d+)"
        while re.search(exponent_pattern, current_expr):
            match = re.search(exponent_pattern, current_expr)
            if match:
                base = int(match.group(1))
                exp = int(match.group(2))
                result = base ** exp

                step = f"Calculate exponent: {base}^{exp} = {result}"
                if step not in steps:
                    steps.append(step)

                current_expr = current_expr[: match.start()] + str(result) + current_expr[match.end() :]

        # Final evaluation
        try:
            parsed = _safe_parse_expression(current_expr)
            if parsed is None:
                raise ValueError("Could not parse final expression")

            final_simplified = simplify(parsed)

            # Add final step if different from current
            if str(final_simplified) != current_expr and not any(
                str(final_simplified) in step for step in steps
            ):
                steps.append(f"Simplify: {current_expr} = {final_simplified}")

            final_answer = str(final_simplified)
            return steps, final_answer, True

        except Exception as e:
            logger.warning(f"Error in final evaluation: {e}")
            # Try to evaluate anyway with simplify
            try:
                parsed = _safe_parse_expression(current_expr)
                if parsed:
                    final_answer = str(simplify(parsed))
                    return steps, final_answer, True
            except Exception:
                pass

            return steps, None, False

    except Exception as e:
        logger.error(f"Unexpected error in arithmetic solver: {e}")
        return [], "Unable to solve expression", False


def solve_arithmetic(problem: str) -> StepSolverResult:
    """
    Solve arithmetic problems step-by-step.

    Solves expressions like:
    - 10 + 5 * 2
    - (8 + 2) * 3
    - 3^2 + 4^2
    - 100 - 25
    - 20 / 4

    Args:
        problem: The arithmetic problem to solve

    Returns:
        StepSolverResult with steps and final answer

    Example:
        >>> result = solve_arithmetic("10 + 5 * 2")
        >>> result.success
        True
        >>> result.final_answer
        '20'
        >>> len(result.steps) > 0
        True
    """
    if not problem or not isinstance(problem, str):
        return StepSolverResult(
            problem_type=ProblemType.ARITHMETIC,
            input_expression=str(problem),
            steps=[],
            final_answer="Invalid input",
            success=False,
        )

    # Generate steps
    steps, final_answer, success = _generate_arithmetic_steps(problem)

    # Build readable step descriptions with one logical action per step
    readable_steps = []
    for i, step in enumerate(steps, 1):
        if ": " in step:
            title, content = step.split(": ", 1)
            readable_steps.append(f"Step {i}: {title}\n{content}")
        else:
            readable_steps.append(f"Step {i}: {step}")

    return StepSolverResult(
        problem_type=ProblemType.ARITHMETIC,
        input_expression=problem,
        steps=readable_steps,
        final_answer=final_answer,
        success=success,
    )
