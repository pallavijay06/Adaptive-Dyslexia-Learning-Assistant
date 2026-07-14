"""Document-scoped API routes for React migration.

Every endpoint here accepts a SQLite document_id (the integer PK returned by
POST /upload) and retrieves document_text internally.  The React frontend
never needs to send raw document text.

Endpoints added
---------------
POST /document/<id>/simplify    — Simplified Notes (Read Mode)
POST /document/<id>/vocabulary  — Vocabulary extraction (Read Mode)
POST /document/<id>/audio       — Audio generation (Listen Mode)
POST /document/<id>/visualize   — Visual Learning (flowchart / mind map)
POST /document/<id>/stem        — STEM analysis by document_id
POST /quiz/hint                 — Quiz hint generation
POST /vocabulary/explain        — Word Explorer (explain any word)
GET  /document/<id>             — Retrieve document metadata + text
"""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Blueprint, jsonify, request

from database.db import get_document
from services.simplification_service import simplify_text, SimplificationError
from services.vocabulary_service import generate_vocabulary, explain_word, VocabularyError
from services.tts_service import generate_audio, TTSError
from services.visual_service import generate_visual_content, VisualError
from services.llm_router import LLMRouterError
from services.behavior_tracking_service import (
    track_simplify_clicked,
    track_vocabulary_clicked,
    track_audio_started,
    track_visual_viewed,
)
from services.quiz_hint_service import generate_quiz_hint, generate_short_answer_hint
from backend.stem.stem_controller import process_stem_support
from backend.stem.formula_extractor import extract_formulas
from backend.stem.symbol_extractor import extract_symbols
from backend.stem.diagram_explainer import explain_diagram
from services.ocr_service import extract_images_from_pdf
from services.behavior_tracking_service import track_diagram_explanation_used

document_bp = Blueprint("document", __name__)
logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_UPLOADS_DIR = _PROJECT_ROOT / "uploads"


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _get_document_text(document_id: int) -> str | None:
    """Return document_text from SQLite for the given saved_document_id."""
    record = get_document(document_id)
    if record is None:
        return None
    return record.document_text or None


def _find_uploaded_file(file_name: str) -> Path | None:
    """Locate the saved upload for a document by matching its original filename stem."""
    original = Path(file_name)
    stem = original.stem
    suffix = original.suffix.lower()
    pattern = f"{stem}_*{suffix}"
    matches = sorted(_UPLOADS_DIR.glob(pattern))
    return matches[-1] if matches else None


def _user_id(data: dict) -> int | None:
    uid = data.get("user_id")
    try:
        return int(uid) if uid is not None else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# GET /document/<id>  — metadata + text
# ---------------------------------------------------------------------------

@document_bp.get("/document/<int:document_id>")
def get_document_info(document_id: int):
    """Return stored metadata and extracted text for a document.

    Response:
        id, file_name, file_type, upload_time, document_text, character_count
    """
    record = get_document(document_id)
    if record is None:
        return jsonify({"success": False, "error": "Document not found."}), 404

    return jsonify({
        "success": True,
        "document": {
            "id": record.id,
            "file_name": record.file_name,
            "file_type": record.file_type,
            "upload_time": record.upload_time.isoformat() if record.upload_time else None,
            "document_text": record.document_text,
            "character_count": len(record.document_text or ""),
        },
    }), 200


# ---------------------------------------------------------------------------
# POST /document/<id>/simplify  — Read Mode / Simplified Notes
# ---------------------------------------------------------------------------

@document_bp.post("/document/<int:document_id>/simplify")
def simplify_document(document_id: int):
    """Generate dyslexia-friendly simplified notes from a stored document.

    Streamlit equivalent:
        simplify_text(st.session_state.document_text)

    Request JSON (all optional):
        user_id (int)

    Response:
        simplified (str)
    """
    data = request.get_json(silent=True) or {}
    text = _get_document_text(document_id)
    if text is None:
        return jsonify({"success": False, "error": "Document not found."}), 404
    if not text.strip():
        return jsonify({"success": False, "error": "Document has no extractable text."}), 400

    uid = _user_id(data)
    if uid is not None:
        try:
            track_simplify_clicked(user_id=uid, metadata={"document_id": document_id})
        except Exception:
            logger.exception("Simplify tracking failed")

    try:
        result = simplify_text(text)
        return jsonify({"success": True, "simplified": result}), 200
    except SimplificationError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except LLMRouterError as exc:
        return jsonify({"success": False, "error": str(exc)}), 503
    except Exception:
        logger.exception("Simplify document failed for document_id=%s", document_id)
        return jsonify({"success": False, "error": "Simplification failed."}), 500


