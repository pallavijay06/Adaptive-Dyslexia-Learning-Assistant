"""Local Ollama fallback service for question answering."""

from __future__ import annotations

import subprocess
from pathlib import Path

DEFAULT_MODEL_NAME = "qwen3:4b"
DEFAULT_TIMEOUT_SECONDS = 30


class OllamaServiceError(RuntimeError):
    """Base error for expected Ollama fallback failures."""


def _build_prompt(question: str, context: str) -> str:
    return (
        "You are a dyslexia-friendly learning tutor.\n"
        "Use the retrieved document context as the primary source.\n\n"
        f"CONTEXT:\n{context.strip()}\n\n"
        f"QUESTION:\n{question.strip()}\n\n"
        "When the context contains the answer, explain it simply.\n"
        "When the context contains only part of the answer, use the context first, then add helpful general knowledge.\n"
        "When the context does not answer the question, answer from general knowledge and say that the information is not directly in the uploaded document.\n"
        "Keep replies short, supportive, beginner-friendly, and dyslexia-friendly.\n"
        "Use short sentences, bullet points, and simple vocabulary.\n"
        "Your goal is to teach, not just retrieve information."
    )


def generate_answer(question: str, context: str, model_name: str = DEFAULT_MODEL_NAME) -> str:
    """Generate an answer using the local Ollama model."""
    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")
    if not context or not context.strip():
        raise ValueError("Context cannot be empty.")

    prompt = _build_prompt(question, context)
    command = ["ollama", "generate", model_name, prompt]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise OllamaServiceError(
            "Ollama CLI is not installed or not on PATH. Install Ollama and run `ollama pull qwen3:4b`."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise OllamaServiceError(
            "Ollama request timed out. Ensure the local Ollama server is running and the model is available."
        ) from exc

    stderr = (completed.stderr or "").strip()
    stdout = (completed.stdout or "").strip()

    if completed.returncode != 0 or not stdout:
        if "not found" in stderr.lower() or "not found" in stdout.lower():
            raise OllamaServiceError(
                f"Ollama model '{model_name}' is missing. Run: ollama pull {model_name}"
            )
        raise OllamaServiceError(
            f"Ollama generation failed: {stderr or stdout or 'unknown error.'}"
        )

    return stdout
