"""LLM facade for frontend code.

The real Gemini implementation remains in services/gemini_service.py.
"""

from services.gemini_service import (
    chat_with_gemini,
    extract_vocabulary,
    generate_quiz,
    simplify_document,
    summarize_document,
)
