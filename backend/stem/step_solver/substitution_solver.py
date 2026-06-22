"""Formula substitution problem solver with step-by-step educational output.

Solves formula substitution problems by:
1. Parsing the formula
2. Extracting variable assignments
3. Validating all variables have values
4. Substituting variables one at a time
5. Performing calculations
6. Displaying final answer

Uses SymPy for safe expression parsing and symbolic substitution.
"""

import logging
import re
from typing import Dict, List, Tuple, Optional

from sympy import symbols, sympify, simplify, Symbol, Expr
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor

from .models import StepSolverResult, ProblemType

logger = logging.getLogger(__name__)


def _parse_formula_and_assignments(problem: str) -> Tuple[Optional[str], Dict[str, float]]:
    """
    Parse problem text to extract formula and variable assignments.

    Args:
        problem: Problem text with formula and assignments

    Returns:
        Tuple of (formula_str, assignments_dict) or (None, {}) if parsing fails
    """
    lines = problem.strip().split("\n")
    if not lines:
        return None, {}

    # First line should be the formula
    formula_line = lines[0].strip()

    # Validate formula contains =
    if "=" not in formula_line:
        return None, {}

    # Extract assignments from remaining lines
    assignments = {}
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        if "=" in line:
            parts = line.split("=")
            if len(parts) == 2:
                var_name = parts[0].strip()
                try:
                    value = float(parts[1].strip())
                    assignments[var_name] = value
                except ValueError:
                    # Skip lines that don't have numeric values
                    pass

    return formula_line, assignments


