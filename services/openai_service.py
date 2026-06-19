"""OpenAI LLM service for the cHEAL learning assistant."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from services.text_cleanup import remove_ansi_escape_codes


DEFAULT_MODEL_NAME = "gpt-5"
DEFAULT_TIMEOUT_SECONDS = 60

SYSTEM_INSTRUCTION = """
You are cHEAL, a friendly dyslexia-focused learning assistant.
Explain concepts clearly, use simple language, break answers into small steps,
and keep responses supportive, beginner-friendly, and easy to read.
""".strip()


class OpenAIServiceError(RuntimeError):
    """Raised when OpenAI cannot generate a response."""


def generate_answer(question: str, context: str) -> str:
    """Generate a dyslexia-friendly answer using retrieved document context."""
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
    return _generate_text(prompt)


def generate_content(prompt: str) -> str:
    """Generate one-off content for simplification, vocabulary, visuals, etc."""
    prompt = (prompt or "").strip()
    if not prompt:
        raise ValueError("Prompt cannot be empty.")

    return _generate_text(prompt)


def _generate_text(prompt: str) -> str:
    try:
        client = _get_client()
        response = client.responses.create(
            model=_get_model_name(),
            instructions=SYSTEM_INSTRUCTION,
            input=prompt,
        )
        return remove_ansi_escape_codes(_extract_response_text(response))
    except OpenAIServiceError:
        raise
    except Exception as exc:
        raise _map_openai_error(exc) from exc


def _get_client() -> Any:
    api_key = _load_api_key()

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise OpenAIServiceError(
            "OpenAI SDK is not installed. Run: pip install openai"
        ) from exc

    try:
        return OpenAI(api_key=api_key, timeout=DEFAULT_TIMEOUT_SECONDS)
    except Exception as exc:
        raise OpenAIServiceError("Could not initialize OpenAI client.") from exc


def _load_api_key() -> str:
    _load_dotenv_files()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise OpenAIServiceError("Missing OpenAI API key. Add OPENAI_API_KEY to .env.")

    return api_key


def _get_model_name() -> str:
    _load_dotenv_files()
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL_NAME).strip() or DEFAULT_MODEL_NAME


def _load_dotenv_files() -> None:
    root_dir = Path(__file__).resolve().parents[1]
    dotenv_paths = [root_dir / ".env", root_dir / "services" / ".env"]

    try:
        from dotenv import load_dotenv
    except ImportError:
        for dotenv_path in dotenv_paths:
            _load_dotenv_without_dependency(dotenv_path)
        return

    for dotenv_path in dotenv_paths:
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path, override=False)


def _load_dotenv_without_dependency(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text and output_text.strip():
        return remove_ansi_escape_codes(output_text)

    try:
        chunks: list[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    chunks.append(text)
        if chunks:
            return remove_ansi_escape_codes("\n".join(chunks))
    except Exception:
        pass

    raise OpenAIServiceError("OpenAI returned an empty response.")


def _map_openai_error(exc: Exception) -> OpenAIServiceError:
    exc_name = exc.__class__.__name__
    message = str(exc).lower()

    if exc_name == "AuthenticationError":
        return OpenAIServiceError("OpenAI authentication failed. Check OPENAI_API_KEY.")
    if exc_name == "RateLimitError":
        if "quota" in message or "insufficient" in message:
            return OpenAIServiceError("OpenAI quota exceeded.")
        return OpenAIServiceError("OpenAI rate limit reached.")
    if exc_name == "APIConnectionError":
        return OpenAIServiceError("Could not connect to OpenAI.")
    if exc_name in {"APITimeoutError", "Timeout", "TimeoutError"}:
        return OpenAIServiceError("OpenAI request timed out.")
    if exc_name == "BadRequestError":
        return OpenAIServiceError("OpenAI rejected the request.")
    if exc_name == "PermissionDeniedError":
        return OpenAIServiceError("OpenAI key does not have permission for this model.")
    if exc_name == "NotFoundError":
        return OpenAIServiceError("Configured OpenAI model was not found.")
    if exc_name == "APIStatusError":
        status_code = getattr(exc, "status_code", None)
        if status_code == 401:
            return OpenAIServiceError("OpenAI authentication failed. Check OPENAI_API_KEY.")
        if status_code == 429:
            return OpenAIServiceError("OpenAI rate limit or quota reached.")
        if status_code and status_code >= 500:
            return OpenAIServiceError("OpenAI service is temporarily unavailable.")

    return OpenAIServiceError("OpenAI generation failed.")
