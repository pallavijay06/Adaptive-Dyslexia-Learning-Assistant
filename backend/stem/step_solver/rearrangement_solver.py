"""Formula rearrangement problem solver."""

import logging
import re
from typing import Dict, List, Optional

from sympy import Eq, Symbol, solve, simplify
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor

from .models import StepSolverResult, ProblemType

logger = logging.getLogger(__name__)


def _clean_input(problem: str) -> str:
    """Normalize formula input for SymPy parsing."""
    if not isinstance(problem, str):
        return ""

    cleaned = problem.strip()
    cleaned = cleaned.replace("²", "**2")
    return cleaned


def _tokenize_symbols(text: str) -> set[str]:
    """Extract candidate symbol names from input text."""
    tokens = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text)
    keywords = {"find", "solve", "for"}
    return {token for token in tokens if token.lower() not in keywords}


def _build_local_dict(lines: List[str], lhs_var: Optional[str] = None, target: Optional[str] = None) -> Dict[str, Symbol]:
    """Build a local SymPy symbol dictionary for key variables."""
    assignments = set(_parse_assignments(lines).keys())
    local_symbols = set(assignments)

    if lhs_var:
        local_symbols.add(lhs_var)
    if target:
        local_symbols.add(target)

    return {name: Symbol(name) for name in local_symbols}


def _parse_expression(expr_str: str, local_dict: Optional[Dict[str, Symbol]] = None):
    """Parse a mathematical expression into SymPy."""
    try:
        return parse_expr(
            expr_str,
            transformations=(standard_transformations + (implicit_multiplication_application, convert_xor)),
            local_dict=local_dict,
            evaluate=False,
        )
    except Exception as e:
        logger.debug(f"Unable to parse expression '{expr_str}': {e}")
        return None


def _is_target_line(line: str) -> Optional[str]:
    """Extract the target variable from a Find/Solve line."""
    match = re.match(r"^(?:find|solve for)\s+([A-Za-z][A-Za-z0-9_]*)$", line, re.IGNORECASE)
    return match.group(1) if match else None


def _is_assignment_line(line: str) -> bool:
    """Detect if a line is a variable assignment."""
    if "=" not in line:
        return False

    parts = line.split("=", 1)
    if len(parts) != 2:
        return False

    lhs, rhs = parts[0].strip(), parts[1].strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", lhs):
        return False

    try:
        float(rhs)
        return True
    except ValueError:
        return False


def _parse_assignments(lines: List[str]) -> Dict[str, float]:
    """Parse numeric variable assignments from input lines."""
    assignments: Dict[str, float] = {}
    for line in lines:
        if _is_assignment_line(line):
            lhs, rhs = [part.strip() for part in line.split("=", 1)]
            try:
                assignments[lhs] = float(rhs)
            except ValueError:
                continue
    return assignments


def _extract_formula_line(lines: List[str]) -> Optional[str]:
    """Find the primary formula line among input lines."""
    candidates = [line for line in lines if "=" in line and _is_target_line(line) is None]
    non_assignments = [line for line in candidates if not _is_assignment_line(line)]
    if non_assignments:
        return non_assignments[0]
    return None


def _target_variable(lines: List[str]) -> Optional[str]:
    """Extract the target variable from the input lines."""
    for line in lines:
        found = _is_target_line(line)
        if found:
            return found
    return None


def _format_result(value) -> str:
    """Format a SymPy result for clean display."""
    try:
        simplified = simplify(value)
        if simplified.is_real:
            if simplified.is_integer:
                return str(int(simplified))
            try:
                float_val = float(simplified)
                if float_val.is_integer():
                    return str(int(float_val))
            except Exception:
                pass
        result = str(simplified)
        if result.endswith('.0000000000000'):
            return result[:-16]
        if result.endswith('.0'):
            return result[:-2]
        return result
    except Exception:
        return str(value)


def _choose_solution(solutions, target_symbol: Symbol, assignments: Dict[str, float]):
    """Select the preferred solution when multiple rearrangements exist."""
    if not solutions:
        return None
    if len(solutions) == 1:
        return solutions[0]

    numeric_solutions = []
    subs_map = {Symbol(name): value for name, value in assignments.items()}
    for sol in solutions:
        try:
            substituted = sol.subs(subs_map)
            evaluated = substituted.evalf()
            if evaluated.is_real:
                numeric_solutions.append((float(evaluated), sol))
        except Exception:
            continue

    positive_options = [item for item in numeric_solutions if item[0] >= 0]
    if positive_options:
        return positive_options[0][1]
    if numeric_solutions:
        return numeric_solutions[0][1]
    return solutions[0]