def _extract_formula_parts(formula_str: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract left-hand side and right-hand side of formula.

    Args:
        formula_str: Formula string (e.g., "F = ma")

    Returns:
        Tuple of (lhs, rhs) or (None, None) if invalid
    """
    if "=" not in formula_str:
        return None, None

    parts = formula_str.split("=", 1)
    if len(parts) != 2:
        return None, None

    lhs = parts[0].strip()
    rhs = parts[1].strip()

    return lhs, rhs


def _parse_sympy_expression(expr_str: str, local_dict: Optional[Dict[str, Symbol]] = None):
    """
    Parse an expression string with SymPy, applying implicit multiplication and caret conversion.

    Args:
        expr_str: Expression string to parse.
        local_dict: Optional mapping of variable names to Symbol objects.

    Returns:
        SymPy expression or None if parsing fails.
    """
    try:
        if local_dict is None:
            tokens = re.findall(r"[A-Za-z]+", expr_str)
            parsed_tokens = []
            for token in tokens:
                if token.isupper() and len(token) > 1:
                    parsed_tokens.extend(list(token))
                else:
                    parsed_tokens.append(token)
            local_dict = {token: Symbol(token) for token in set(parsed_tokens)}

        return parse_expr(
            expr_str,
            transformations=(standard_transformations + (implicit_multiplication_application, convert_xor)),
            local_dict=local_dict,
            evaluate=False,
        )
    except Exception as e:
        logger.warning(f"Error parsing expression '{expr_str}': {e}")
        return None


def _get_variables_from_expression(expr_str: str, assignments: Optional[Dict[str, float]] = None) -> set:
    """
    Extract all variables from an expression.

    Args:
        expr_str: Expression string
        assignments: Optional variable assignments to guide parsing

    Returns:
        Set of variable names
    """
    local_dict = None
    if assignments:
        local_dict = {name: Symbol(name) for name in assignments.keys()}

    expr = _parse_sympy_expression(expr_str, local_dict=local_dict)
    if expr is None:
        return set()

    return {str(sym) for sym in expr.free_symbols}


def _validate_all_variables_assigned(
    formula_rhs: str, assignments: Dict[str, float]
) -> Tuple[bool, Optional[str]]:
    """
    Validate that all variables in formula have assigned values.

    Args:
        formula_rhs: Right-hand side of formula
        assignments: Dictionary of variable assignments

    Returns:
        Tuple of (is_valid, error_message)
    """
    variables = _get_variables_from_expression(formula_rhs, assignments=assignments)

    for var in variables:
        if var not in assignments:
            return False, f"Value for variable '{var}' is missing"

    return True, None


def _format_result(expr) -> str:
    """
    Format result for display.

    Converts to integer if result is a whole number.

    Args:
        expr: SymPy expression

    Returns:
        Formatted result string
    """
    if expr is None:
        return ""

    result_str = str(expr)

    try:
        if expr.is_real:
            if expr.is_integer:
                return str(int(expr))
            if hasattr(expr, 'evalf'):
                float_value = float(expr.evalf())
                if float_value.is_integer():
                    return str(int(float_value))
                return str(float_value).rstrip('0').rstrip('.')
    except Exception:
        pass

    # Fallback string normalization for decimal artifacts
    if result_str.endswith('.0000000000000'):
        return result_str[: -len('.0000000000000')]
    if result_str.endswith('.0'):
        return result_str[: -2]

    return result_str


def _substitute_and_simplify_step_by_step(
    formula_rhs: str, assignments: Dict[str, float], lhs: str
) -> Tuple[List[str], Optional[str], bool]:
    """
    Perform substitutions step by step and generate steps.

    Args:
        formula_rhs: Right-hand side of formula
        assignments: Variable assignments
        lhs: Left-hand side of formula (for display)

    Returns:
        Tuple of (steps, final_answer, success)
    """
    steps = []
    current_expr_str = formula_rhs

    try:
        # Parse the formula using assignment names to preserve the intended variables.
        local_dict = {var_name: Symbol(var_name) for var_name in assignments.keys()}
        current_expr = parse_expr(
            current_expr_str,
            transformations=(standard_transformations + (implicit_multiplication_application, convert_xor)),
            local_dict=local_dict,
            evaluate=False,
        )

        # Step 1: Display original formula
        steps.append(f"Original Formula: {lhs} = {formula_rhs}")

        # Step 2-N: Substitute each variable
        for var_name, value in assignments.items():
            # Check if variable is in current expression
            if var_name not in str(current_expr):
                continue

            # Display substitution step
            steps.append(f"Substitute {var_name} = {value}: {lhs} = {current_expr}")

            # Perform substitution
            var_symbol = Symbol(var_name)
            current_expr = current_expr.subs(var_symbol, value)

            # Simplify after substitution
            current_expr = simplify(current_expr)

        # Final calculation
        final_simplified = simplify(current_expr)
        steps.append(f"Calculate: {lhs} = {final_simplified}")

        final_answer = _format_result(final_simplified)
        return steps, final_answer, True

    except Exception as e:
        logger.warning(f"Error in substitution: {e}")
        return [], "Unable to calculate result", False


def _format_expression_for_display(expr_str: str) -> str:
    """
    Format expression for display (replace ** with ^, * with ×).

    Args:
        expr_str: Expression string

    Returns:
        Formatted expression string
    """
    # Replace ^ with ** for parsing, then display with ^
    formatted = expr_str.replace("^", "**")
    formatted = formatted.replace("**", "^")
    # Optionally replace * with × for display (but keep for parsing)
    return formatted


def solve_substitution(problem: str) -> StepSolverResult:
    """
    Solve formula substitution problems step-by-step.

    Solves problems like:
    - F = ma with m = 5, a = 2
    - V = IR with I = 2, R = 5
    - P = VI with V = 12, I = 3
    - KE = 0.5 * m * v^2 with m = 10, v = 4

    Args:
        problem: The substitution problem text

    Returns:
        StepSolverResult with steps and final answer

    Example:
        >>> result = solve_substitution("F = ma\\nm = 5\\na = 2")
        >>> result.success
        True
        >>> result.final_answer
        '10'
    """
    if not problem or not isinstance(problem, str):
        return StepSolverResult(
            problem_type=ProblemType.SUBSTITUTION,
            input_expression=str(problem),
            steps=[],
            final_answer="Invalid input",
            success=False,
        )

    try:
        # Parse formula and assignments
        formula_str, assignments = _parse_formula_and_assignments(problem)

        if not formula_str:
            return StepSolverResult(
                problem_type=ProblemType.SUBSTITUTION,
                input_expression=problem,
                steps=[],
                final_answer="Unable to parse formula",
                success=False,
            )

        # Extract left and right sides of formula
        lhs, rhs = _extract_formula_parts(formula_str)

        if not lhs or not rhs:
            return StepSolverResult(
                problem_type=ProblemType.SUBSTITUTION,
                input_expression=problem,
                steps=[],
                final_answer="Invalid formula format",
                success=False,
            )

        # Validate all variables have assignments
        is_valid, error_msg = _validate_all_variables_assigned(rhs, assignments)

        if not is_valid:
            return StepSolverResult(
                problem_type=ProblemType.SUBSTITUTION,
                input_expression=problem,
                steps=[],
                final_answer=error_msg,
                success=False,
            )

        # Perform substitution and calculate
        steps, final_answer, success = _substitute_and_simplify_step_by_step(rhs, assignments, lhs)

        if not success:
            return StepSolverResult(
                problem_type=ProblemType.SUBSTITUTION,
                input_expression=problem,
                steps=steps,
                final_answer=final_answer,
                success=False,
            )

        # Format steps for readability with one logical action per step
        readable_steps = []
        for i, step in enumerate(steps, 1):
            if ": " in step:
                title, content = step.split(": ", 1)
                readable_steps.append(f"Step {i}: {title}\n{content}")
            else:
                readable_steps.append(f"Step {i}: {step}")

        return StepSolverResult(
            problem_type=ProblemType.SUBSTITUTION,
            input_expression=problem,
            steps=readable_steps,
            final_answer=final_answer,
            success=success,
        )

    except Exception as e:
        logger.error(f"Unexpected error in substitution solver: {e}")
        return StepSolverResult(
            problem_type=ProblemType.SUBSTITUTION,
            input_expression=problem,
            steps=[],
            final_answer="Unable to solve substitution problem",
            success=False,
        )
