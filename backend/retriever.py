"""Retriever abstraction that uses embeddings and FAISS to find relevant chunks."""

from __future__ import annotations

from services.embedding_service import embed_query
from backend.vector_store import VectorStore, retrieve_relevant_chunks


def retrieve_relevant_chunks_for_question(
    question: str,
    vector_store: VectorStore,
    top_k: int = 3,
) -> list[dict[str, object]]:
    """Return the most relevant document chunks for a user question."""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    query_embedding = embed_query(question)
    return retrieve_relevant_chunks(vector_store, query_embedding, top_k=top_k)
