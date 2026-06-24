"""OpenRouter LLM service for the cHEAL learning assistant.

OpenRouter is an OpenAI-compatible API that provides access to multiple LLMs
including Google's Gemini, Anthropic's Claude, and others.

This module owns all OpenRouter-specific behavior:
- loading the API key and model from .env
- creating the OpenAI client configured for OpenRouter
- returning plain response text to the router

The router layer should call generate_content() and generate_answer() instead
of importing OpenRouter SDK objects directly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from services.text_cleanup import remove_ansi_escape_codes


DEFAULT_MODEL_NAME = "google/gemini-2.5-flash"
DEFAULT_TIMEOUT_SECONDS = 60
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

SYSTEM_INSTRUCTION = """
You are a friendly dyslexia-focused learning assistant.
Explain concepts clearly, use simple language, break answers into small steps,
and keep responses supportive, beginner-friendly, and easy to read.
""".strip()


class OpenRouterServiceError(RuntimeError):
    """Base error for expected OpenRouter service failures."""


class OpenRouterConfigurationError(OpenRouterServiceError):
    """Raised when OpenRouter cannot be configured, usually because the key is missing."""


class OpenRouterAPIError(OpenRouterServiceError):
    """Raised when OpenRouter fails to generate a response."""


def generate_answer(question: str, context: str, max_tokens: int | None = None) -> str:
    """Generate a dyslexia-friendly answer using retrieved document context.
    
    Args:
        question: The learner's question.
        context: Retrieved document context for answering.
        
    Returns:
        Generated answer text.
        
    Raises:
        ValueError: If question or context is empty.
        OpenRouterConfigurationError: If API key or SDK is missing.
        OpenRouterAPIError: If generation fails.
    """
    question = (question or "").strip()
    context = (context or "").strip()

    if not question:
        raise ValueError("Question cannot be empty.")
    if not context:
        raise ValueError("Context cannot be empty.")

    prompt = (
        "Use the retrieved document context as the primary source.\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION:\n{question}\n\n"
        "When the context contains the answer, explain it simply.\n"
        "When the context contains only part of the answer, use the context first, then add helpful general knowledge.\n"
        "When the context does not answer the question, answer from general knowledge and say that the information is not directly in the uploaded document.\n"
        "Keep replies short.\n"
        "Use simple vocabulary.\n"
        "Use short bullets when helpful."
    )
    return _generate_text(prompt, max_tokens=max_tokens)


def generate_content(prompt: str, max_tokens: int | None = None) -> str:
    """Generate one-off content for simplification, vocabulary, visuals, etc.
    
    Args:
        prompt: The task prompt (e.g., "Simplify this: ...").
        
    Returns:
        Generated content text.
        
    Raises:
        ValueError: If prompt is empty.
        OpenRouterConfigurationError: If API key or SDK is missing.
        OpenRouterAPIError: If generation fails.
    """
    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("Prompt cannot be empty.")

    return _generate_text(prompt, max_tokens=max_tokens)


def _generate_text(prompt: str, max_tokens: int | None = None) -> str:
    """Internal method to generate text via OpenRouter API."""
    try:
        client = _get_client()
        create_kwargs = dict(
            model=_get_model_name(),
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        # Only include an explicit output token limit when provided.
        if isinstance(max_tokens, int):
            create_kwargs["max_tokens"] = int(max_tokens)

        response = client.chat.completions.create(**create_kwargs)
        return remove_ansi_escape_codes(_extract_response_text(response))
    except OpenRouterServiceError:
        raise
    except Exception as exc:
        raise _map_openrouter_error(exc) from exc


def _get_client() -> Any:
    """Create and return an OpenAI client configured for OpenRouter."""
    api_key = _load_api_key()

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise OpenRouterConfigurationError(
            "OpenAI SDK is not installed. Run: pip install openai"
        ) from exc

    try:
        return OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        raise OpenRouterConfigurationError(
            "Could not initialize OpenRouter client."
        ) from exc


def _load_api_key() -> str:
    """Load OpenRouter API key from .env file."""
    _load_dotenv_files()

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise OpenRouterConfigurationError(
            "Missing OpenRouter API key. Add OPENROUTER_API_KEY to .env."
        )

    return api_key


def _get_model_name() -> str:
    """Load OpenRouter model name from .env, with fallback to default."""
    _load_dotenv_files()

    model_name = os.getenv("OPENROUTER_MODEL", "").strip()
    return model_name or DEFAULT_MODEL_NAME


def _load_dotenv_files() -> None:
    """Load environment variables from .env and .env.local if they exist."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)

    env_local_path = Path(__file__).parent.parent / ".env.local"
    if env_local_path.exists():
        load_dotenv(env_local_path, override=True)


def _extract_response_text(response: Any) -> str:
    """Extract plain text from OpenRouter API response."""
    try:
        if hasattr(response, "choices") and response.choices:
            choice = response.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "content"):
                return choice.message.content or ""
    except Exception:
        pass

    return str(response)


def _map_openrouter_error(exc: Exception) -> OpenRouterAPIError:
    """Convert various exceptions to OpenRouterAPIError with helpful messages."""
    error_message = str(exc)

    if "authentication" in error_message.lower() or "401" in error_message:
        return OpenRouterAPIError(
            "OpenRouter authentication failed. Check your OPENROUTER_API_KEY."
        )

    if "rate" in error_message.lower() or "429" in error_message:
        return OpenRouterAPIError(
            "OpenRouter rate limit exceeded. Please try again in a moment."
        )

    if "timeout" in error_message.lower() or "504" in error_message:
        return OpenRouterAPIError(
            "OpenRouter request timed out. Please try again."
        )

    if "model" in error_message.lower():
        return OpenRouterAPIError(
            f"OpenRouter model error: {error_message}"
        )

    return OpenRouterAPIError(f"OpenRouter request failed: {error_message}")
