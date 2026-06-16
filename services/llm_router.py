"""Route LLM calls through OpenAI, Gemini, then Ollama."""

from __future__ import annotations

import logging

from services.gemini_service import (
    GeminiAPIError,
    GeminiConfigurationError,
    generate_answer as gemini_generate_answer,
    generate_content as gemini_generate_content,
)
from services.openai_service import (
    OpenAIServiceError,
    generate_answer as openai_generate_answer,
    generate_content as openai_generate_content,
)
from services.ollama_service import (
    OllamaServiceError,
    generate_answer as ollama_generate_answer,
    generate_content as ollama_generate_content,
)
from services.text_cleanup import remove_ansi_escape_codes

logger = logging.getLogger(__name__)


class LLMRouterError(RuntimeError):
    """Raised when all configured LLM providers fail to produce an answer."""


def generate_answer(question: str, context: str) -> str:
    """Generate an answer with OpenAI first, then Gemini, then Ollama.
    
    Used for RAG-style question answering with context.
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")
    if not context or not context.strip():
        raise ValueError("Context cannot be empty.")

    try:
        return remove_ansi_escape_codes(openai_generate_answer(question, context))
    except OpenAIServiceError as exc:
        logger.warning("OpenAI answer generation failed; falling back to Gemini: %s", exc)

    try:
        return remove_ansi_escape_codes(gemini_generate_answer(question, context))
    except (GeminiAPIError, GeminiConfigurationError) as exc:
        logger.warning("Gemini answer generation failed; falling back to Ollama: %s", exc)
        try:
            return remove_ansi_escape_codes(ollama_generate_answer(question, context))
        except OllamaServiceError as ollama_exc:
            logger.exception("All LLM providers failed for answer generation.")
            raise LLMRouterError(
                "I could not reach any AI provider right now. Please check your API keys, quota, or local Ollama setup and try again."
            ) from ollama_exc


def generate_content(prompt: str) -> str:
    """Generate content with OpenAI first, then Gemini, then Ollama.
    
    Used for content generation tasks like simplification, vocabulary extraction,
    visual learning generation, etc. Does NOT use chat history.
    
    Args:
        prompt: The task prompt (e.g., "Simplify this: ...")
        
    Returns:
        Generated content text.
        
    Raises:
        ValueError: If prompt is empty.
        LLMRouterError: If both Gemini and Ollama fail.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    try:
        return remove_ansi_escape_codes(openai_generate_content(prompt))
    except OpenAIServiceError as exc:
        logger.warning("OpenAI content generation failed; falling back to Gemini: %s", exc)

    try:
        return remove_ansi_escape_codes(gemini_generate_content(prompt))
    except (GeminiAPIError, GeminiConfigurationError) as exc:
        logger.warning("Gemini content generation failed; falling back to Ollama: %s", exc)
        try:
            return remove_ansi_escape_codes(ollama_generate_content(prompt))
        except OllamaServiceError as ollama_exc:
            logger.exception("All LLM providers failed for content generation.")
            raise LLMRouterError(
                "I could not reach any AI provider right now. Please check your API keys, quota, or local Ollama setup and try again."
            ) from ollama_exc


def summarize_document(document_text: str) -> str:
    """Summarize uploaded content through the configured provider chain."""
    return generate_content(
        _document_prompt(
            document_text,
            "Summarize this document in simple language with short sections.",
        )
    )


def simplify_document(document_text: str) -> str:
    """Simplify uploaded content through the configured provider chain."""
    return generate_content(
        _document_prompt(
            document_text,
            "Simplify this document for a dyslexic learner. Use short sentences and clear bullets.",
        )
    )


def generate_quiz(document_text: str) -> str:
    """Generate a short quiz through the configured provider chain."""
    return generate_content(
        _document_prompt(
            document_text,
            "Create a 5-question quiz from this document. Include answers after the questions.",
        )
    )


def extract_vocabulary(document_text: str) -> str:
    """Extract vocabulary through the configured provider chain."""
    return generate_content(
        _document_prompt(
            document_text,
            "Extract important vocabulary from this document and define each term simply.",
        )
    )


def _document_prompt(document_text: str, instruction: str) -> str:
    text = (document_text or "").strip()
    if not text:
        raise ValueError("Document text cannot be empty.")

    return (
        f"{instruction}\n\n"
        "DOCUMENT CONTENT:\n"
        f"{text}"
    )
