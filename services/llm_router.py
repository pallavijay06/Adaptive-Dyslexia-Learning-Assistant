"""Route answers through Gemini first, then Ollama as a fallback."""

from __future__ import annotations

from services.gemini_service import GeminiAPIError, GeminiConfigurationError, generate_answer as gemini_generate_answer
from services.ollama_service import OllamaServiceError, generate_answer as ollama_generate_answer


class LLMRouterError(RuntimeError):
    """Raised when both Gemini and Ollama fail to produce an answer."""


def generate_answer(question: str, context: str) -> str:
    """Generate an answer, trying Gemini first and falling back to Ollama on failure."""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")
    if not context or not context.strip():
        raise ValueError("Context cannot be empty.")

    try:
        return gemini_generate_answer(question, context)
    except (GeminiAPIError, GeminiConfigurationError) as gemini_exc:
        try:
            return ollama_generate_answer(question, context)
        except OllamaServiceError as ollama_exc:
            raise LLMRouterError(
                "Gemini failed and Ollama fallback also failed. "
                f"Gemini error: {gemini_exc}. Ollama error: {ollama_exc}"
            ) from ollama_exc
