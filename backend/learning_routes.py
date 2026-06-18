"""Learning routes for Prototype 2 features: OCR, simplification, vocabulary, audio, visual."""

from __future__ import annotations

import tempfile
from pathlib import Path

from flask import Blueprint, request, jsonify

from services.ocr_service import extract_text_from_image, extract_text_from_pdf_images, OCRError
from services.simplification_service import simplify_text, SimplificationError
from services.vocabulary_service import generate_vocabulary, VocabularyError
from services.tts_service import generate_audio, TTSError
from services.visual_service import generate_visual_content, VisualError
from services.llm_router import LLMRouterError


learning_bp = Blueprint("learning", __name__)


# =========================
# OCR - Extract text from images and scanned PDFs
# =========================
@learning_bp.route("/ocr", methods=["POST"])
def ocr():
    """Extract text from image or scanned PDF.
    
    Request:
        - file: Image file (PNG, JPG, GIF, WebP) or PDF
        
    Response:
        - text: Extracted text
        - confidence: "high", "medium", or "low" (optional)
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded_file = request.files["file"]

    if not uploaded_file or uploaded_file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        # Save file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.filename).suffix) as tmp:
            uploaded_file.save(tmp.name)
            temp_path = tmp.name
        
        # Determine file type and extract text
        filename_lower = uploaded_file.filename.lower()
        
        if filename_lower.endswith(".pdf"):
            text = extract_text_from_pdf_images(temp_path)
        else:
            text = extract_text_from_image(temp_path)
        
        # Clean up temp file
        try:
            Path(temp_path).unlink()
        except:
            pass
        
        if not text or not text.strip():
            return jsonify({
                "error": "No text could be extracted from the image",
                "text": ""
            }), 400
        
        return jsonify({
            "text": text,
            "success": True
        }), 200

    except OCRError as exc:
        return jsonify({"error": f"OCR failed: {str(exc)}"}), 400
    except Exception as exc:
        return jsonify({"error": f"Unexpected error during OCR: {str(exc)}"}), 500


# =========================
# Simplification - Simplify text for dyslexia
# =========================
@learning_bp.route("/simplify", methods=["POST"])
def simplify():
    """Simplify text for students with dyslexia.
    
    Request (JSON):
        - text: Text to simplify (required)
        
    Response:
        - simplified: Simplified text with short sentences, bullet points, etc.
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()

    if not text:
        return jsonify({"error": "Text cannot be empty"}), 400

    try:
        result = simplify_text(text)
        return jsonify({
            "simplified": result,
            "success": True
        }), 200

    except SimplificationError as exc:
        return jsonify({"error": f"Simplification failed: {str(exc)}"}), 400
    except LLMRouterError as exc:
        return jsonify({"error": f"Both Gemini and Ollama failed: {str(exc)}"}), 503
    except Exception as exc:
        return jsonify({"error": f"Unexpected error: {str(exc)}"}), 500


# =========================
# Vocabulary - Extract difficult words with definitions
# =========================
@learning_bp.route("/vocabulary", methods=["POST"])
def vocabulary():
    """Extract difficult vocabulary and generate simple definitions.
    
    Request (JSON):
        - text: Text to extract vocabulary from (required)
        
    Response:
        - vocabulary: List of dicts with "word" and "meaning" keys
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()

    if not text:
        return jsonify({"error": "Text cannot be empty"}), 400

    try:
        result = generate_vocabulary(text)
        return jsonify({
            "vocabulary": result,
            "success": True
        }), 200

    except VocabularyError as exc:
        return jsonify({"error": f"Vocabulary extraction failed: {str(exc)}"}), 400
    except LLMRouterError as exc:
        return jsonify({"error": f"Both Gemini and Ollama failed: {str(exc)}"}), 503
    except Exception as exc:
        return jsonify({"error": f"Unexpected error: {str(exc)}"}), 500


# =========================
# Audio - Generate MP3 from text
# =========================
@learning_bp.route("/audio", methods=["POST"])
def audio():
    """Generate MP3 audio from text.
    
    Request (JSON):
        - text: Text to convert to speech (required)
        - lang: Language code (optional, default: "en")
        - slow: Whether to speak slowly (optional, default: false)
        
    Response:
        - audio_file: Path to generated MP3 file
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    lang = (data.get("lang") or "en").strip()
    slow = data.get("slow", False)

    if not text:
        return jsonify({"error": "Text cannot be empty"}), 400

    try:
        audio_path = generate_audio(text, lang=lang, slow=slow)
        return jsonify({
            "audio_file": audio_path,
            "success": True
        }), 200

    except TTSError as exc:
        return jsonify({"error": f"Audio generation failed: {str(exc)}"}), 400
    except Exception as exc:
        return jsonify({"error": f"Unexpected error: {str(exc)}"}), 500


# =========================
# Visual Learning - Generate flowcharts and concept maps
# =========================
@learning_bp.route("/visualize", methods=["POST"])
def visualize():
    """Generate visual learning content (flowcharts, concept maps, etc).
    
    Request (JSON):
        - text: Text to visualize (required)
        
    Response:
        - title: Visual title
        - type: Type of visualization (flowchart, concept_map, process, summary)
        - steps: List of steps or components
        - description: Brief description
    """
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    visual_type = (data.get("visual_type") or None)

    if not text:
        return jsonify({"error": "Text cannot be empty"}), 400

    try:
        visual_content = generate_visual_content(text, visual_type=visual_type)
        return jsonify({
            "visual": visual_content,
            "success": True
        }), 200

    except VisualError as exc:
        return jsonify({"error": f"Visual generation failed: {str(exc)}"}), 400
    except LLMRouterError as exc:
        return jsonify({"error": f"Both Gemini and Ollama failed: {str(exc)}"}), 503
    except Exception as exc:
        return jsonify({"error": f"Unexpected error: {str(exc)}"}), 500


# =========================
# Health check for learning routes
# =========================
@learning_bp.route("/health", methods=["GET"])
def learning_health():
    """Health check for learning features."""
    return jsonify({"status": "ok", "module": "learning"}), 200