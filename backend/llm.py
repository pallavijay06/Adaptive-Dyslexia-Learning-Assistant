"""LLM facade for frontend code."""

from services.llm_router import (
    extract_vocabulary,
    generate_answer,
    generate_content,
    generate_quiz,
    simplify_document,
    summarize_document,
)


def chat_with_gemini(user_message: str, document_text: str | None = None) -> str:
    """Backward-compatible chat helper routed through OpenAI -> Gemini -> Ollama."""
    # Ensure chat uses RAG: if document_text is provided, prefer caller to pass retrieved context
    if document_text and document_text.strip():
        # If the caller supplied a full document, this function should not forward the entire
        # document to the LLM. The higher-level flow (e.g., backend.rag.ask_document) should
        # provide retrieved context. Here we defensively route through generate_answer which
        # expects contextual text (already limited by RAG in practice).
        return generate_answer(user_message, document_text)

    # Plain chat without document uses chat-level token limits
    return generate_content(user_message, max_tokens=1000)
