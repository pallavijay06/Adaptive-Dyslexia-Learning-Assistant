"""Upload API routes for document-aware learning."""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from services.document_context import DocumentError, process_uploaded_document
from database.db import save_document, save_user, get_user

logger = logging.getLogger(__name__)

upload_bp = Blueprint("upload", __name__)


def _resolve_user_id() -> int:
    """Resolve a user ID for database storage using a fallback anonymous account."""
    user = get_user("anonymous@cheal.local")
    if user is not None:
        return user.id  # type: ignore[index]

    anonymous = save_user(
        name="Anonymous Learner",
        email="anonymous@cheal.local",
        password_hash="",
    )
    return anonymous.id  # type: ignore[index]


@upload_bp.post("/upload")
def upload_document() -> tuple[object, int]:
    """Accept a learner document, extract text, and persist it to SQLite."""
    file = request.files.get("file")
    if file is None:
        return jsonify({"success": False, "error": "Upload field 'file' is required."}), 400

    try:
        record = process_uploaded_document(file)
        with open(record.extracted_path, encoding="utf-8") as extracted_file:
            document_text = extracted_file.read()

        user_id = _resolve_user_id()
        saved_document = save_document(
            user_id=user_id,
            file_name=record.original_filename,
            file_type=record.file_type,
            document_text=document_text,
        )
        logger.info(
            "Document saved to database: %s (file_type=%s, upload_time=%s, document_id=%s)",
            saved_document.file_name,
            saved_document.file_type,
            saved_document.upload_time.isoformat(),
            saved_document.id,
        )
    except DocumentError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": f"Document processing failed: {exc}"}), 500

    return (
        jsonify(
            {
                "success": True,
                "filename": record.original_filename,
                "document_id": record.document_id,
                "saved_document_id": saved_document.id,
                "characters_extracted": record.characters_extracted,
                "document": {
                    "id": saved_document.id,
                    "file_name": saved_document.file_name,
                    "file_type": saved_document.file_type,
                    "upload_time": saved_document.upload_time.isoformat(),
                },
            }
        ),
        200,
    )
