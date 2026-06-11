"""Upload API routes for document-aware learning."""

from __future__ import annotations

from dataclasses import asdict

from flask import Blueprint, jsonify, request

from services.document_context import DocumentError, process_uploaded_document


upload_bp = Blueprint("upload", __name__)


@upload_bp.post("/upload")
def upload_document() -> tuple[object, int]:
    """Accept a learner document, extract text, and make it active for chat."""
    file = request.files.get("file")
    if file is None:
        return jsonify({"success": False, "error": "Upload field 'file' is required."}), 400

    try:
        record = process_uploaded_document(file)
    except DocumentError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": f"Document processing failed: {exc}"}), 500

    return (
        jsonify(
            {
                "success": True,
                "filename": record.original_filename,
                "document_id": record.document_id,
                "characters_extracted": record.characters_extracted,
                "document": asdict(record),
            }
        ),
        200,
    )