def solve_rearrangement(problem: str) -> StepSolverResult:
    """Solve formula rearrangement problems step-by-step."""
    cleaned_problem = _clean_input(problem)
    if not cleaned_problem:
        return StepSolverResult(
            problem_type=ProblemType.REARRANGEMENT,
            input_expression=str(problem),
            steps=[],
            final_answer="Invalid rearrangement input",
            success=False,
        )

    lines = [line.strip() for line in cleaned_problem.splitlines() if line.strip()]
    if not lines:
        return StepSolverResult(
            problem_type=ProblemType.REARRANGEMENT,
            input_expression=problem,
            steps=[],
            final_answer="No input provided",
            success=False,
        )

    target = _target_variable(lines)
    formula_line = _extract_formula_line(lines)
    assignments = _parse_assignments(lines)

    if target is None:
        return StepSolverResult(
            problem_type=ProblemType.REARRANGEMENT,
            input_expression=problem,
            steps=[],
            final_answer="Target variable not specified. Use 'Find <variable>' or 'Solve for <variable>'.",
            success=False,
        )

    if formula_line is None:
        return StepSolverResult(
            problem_type=ProblemType.REARRANGEMENT,
            input_expression=problem,
            steps=[],
            final_answer="Formula not found in input.",
            success=False,
        )

    if target not in formula_line:
        return StepSolverResult(
            problem_type=ProblemType.REARRANGEMENT,
            input_expression=problem,
            steps=[],
            final_answer=f"Target variable '{target}' not present in the formula.",
            success=False,
        )

    if "=" not in formula_line:
        return StepSolverResult(
            problem_type=ProblemType.REARRANGEMENT,
            input_expression=problem,
            steps=[],
            final_answer="Invalid formula format.",
            success=False,
        )

    lhs_text, rhs_text = [part.strip() for part in formula_line.split("=", 1)]
    local_dict = _build_local_dict(lines, lhs_var=lhs_text, target=target)
    lhs_expr = _parse_expression(lhs_text, local_dict=local_dict)
    rhs_expr = _parse_expression(rhs_text, local_dict=local_dict)

    if lhs_expr is None or rhs_expr is None:
        return StepSolverResult(
            problem_type=ProblemType.REARRANGEMENT,
            input_expression=problem,
            steps=[],
            final_answer="Unable to parse the formula.",
            success=False,
        )

    target_symbol = Symbol(target)
    equation = Eq(lhs_expr, rhs_expr)

    try:
        solutions = solve(equation, target_symbol)
    except Exception as e:
        logger.debug(f"Unable to rearrange formula: {e}")
        return StepSolverResult(
            problem_type=ProblemType.REARRANGEMENT,
            input_expression=problem,
            steps=[],
            final_answer="Unable to rearrange the formula for the target variable.",
            success=False,
        )

    if not solutions:
        return StepSolverResult(
            problem_type=ProblemType.REARRANGEMENT,
            input_expression=problem,
            steps=[],
            final_answer=f"No rearranged expression found for '{target}'.",
            success=False,
        )

    selected_solution = _choose_solution(solutions, target_symbol, assignments)
    if selected_solution is None:
        return StepSolverResult(
            problem_type=ProblemType.REARRANGEMENT,
            input_expression=problem,
            steps=[],
            final_answer="Unable to choose a rearranged result.",
            success=False,
        )

    rearranged = simplify(selected_solution)
    substitution_map = {Symbol(name): value for name, value in assignments.items()}
    substituted = rearranged.subs(substitution_map)

    missing_symbols = substituted.free_symbols
    if missing_symbols:
        missing_vars = ", ".join(sorted(str(symbol) for symbol in missing_symbols))
        return StepSolverResult(
            problem_type=ProblemType.REARRANGEMENT,
            input_expression=problem,
            steps=[],
            final_answer=f"Missing values for: {missing_vars}",
            success=False,
        )

    formatted_substituted = _format_result(substituted)
    calculated = simplify(substituted)
    final_answer = f"{target} = {_format_result(calculated)}"

    formatted_substituted = _format_result(substituted)
    steps = [
        f"Step 1: Original Formula\n{formula_line}",
        f"Step 2: Identify target variable\n{target}",
        f"Step 3: Rearrange formula\n{target} = {rearranged}",
        f"Step 4: Substitute values\n{target} = {formatted_substituted}",
        f"Step 5: Final Answer\n{final_answer}",
    ]

    return StepSolverResult(
        problem_type=ProblemType.REARRANGEMENT,
        input_expression=problem,
        steps=steps,
        final_answer=final_answer,
        success=True,
    )
