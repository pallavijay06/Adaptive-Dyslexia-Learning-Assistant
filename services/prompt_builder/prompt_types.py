"""Prompt type definitions for the Prompt Builder.

Adding a new prompt type in the future requires only:
  1. Adding a new member to PromptType.
  2. Adding its filter rules to personalization.py.
Nothing else needs to change.
"""

from enum import Enum


class PromptType(str, Enum):
    NOTES      = "notes"
    VISUAL     = "visual"
    QUIZ       = "quiz"
    VOCABULARY = "vocabulary"
    AI_TUTOR   = "ai_tutor"
    RAG_CHAT   = "rag_chat"
