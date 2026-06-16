"""
Local Ollama fallback service for question answering.
"""

from __future__ import annotations

import subprocess
import re

from services.text_cleanup import remove_ansi_escape_codes


DEFAULT_MODEL_NAME = "qwen3:8b"
DEFAULT_TIMEOUT_SECONDS = 300


class OllamaServiceError(RuntimeError):
    """Base error for expected Ollama fallback failures."""


def clean_ollama_response(response: str) -> str:
    """Remove model reasoning/thinking wrappers from Ollama output."""
    if not response:
        return ""

    cleaned = remove_ansi_escape_codes(response)

    cleaned = re.sub(r"(?is)<think>.*?</think>", "", cleaned)
    cleaned = re.sub(r"(?is)<thinking>.*?</thinking>", "", cleaned)

    thinking_markers = [
        "...done thinking.",
        "done thinking.",
        "Final Answer:",
        "Answer:",
    ]
    for marker in thinking_markers:
        if marker.lower() in cleaned.lower():
            parts = re.split(re.escape(marker), cleaned, flags=re.IGNORECASE)
            cleaned = parts[-1].strip()

    if re.search(r"(?im)^\s*thinking\.\.\.\s*$", cleaned):
        parts = re.split(r"(?im)^\s*thinking\.\.\.\s*$", cleaned)
        cleaned = parts[-1].strip()

    json_positions = [pos for pos in (cleaned.find("["), cleaned.find("{")) if pos != -1]
    if json_positions:
        prefix = cleaned[: min(json_positions)].strip()
        if prefix:
            cleaned = cleaned[min(json_positions):].strip()

    cleaned = re.sub(r"(?im)^\s*(reasoning|thoughts|analysis)\s*:.*$", "", cleaned)
    cleaned = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", " ", cleaned)
    return remove_ansi_escape_codes(cleaned)


def _build_prompt(question: str, context: str) -> str:
    return (
        "You are a dyslexia-friendly learning tutor.\n"
        "Use the retrieved document context as the primary source.\n\n"
        f"CONTEXT:\n{context.strip()}\n\n"
        f"QUESTION:\n{question.strip()}\n\n"
        "When the context contains the answer, explain it simply.\n"
        "When the context contains only part of the answer, use the context first, then add helpful general knowledge.\n"
        "When the context does not answer the question, answer from general knowledge and say that the information is not directly in the uploaded document.\n"
        "Keep replies short.\n"
        "Use bullet points.\n"
        "Use simple vocabulary.\n"
        "Be beginner-friendly.\n"
    )


def generate_answer(
    question: str,
    context: str,
    model_name: str = DEFAULT_MODEL_NAME,
) -> str:
    """
    Generate an answer using the local Ollama model.
    """

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    if not context or not context.strip():
        raise ValueError("Context cannot be empty.")

    prompt = _build_prompt(question, context)

    command = [
        "ollama",
        "run",
        model_name,
        "/no_think " + prompt.strip(),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )

    except FileNotFoundError as exc:
        raise OllamaServiceError(
            "Ollama is not installed or not available in PATH."
        ) from exc

    except subprocess.TimeoutExpired as exc:
        raise OllamaServiceError(
            f"Ollama request timed out after {DEFAULT_TIMEOUT_SECONDS} seconds."
        ) from exc

    stderr = (completed.stderr or "").strip()
    stdout = (completed.stdout or "").strip()

    if completed.returncode != 0:

        if "not found" in stderr.lower():
            raise OllamaServiceError(
                f"Model '{model_name}' not found. Run:\nollama pull {model_name}"
            )

        raise OllamaServiceError(
            f"Ollama generation failed:\n{stderr}"
        )

    stdout = clean_ollama_response(stdout)

    if not stdout:
        raise OllamaServiceError(
            "Ollama returned an empty response."
        )

    return stdout


def generate_content(
    prompt: str,
    model_name: str = DEFAULT_MODEL_NAME,
) -> str:
    """Generate content from a prompt without context (for simplification, vocab, visual, etc).
    
    This method is for one-off content generation tasks that don't involve RAG context.
    
    Args:
        prompt: The task prompt (e.g., "Simplify this: ...")
        model_name: Ollama model to use
        
    Returns:
        Generated content text.
        
    Raises:
        ValueError: If prompt is empty.
        OllamaServiceError: If Ollama fails or is unavailable.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")
    
    command = [
        "ollama",
        "run",
        model_name,
        "/no_think " + prompt.strip(),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise OllamaServiceError(
            "Ollama is not installed or not available in PATH."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise OllamaServiceError(
            f"Ollama request timed out after {DEFAULT_TIMEOUT_SECONDS} seconds."
        ) from exc

    stderr = (completed.stderr or "").strip()
    stdout = (completed.stdout or "").strip()

    if completed.returncode != 0:
        if "not found" in stderr.lower():
            raise OllamaServiceError(
                f"Model '{model_name}' not found. Run:\nollama pull {model_name}"
            )
        raise OllamaServiceError(
            f"Ollama generation failed:\n{stderr}"
        )

    stdout = clean_ollama_response(stdout)

    if not stdout:
        raise OllamaServiceError(
            "Ollama returned an empty response."
        )

    return stdout