# ---------------------------------------------------------------------------
# POST /document/<id>/vocabulary  — Read Mode / Vocabulary
# ---------------------------------------------------------------------------

@document_bp.post("/document/<int:document_id>/vocabulary")
def vocabulary_document(document_id: int):
    """Extract difficult vocabulary from a stored document.

    Streamlit equivalent:
        generate_vocabulary(st.session_state.document_text)

    Request JSON (all optional):
        user_id (int)
        word_count (int, default 10)

    Response:
        vocabulary (list of {word, meaning})
    """
    data = request.get_json(silent=True) or {}
    text = _get_document_text(document_id)
    if text is None:
        return jsonify({"success": False, "error": "Document not found."}), 404
    if not text.strip():
        return jsonify({"success": False, "error": "Document has no extractable text."}), 400

    word_count = int(data.get("word_count") or 10)
    uid = _user_id(data)
    if uid is not None:
        try:
            track_vocabulary_clicked(user_id=uid, metadata={"document_id": document_id})
        except Exception:
            logger.exception("Vocabulary tracking failed")

    try:
        result = generate_vocabulary(text, word_count=word_count)
        return jsonify({"success": True, "vocabulary": result}), 200
    except VocabularyError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except LLMRouterError as exc:
        return jsonify({"success": False, "error": str(exc)}), 503
    except Exception:
        logger.exception("Vocabulary document failed for document_id=%s", document_id)
        return jsonify({"success": False, "error": "Vocabulary extraction failed."}), 500


# ---------------------------------------------------------------------------
# POST /document/<id>/audio  — Listen Mode
# ---------------------------------------------------------------------------

@document_bp.post("/document/<int:document_id>/audio")
def audio_document(document_id: int):
    """Generate MP3 audio from a stored document.

    Streamlit equivalent:
        generate_audio(st.session_state.document_text)

    Request JSON (all optional):
        user_id (int)
        lang (str, default "en")
        slow (bool, default false)

    Response:
        audio_url (/audio/<filename>), sentences (list[str])
    """
    data = request.get_json(silent=True) or {}
    text = _get_document_text(document_id)
    if text is None:
        return jsonify({"success": False, "error": "Document not found."}), 404
    if not text.strip():
        return jsonify({"success": False, "error": "Document has no extractable text."}), 400

    lang = (data.get("lang") or "en").strip()
    slow = bool(data.get("slow", False))
    uid = _user_id(data)

    try:
        audio_path = generate_audio(text, lang=lang, slow=slow)
        filename = Path(audio_path).name
        if uid is not None:
            try:
                track_audio_started(user_id=uid, metadata={"document_id": document_id, "text_length": len(text)})
            except Exception:
                logger.exception("Audio tracking failed")

        from services.tts_service import split_text_into_sentences
        sentences = split_text_into_sentences(text)

        return jsonify({
            "success": True,
            "audio_url": f"/audio/{filename}",
            "audio_file": audio_path,
            "sentences": sentences,
        }), 200
    except TTSError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:
        logger.exception("Audio document failed for document_id=%s", document_id)
        return jsonify({"success": False, "error": "Audio generation failed."}), 500


# ---------------------------------------------------------------------------
# POST /document/<id>/visualize  — Visual Learning
# ---------------------------------------------------------------------------

