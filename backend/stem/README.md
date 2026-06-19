# STEM Support Module

This folder contains the isolated Phase 1 framework for Prototype 3 STEM
Support in the Adaptive Dyslexia Learning Assistant.

## Purpose

The STEM module provides a focused backend layer for detecting STEM content in
extracted document text. It is self-contained and is not wired into `app.py`,
quiz modules, document-processing pipelines, visual modules, audio modules, OCR
modules, or simplification modules.

Planned feature areas:

- Formula Assistant
- Symbol Explanation
- Diagram Explanation
- Step-by-Step Solutions
- Scientific Vocabulary Simplification

## Proposed Architecture

- `detector.py`: Lightweight placeholder detection for formulas, symbols, and
  diagram-related keywords.
- `models.py`: Dataclasses and response schemas shared across STEM features,
  including `STEMDetectionResult`.
- `constants.py`: Constants for STEM symbols, formula tokens, and diagram
  keywords.
- `stem_service.py`: High-level orchestration layer that exposes document
  analysis and placeholder feature registry functions.
- `__init__.py`: Package marker and package-level documentation.
- `test_detector.py`: Local tests for the Phase 1 detection framework.

## Phase 1 Output

`analyze_document_for_stem(text)` returns a `STEMDetectionResult` with:

- `has_formula`
- `has_symbols`
- `has_diagrams`
- `formula_count`
- `symbol_count`
- `diagram_count`

`get_available_stem_features(result)` returns placeholder feature names based on
the detected content:

- Formula content enables `Formula Assistant` and `Step-by-Step Solutions`.
- Symbol content enables `Symbol Explanation`.
- Diagram content enables `Diagram Explanation`.

## Roadmap

1. Replace placeholder formula token detection with a math-aware parser.
2. Add contextual Symbol Explanation services.
3. Add Diagram Explanation services for extracted or uploaded visual content.
4. Add Step-by-Step Solutions services for detected formulas and problems.
5. Connect the orchestration layer to approved backend routes or UI workflows.
6. Add focused tests for each STEM feature area.

No Formula Assistant, Symbol Explanation, Diagram Explanation, or Step-by-Step
Solutions implementation is included in Phase 1.
