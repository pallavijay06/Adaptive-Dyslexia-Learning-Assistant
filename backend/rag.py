"""RAG-style document helpers for chat-with-document flows."""

from __future__ import annotations

from services.document_context import get_document_text
from services.gemini_service import chat_with_gemini


def ask_document(question: str, document_id: str | None = None) -> str:
    """Answer a learner question using the active or selected document context."""
    document_text = get_document_text(document_id)
    return chat_with_gemini(question, document_text=document_text)
