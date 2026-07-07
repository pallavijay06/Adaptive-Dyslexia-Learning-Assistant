"""STEM API routes — exposes existing STEM services through Flask endpoints."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request

from backend.stem.formula_assistant import explain_formula, get_formula_explanations
from backend.stem.symbol_assistant import explain_symbol, get_symbol_explanations
from backend.stem.diagram_explainer import explain_diagram
from backend.stem.stem_controller import process_stem_support
from backend.stem.formula_extractor import extract_formulas
from backend.stem.symbol_extractor import extract_symbols
from services.behavior_tracking_service import (
    track_formula_assistant_used,
    track_symbol_explanation_used,
    track_diagram_explanation_used,
    track_step_solver_used,
)

stem_bp = Blueprint("stem", __name__, url_prefix="/stem")
logger = logging.getLogger(__name__)


def _user_id_from_body(data: dict) -> int | None:
    uid = data.get("user_id")
    try:
        return int(uid) if uid is not None else None
    except (TypeError, ValueError):
        return None


@stem_bp.post("/formula/explain")
def formula_explain():
    """Explain a single formula in dyslexia-friendly language."""
    data = request.get_json(silent=True) or {}
    formula = (data.get("formula") or "").strip()
    if not formula:
        return jsonify({"success": False, "error": "formula is required."}), 400

    try:
        result = explain_formula(formula)
        uid = _user_id_from_body(data)
        if uid:
            track_formula_assistant_used(uid, metadata={"formula": formula})
        return jsonify({"success": True, "explanation": result}), 200
    except Exception:
        logger.exception("Formula explain failed")
        return jsonify({"success": False, "error": "Formula explanation failed."}), 500


@stem_bp.post("/formula/extract")
def formula_extract():
    """Extract and explain all formulas found in document text."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"success": False, "error": "text is required."}), 400

    try:
        formulas = extract_formulas(text)
        explanations = get_formula_explanations(text)
        uid = _user_id_from_body(data)
        if uid:
            track_formula_assistant_used(uid, metadata={"formula_count": len(formulas)})
        return jsonify({"success": True, "formulas": formulas, "explanations": explanations}), 200
    except Exception:
        logger.exception("Formula extract failed")
        return jsonify({"success": False, "error": "Formula extraction failed."}), 500


@stem_bp.post("/symbol/explain")
def symbol_explain():
    """Explain a single STEM symbol."""
    data = request.get_json(silent=True) or {}
    symbol = (data.get("symbol") or "").strip()
    if not symbol:
        return jsonify({"success": False, "error": "symbol is required."}), 400

    try:
        result = explain_symbol(symbol)
        uid = _user_id_from_body(data)
        if uid:
            track_symbol_explanation_used(uid, metadata={"symbol": symbol})
        return jsonify({"success": True, "explanation": result}), 200
    except Exception:
        logger.exception("Symbol explain failed")
        return jsonify({"success": False, "error": "Symbol explanation failed."}), 500


@stem_bp.post("/symbol/extract")
def symbol_extract():
    """Extract and explain all STEM symbols found in document text."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"success": False, "error": "text is required."}), 400

    try:
        symbols = extract_symbols(text)
        explanations = get_symbol_explanations(text)
        uid = _user_id_from_body(data)
        if uid:
            track_symbol_explanation_used(uid, metadata={"symbol_count": len(symbols)})
        return jsonify({"success": True, "symbols": symbols, "explanations": explanations}), 200
    except Exception:
        logger.exception("Symbol extract failed")
        return jsonify({"success": False, "error": "Symbol extraction failed."}), 500


@stem_bp.post("/diagram/explain")
def diagram_explain():
    """Explain an uploaded diagram image."""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "file is required."}), 400

    uploaded = request.files["file"]
    if not uploaded or uploaded.filename == "":
        return jsonify({"success": False, "error": "No file selected."}), 400

    suffix = Path(uploaded.filename).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        return jsonify({"success": False, "error": "Only PNG and JPG images are supported."}), 400

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            uploaded.save(tmp.name)
            temp_path = tmp.name

        result = explain_diagram(temp_path)

        try:
            Path(temp_path).unlink()
        except Exception:
            pass

        uid = request.form.get("user_id")
        if uid:
            try:
                track_diagram_explanation_used(int(uid))
            except (TypeError, ValueError):
                pass

        return jsonify({"success": True, "explanation": result}), 200
    except Exception:
        logger.exception("Diagram explain failed")
        return jsonify({"success": False, "error": "Diagram explanation failed."}), 500


@stem_bp.post("/document/analyze")
def document_analyze():
    """Analyze document text for STEM content and return detection results."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"success": False, "error": "text is required."}), 400

    try:
        result = process_stem_support(text)
        detection = result["result"]
        return jsonify({
            "success": True,
            "has_formula": detection.has_formula,
            "has_symbols": detection.has_symbols,
            "has_diagrams": detection.has_diagrams,
            "formula_count": detection.formula_count,
            "symbol_count": detection.symbol_count,
            "available_features": result["features"],
            "formulas": result["formulas"],
            "symbols": result["symbols"],
        }), 200
    except Exception:
        logger.exception("STEM document analysis failed")
        return jsonify({"success": False, "error": "STEM document analysis failed."}), 500


@stem_bp.post("/step-solver")
def step_solver():
    """Solve a STEM problem step-by-step using the formula assistant."""
    data = request.get_json(silent=True) or {}
    problem = (data.get("problem") or data.get("formula") or "").strip()
    if not problem:
        return jsonify({"success": False, "error": "problem is required."}), 400

    try:
        explanation = explain_formula(problem)
        uid = _user_id_from_body(data)
        if uid:
            track_step_solver_used(uid, metadata={"problem": problem})
        return jsonify({"success": True, "solution": explanation}), 200
    except Exception:
        logger.exception("Step solver failed")
        return jsonify({"success": False, "error": "Step solver failed."}), 500


@stem_bp.post("/concept-breakdown")
def concept_breakdown():
    """Break down STEM concepts found in text."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"success": False, "error": "text is required."}), 400

    try:
        formulas = extract_formulas(text)
        symbols = extract_symbols(text)
        formula_explanations = [explain_formula(f) for f in formulas[:5]]
        symbol_explanations = [explain_symbol(s) for s in symbols[:5]]
        return jsonify({
            "success": True,
            "formulas": formula_explanations,
            "symbols": symbol_explanations,
        }), 200
    except Exception:
        logger.exception("Concept breakdown failed")
        return jsonify({"success": False, "error": "Concept breakdown failed."}), 500


@stem_bp.post("/vocabulary")
def scientific_vocabulary():
    """Extract scientific vocabulary from STEM text using the symbol extractor."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"success": False, "error": "text is required."}), 400

    try:
        symbols = extract_symbols(text)
        explanations = [explain_symbol(s) for s in symbols]
        return jsonify({"success": True, "vocabulary": explanations}), 200
    except Exception:
        logger.exception("Scientific vocabulary failed")
        return jsonify({"success": False, "error": "Scientific vocabulary extraction failed."}), 500