@document_bp.post("/document/<int:document_id>/visualize")
def visualize_document(document_id: int):
    """Generate a flowchart or mind map from a stored document.

    Streamlit equivalent:
        generate_visual_content(
            st.session_state.document_text,
            theme=visual_theme,
            visual_type=visual_type_map[selected_visual],
        )

    Request JSON:
        visual_type (str, required) — "flowchart" or "mind_map"
        theme (str, optional)       — "light" | "dark" | "dyslexia_cream" | "dyslexia_yellow"
        user_id (int, optional)

    Response:
        visual { topic, title, description, flowchart_url, mindmap_url, structure }
    """
    data = request.get_json(silent=True) or {}
    visual_type = (data.get("visual_type") or "").strip().lower()
    if not visual_type:
        return jsonify({"success": False, "error": "visual_type is required."}), 400

    text = _get_document_text(document_id)
    if text is None:
        return jsonify({"success": False, "error": "Document not found."}), 404
    if not text.strip():
        return jsonify({"success": False, "error": "Document has no extractable text."}), 400

    theme = (data.get("theme") or "light").strip()
    uid = _user_id(data)

    try:
        visual_content = generate_visual_content(text, theme=theme, visual_type=visual_type)

        if visual_content.get("flowchart_path"):
            visual_content["flowchart_url"] = f"/diagrams/{Path(visual_content['flowchart_path']).name}"
        if visual_content.get("mindmap_path"):
            visual_content["mindmap_url"] = f"/diagrams/{Path(visual_content['mindmap_path']).name}"

        if uid is not None:
            try:
                track_visual_viewed(user_id=uid, metadata={"document_id": document_id, "visual_type": visual_type})
            except Exception:
                logger.exception("Visual tracking failed")

        return jsonify({"success": True, "visual": visual_content}), 200
    except VisualError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except LLMRouterError as exc:
        return jsonify({"success": False, "error": str(exc)}), 503
    except Exception:
        logger.exception("Visualize document failed for document_id=%s", document_id)
        return jsonify({"success": False, "error": "Visual generation failed."}), 500


# ---------------------------------------------------------------------------
# POST /document/<id>/stem  — STEM Support by document_id
# ---------------------------------------------------------------------------

@document_bp.post("/document/<int:document_id>/stem")
def stem_document(document_id: int):
    """Analyze a stored document for STEM content.

    Streamlit equivalent:
        render_stem_mode(document_text=st.session_state.document_text,
                         diagram_images=st.session_state.document_diagram_images)

    Response:
        has_formula, has_symbols, has_diagrams, formula_count, symbol_count,
        available_features, formulas, symbols, diagram_count
    """
    record = get_document(document_id)
    if record is None:
        return jsonify({"success": False, "error": "Document not found."}), 404
    text = record.document_text or ""
    if not text.strip():
        return jsonify({"success": False, "error": "Document has no extractable text."}), 400

    # Mirror Streamlit: extract images from the uploaded PDF automatically.
    diagram_images: list[str] = []
    if record.file_type and record.file_type.lower() == "pdf":
        uploaded_path = _find_uploaded_file(record.file_name)
        if uploaded_path:
            try:
                diagram_images = extract_images_from_pdf(str(uploaded_path))
            except Exception:
                logger.exception("PDF image extraction failed for document_id=%s", document_id)

    try:
        result = process_stem_support(text, diagram_images=diagram_images)
        detection = result["result"]
        return jsonify({
            "success": True,
            "has_formula": detection.has_formula,
            "has_symbols": detection.has_symbols,
            "has_diagrams": detection.has_diagrams or len(diagram_images) > 0,
            "formula_count": detection.formula_count,
            "symbol_count": detection.symbol_count,
            "available_features": result["features"],
            "formulas": result["formulas"],
            "symbols": result["symbols"],
            "diagram_count": len(diagram_images),
        }), 200
    except Exception:
        logger.exception("STEM document analysis failed for document_id=%s", document_id)
        return jsonify({"success": False, "error": "STEM analysis failed."}), 500


# ---------------------------------------------------------------------------
# POST /document/<id>/diagrams  — Diagram Explanation (Streamlit-equivalent)
# ---------------------------------------------------------------------------

