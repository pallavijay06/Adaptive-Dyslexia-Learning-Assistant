# Step-by-Step Solver Module

## Purpose

The Step Solver module provides step-by-step solutions for STEM problems to help dyslexic students understand mathematical and scientific problem-solving processes. This module breaks down complex problems into manageable, sequential steps that improve comprehension and learning outcomes.

## Supported Problem Categories

### Current (Planned Implementation)

- **Arithmetic**: Basic numerical operations with detailed step-by-step breakdown
- **Simple Algebra**: Algebraic equations and expression manipulation
- **Formula Substitution**: Substituting values into formulas and solving
- **Formula Rearrangement**: Rearranging formulas to solve for different variables

## Architecture

### Component Overview

```
Question
  ↓
Detector (detect_problem_type)
  ↓
Problem Type Classification
  ↓
Specialized Solver (arithmetic/algebra/substitution/rearrangement)
  ↓
Step-by-Step Output (StepSolverResult)
```

### Key Components

1. **models.py**: Data structures
   - `ProblemType` enum: Problem classification
   - `StepSolverResult` dataclass: Solution output format

2. **detector.py**: Problem type detection
   - `detect_problem_type()`: Analyzes input and classifies problem

3. **Solvers**: Problem-specific solvers
   - `arithmetic_solver.py`: Arithmetic problem solver
   - `algebra_solver.py`: Algebra problem solver
   - `substitution_solver.py`: Formula substitution solver
   - `rearrangement_solver.py`: Formula rearrangement solver

4. **solver_service.py**: Main orchestration service
   - `solve_problem()`: Unified entry point that routes to appropriate solver

5. **__init__.py**: Module exports

## Data Structures

### ProblemType Enum

```python
class ProblemType(Enum):
    ARITHMETIC = "arithmetic"
    ALGEBRA = "algebra"
    SUBSTITUTION = "substitution"
    REARRANGEMENT = "rearrangement"
    UNKNOWN = "unknown"
```

### StepSolverResult

```python
@dataclass
class StepSolverResult:
    problem_type: ProblemType
    input_expression: str
    steps: List[str]                    # Sequential solution steps
    final_answer: Optional[str]          # Final computed answer
    success: bool                        # Whether solving succeeded
```

## Future Workflow

### Detailed Process Flow

1. **Input Reception**
   - User provides a mathematical problem or equation

2. **Problem Detection**
   - Detector analyzes the input
   - Classifies as ARITHMETIC, ALGEBRA, SUBSTITUTION, REARRANGEMENT, or UNKNOWN

3. **Solver Selection**
   - Router directs to appropriate solver based on classification
   - Each solver specializes in its problem type

4. **Solution Generation**
   - Solver breaks problem into logical steps
   - Each step is human-readable and accessible
   - Special consideration for dyslexic learning needs

5. **Result Output**
   - Returns StepSolverResult with:
     - Problem classification
     - Sequential steps (list)
     - Final answer
     - Success status

## Future Integration

This module will integrate with:
- Formula Assistant: For formula recognition
- Symbol Explanation: For symbol meanings
- Diagram Explanation: For visual representations of steps
- Reading Experience: For accessible presentation of steps

## Development Status

- ✅ Architecture and scaffolding
- ⏳ Detection logic
- ⏳ Arithmetic solver implementation
- ⏳ Algebra solver implementation
- ⏳ Substitution solver implementation
- ⏳ Rearrangement solver implementation
- ⏳ UI integration
- ⏳ Testing suite

## Notes for Implementers

- Solvers must return `StepSolverResult` objects
- Each step should be a clear, single operation
- Consider accessibility: avoid overly technical terminology
- Use SymPy for symbolic mathematics when needed
- Log all solving operations for debugging
