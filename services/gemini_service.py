"""Reusable Gemini chat service for the cHEAL learning assistant.

This module owns all Gemini-specific behavior:
- loading the API key from .env
- creating the Gemini model/client once
- keeping an in-memory multi-turn chat history
- returning plain response text to the backend route

The route layer should call chat_with_gemini(...) instead of importing Gemini
SDK objects directly. That keeps document chat, dyslexia-focused prompting, and
future parser integrations easier to add later.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock
from typing import Any


DEFAULT_MODEL_NAME = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """
You are cHEAL, a friendly dyslexia-focused learning assistant.
Explain concepts clearly, use simple language, break answers into small steps,
and invite the learner to ask follow-up questions. When document content is
provided later, answer from that content first and say when something is not in
the document.
""".strip()


class GeminiServiceError(RuntimeError):
    """Base error for expected Gemini service failures."""


class GeminiConfigurationError(GeminiServiceError):
    """Raised when Gemini cannot be configured, usually because the key is missing."""


class GeminiAPIError(GeminiServiceError):
    """Raised when Gemini fails to generate a response."""


_client: Any | None = None
_chat: Any | None = None
_history: list[dict[str, str]] = []
_lock = Lock()


def chat_with_gemini(user_message: str, document_text: str | None = None) -> str:
    """Send a user message to Gemini and return the assistant response text.

    The service keeps chat history in memory for the current backend process, so
    follow-up questions can use earlier user and assistant turns. This function
    is intentionally small from the route's point of view: routes validate JSON,
    then pass the message here.

    Args:
        user_message: The learner's message.

    Returns:
        Gemini's response text.

    Raises:
        ValueError: If the message is empty.
        GeminiConfigurationError: If the API key or SDK is missing.
        GeminiAPIError: If Gemini or the network request fails.
    """
    message = build_document_prompt(user_message, document_text)
    return _send_chat_message(message)


def generate_answer(question: str, context: str | None = None) -> str:
    """Generate a Gemini answer using retrieved context, not the full document."""
    message = build_document_prompt(question, context)
    return _send_chat_message(message)


def _send_chat_message(message: str) -> str:
    message = (message or "").strip()
    if not message:
        raise ValueError("Message cannot be empty.")

    with _lock:
        chat = _get_chat()

        try:
            response = chat.send_message(message)
            response_text = _extract_response_text(response)
        except GeminiServiceError:
            raise
        except Exception as exc:
            raise GeminiAPIError(f"Gemini request failed: {exc}") from exc

        _history.append({"role": "user", "content": message})
        _history.append({"role": "assistant", "content": response_text})
        return response_text


def get_chat_history() -> list[dict[str, str]]:
    """Return a copy of the current in-memory conversation history."""
    with _lock:
        return list(_history)


def reset_chat_history() -> None:
    """Clear the current conversation and start a fresh Gemini chat session."""
    global _chat

    with _lock:
        _history.clear()
        _chat = None


def build_document_prompt(user_message: str, document_text: str | None = None) -> str:
    """Build a future-compatible prompt for document-aware chat.

    If retrieved context is available, use it to answer the learner. Otherwise,
    continue to support older endpoints that pass full document text.
    """
    if not document_text:
        return user_message

    return (
        "You are a dyslexia-friendly learning tutor.\n"
        "Use the retrieved document context as the primary source.\n\n"
        f"CONTEXT:\n{document_text.strip()}\n\n"
        f"QUESTION:\n{user_message.strip()}\n\n"
        "When the context contains the answer, explain it simply.\n"
        "When the context contains only part of the answer, use the context first, then add helpful general knowledge.\n"
        "When the context does not answer the question, answer from general knowledge and say that the information is not directly in the uploaded document.\n"
        "Keep replies short, supportive, beginner-friendly, and dyslexia-friendly.\n"
        "Use short sentences, bullet points, and simple vocabulary.\n"
        "Your goal is to teach, not just retrieve information."
    )


def summarize_document(document_text: str) -> str:
    """Summarize uploaded content in dyslexia-friendly language."""
    return _run_document_task(
        document_text,
        "Summarize this document in simple language with short sections.",
    )


def simplify_document(document_text: str) -> str:
    """Rewrite uploaded content into simpler, learner-friendly wording."""
    return _run_document_task(
        document_text,
        "Simplify this document for a dyslexic learner. Use short sentences and clear bullets.",
    )


def generate_quiz(document_text: str) -> str:
    """Generate a short quiz from uploaded content."""
    return _run_document_task(
        document_text,
        "Create a 5-question quiz from this document. Include answers after the questions.",
    )


def extract_vocabulary(document_text: str) -> str:
    """Extract key terms and simple definitions from uploaded content."""
    return _run_document_task(
        document_text,
        "Extract important vocabulary from this document and define each term simply.",
    )


def validate_gemini_startup() -> bool:
    """Validate API key, SDK import, and Gemini connectivity at backend startup.

    Returns:
        True when Gemini is reachable, otherwise False. The function prints a
        clear message because it is intended to run when the Flask app starts.
    """
    try:
        client = _get_client()
        model_name = _get_model_name()
        response = client.models.generate_content(
            model=model_name,
            contents="Reply with only: cHEAL Gemini startup check passed.",
        )
        response_text = _extract_response_text(response)
    except GeminiServiceError as exc:
        print(f"[cHEAL] Gemini startup validation failed: {exc}")
        return False
    except Exception as exc:
        print(f"[cHEAL] Gemini startup validation failed: {exc}")
        return False

    print(
        f"[cHEAL] Gemini ready using model '{model_name}'. "
        f"Validation response: {response_text}"
    )
    return True


def _get_client() -> Any:
    """Create and cache the google-genai Client once per backend process."""
    global _client

    if _client is not None:
        return _client

    api_key = _load_api_key()

    try:
        import google.genai as genai
    except ImportError as exc:
        raise GeminiConfigurationError(
            "Gemini SDK is not installed. Run: pip install google-genai"
        ) from exc

    try:
        _client = genai.Client(api_key=api_key)
        return _client
    except Exception as exc:
        raise GeminiConfigurationError(f"Could not initialize Gemini client: {exc}") from exc


def _get_chat() -> Any:
    """Create and cache the Gemini chat object once per backend process."""
    global _chat

    if _chat is not None:
        return _chat

    try:
        from google.genai import types

        client = _get_client()
        config = types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
        _chat = client.chats.create(model=_get_model_name(), config=config, history=[])
        return _chat
    except Exception as exc:
        raise GeminiConfigurationError(f"Could not initialize Gemini chat: {exc}") from exc


def _run_document_task(document_text: str, instruction: str) -> str:
    """Run one document-processing task without changing the chat history."""
    text = (document_text or "").strip()
    if not text:
        raise ValueError("Document text cannot be empty.")

    prompt = (
        f"{instruction}\n\n"
        "DOCUMENT CONTENT:\n"
        f"{text}"
    )

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=_get_model_name(),
            contents=prompt,
        )
        return _extract_response_text(response)
    except GeminiServiceError:
        raise
    except Exception as exc:
        raise GeminiAPIError(f"Gemini document task failed: {exc}") from exc


def _load_api_key() -> str:
    """Load GEMINI_API_KEY from environment variables or .env files."""
    _load_dotenv_files()

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise GeminiConfigurationError(
            "Missing Gemini API key. Add GEMINI_API_KEY=your_key to .env."
        )

    return api_key


def _get_model_name() -> str:
    """Return the configured Gemini model, defaulting to the tested model."""
    _load_dotenv_files()
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL_NAME).strip() or DEFAULT_MODEL_NAME


def _load_dotenv_files() -> None:
    """Load .env values, preferring python-dotenv and falling back to a tiny parser."""
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
    """Small .env fallback so local development still works without python-dotenv."""
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
    """Safely read text from a Gemini response object."""
    text = getattr(response, "text", None)
    if text and text.strip():
        return text.strip()

    raise GeminiAPIError("Gemini returned an empty response.")