@document_bp.post("/document/<int:document_id>/diagrams")
def explain_document_diagrams(document_id: int):
    """Extract and explain all diagrams from an uploaded PDF document.

    Streamlit equivalent:
        diagram_images = extract_images_from_pdf(record.uploaded_path)
        _render_diagram_tab(diagram_images)  # calls explain_diagram per image

    This endpoint mirrors the Streamlit workflow exactly:
    - No second upload is required.
    - Images are extracted automatically from the uploaded document.
    - Each image is explained by the backend using Gemini Vision.

    Response:
        diagrams: list of { index, filename, explanation }
    """
    record = get_document(document_id)
    if record is None:
        return jsonify({"success": False, "error": "Document not found."}), 404

    if not record.file_type or record.file_type.lower() != "pdf":
        return jsonify({"success": True, "diagrams": [], "message": "Diagram extraction is only supported for PDF documents."}), 200

    uploaded_path = _find_uploaded_file(record.file_name)
    if not uploaded_path:
        return jsonify({"success": True, "diagrams": [], "message": "Uploaded file not found on disk."}), 200

    try:
        image_paths = extract_images_from_pdf(str(uploaded_path))
    except Exception:
        logger.exception("PDF image extraction failed for document_id=%s", document_id)
        return jsonify({"success": False, "error": "Failed to extract images from document."}), 500

    if not image_paths:
        return jsonify({"success": True, "diagrams": [], "message": "No diagrams found in this document."}), 200

    data = request.get_json(silent=True) or {}
    uid = _user_id(data)

    _DIAGRAMS_SERVE_DIR = _PROJECT_ROOT / "generated_diagrams"
    _DIAGRAMS_SERVE_DIR.mkdir(parents=True, exist_ok=True)

    diagrams = []
    for idx, image_path in enumerate(image_paths, start=1):
        try:
            explanation = explain_diagram(image_path)
        except Exception:
            logger.exception("Diagram explanation failed for image %s", image_path)
            explanation = {
                "diagram_type": "Unknown",
                "purpose": "Unable to determine diagram purpose.",
                "how_it_works": [],
                "component_roles": [],
                "key_concept": "",
                "simplified_explanation": "The diagram could not be analyzed.",
                "key_takeaway": "Try another image.",
            }

        # Copy the extracted temp image into the served diagrams directory so
        # Flask can serve it at /diagrams/<filename> — mirrors how Streamlit
        # reads the image directly from disk via st.image(image_path).
        src = Path(image_path)
        dest = _DIAGRAMS_SERVE_DIR / src.name
        try:
            import shutil
            shutil.copy2(str(src), str(dest))
            image_url = f"/diagrams/{src.name}"
        except Exception:
            logger.exception("Failed to copy diagram image to serve directory: %s", image_path)
            image_url = None

        diagrams.append({
            "index": idx,
            "filename": src.name,
            "image_url": image_url,
            "explanation": explanation,
        })

    if uid is not None:
        try:
            track_diagram_explanation_used(uid, metadata={"document_id": document_id, "diagram_count": len(diagrams)})
        except Exception:
            logger.exception("Diagram tracking failed")

    return jsonify({"success": True, "diagrams": diagrams}), 200


# ---------------------------------------------------------------------------
# POST /quiz/hint  — Quiz Hint (Read Mode / Quiz Mode)
# ---------------------------------------------------------------------------

@document_bp.post("/quiz/hint")
def quiz_hint():
    """Generate an AI hint for a quiz question without revealing the answer.

    Streamlit equivalent:
        generate_quiz_hint(question, correct_answer, concept, question_type)

    Request JSON:
        question (str, required)
        correct_answer (str, required)
        concept (str, optional)
        question_type (str, optional) — "MCQ" | "Short Answer", default "MCQ"

    Response:
        hint (str)
    """
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    correct_answer = (data.get("correct_answer") or "").strip()
    if not question or not correct_answer:
        return jsonify({"success": False, "error": "question and correct_answer are required."}), 400

    concept = (data.get("concept") or None)
    question_type = (data.get("question_type") or "MCQ").strip()

    try:
        if question_type == "Short Answer":
            hint = generate_short_answer_hint(question, correct_answer, concept=concept)
        else:
            hint = generate_quiz_hint(question, correct_answer, concept=concept, question_type=question_type)
        return jsonify({"success": True, "hint": hint}), 200
    except LLMRouterError as exc:
        return jsonify({"success": False, "error": str(exc)}), 503
    except Exception:
        logger.exception("Quiz hint generation failed")
        return jsonify({"success": False, "error": "Hint generation failed."}), 500


# ---------------------------------------------------------------------------
# POST /vocabulary/explain  — Word Explorer
# ---------------------------------------------------------------------------

@document_bp.post("/vocabulary/explain")
def vocabulary_explain():
    """Explain any word in dyslexia-friendly language.

    Streamlit equivalent:
        explain_word(word_input.strip())

    Request JSON:
        word (str, required)

    Response:
        explanation { word, meaning, explanation, example }
    """
    data = request.get_json(silent=True) or {}
    word = (data.get("word") or "").strip()
    if not word:
        return jsonify({"success": False, "error": "word is required."}), 400

    try:
        result = explain_word(word)
        return jsonify({"success": True, "explanation": result}), 200
    except VocabularyError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except LLMRouterError as exc:
        return jsonify({"success": False, "error": str(exc)}), 503
    except Exception:
        logger.exception("Word explanation failed for word=%s", word)
        return jsonify({"success": False, "error": "Word explanation failed."}), 500
