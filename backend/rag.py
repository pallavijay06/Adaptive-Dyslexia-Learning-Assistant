"""RAG-style document helpers for chat-with-document flows."""

from __future__ import annotations

from backend.chunker import chunk_text
from backend.retriever import retrieve_relevant_chunks_for_question
from backend.vector_store import build_index
from services.document_context import DocumentError, get_document_text
from services.llm_router import generate_answer


def ask_document(
    question: str,
    document_id: str | None = None,
    document_text: str | None = None,
) -> str:
    """Answer a learner question using the active or selected document context."""
    if document_text is None:
        document_text = get_document_text(document_id)

    if not document_text:
        raise DocumentError("Upload a document before asking a question.")

    chunks = chunk_text(document_text)
    vector_store = build_index(chunks)
    relevant_chunks = retrieve_relevant_chunks_for_question(question, vector_store, top_k=3)
    context = "\n\n".join(chunk["text"] for chunk in relevant_chunks)
    return generate_answer(question, context)
