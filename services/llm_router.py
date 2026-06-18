"""Route LLM calls through OpenRouter, Gemini, then Ollama."""

from __future__ import annotations

import logging

from services.openrouter_service import (
    OpenRouterAPIError,
    OpenRouterConfigurationError,
    generate_answer as openrouter_generate_answer,
    generate_content as openrouter_generate_content,
)
from services.gemini_service import (
    GeminiAPIError,
    GeminiConfigurationError,
    generate_answer as gemini_generate_answer,
    generate_content as gemini_generate_content,
)
from services.ollama_service import (
    OllamaServiceError,
    generate_answer as ollama_generate_answer,
    generate_content as ollama_generate_content,
)
from services.text_cleanup import (
    remove_ansi_escape_codes,
    remove_markdown_and_html,
)

logger = logging.getLogger(__name__)


class LLMRouterError(RuntimeError):
    """Raised when all configured LLM providers fail to produce an answer."""


def generate_answer(question: str, context: str) -> str:
    """Generate an answer with OpenRouter first, then Gemini, then Ollama.
    
    Used for RAG-style question answering with context.
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")
    if not context or not context.strip():
        raise ValueError("Context cannot be empty.")

    try:
        return _clean_model_response(openrouter_generate_answer(question, context))
    except (OpenRouterAPIError, OpenRouterConfigurationError) as exc:
        logger.warning("OpenRouter answer generation failed; falling back to Gemini: %s", exc)

    try:
        return _clean_model_response(gemini_generate_answer(question, context))
    except (GeminiAPIError, GeminiConfigurationError) as exc:
        logger.warning("Gemini answer generation failed; falling back to Ollama: %s", exc)
        try:
            return _clean_model_response(ollama_generate_answer(question, context))
        except OllamaServiceError as ollama_exc:
            logger.exception("All LLM providers failed for answer generation.")
            raise LLMRouterError(
                "I could not reach any AI provider right now. Please check your API keys, quota, or local Ollama setup and try again."
            ) from ollama_exc


def _clean_model_response(text: str) -> str:
    """Clean raw model output before returning to the service layer."""
    cleaned = remove_ansi_escape_codes(text)
    return remove_markdown_and_html(cleaned)


def generate_content(prompt: str) -> str:
    """Generate content with OpenRouter first, then Gemini, then Ollama.
    
    Used for content generation tasks like simplification, vocabulary extraction,
    visual learning generation, etc. Does NOT use chat history.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    try:
        return _clean_model_response(openrouter_generate_content(prompt))
    except (OpenRouterAPIError, OpenRouterConfigurationError) as exc:
        logger.warning("OpenRouter content generation failed; falling back to Gemini: %s", exc)

    try:
        return _clean_model_response(gemini_generate_content(prompt))
    except (GeminiAPIError, GeminiConfigurationError) as exc:
        logger.warning("Gemini content generation failed; falling back to Ollama: %s", exc)
        try:
            return _clean_model_response(ollama_generate_content(prompt))
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
