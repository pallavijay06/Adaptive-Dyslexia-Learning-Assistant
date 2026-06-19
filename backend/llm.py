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
    if document_text and document_text.strip():
        return generate_answer(user_message, document_text)
    return generate_content(user_message)
