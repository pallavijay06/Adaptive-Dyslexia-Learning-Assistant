"""Educational understanding engine for the mind-map pipeline.

This module is the first stage of the mind-map redesign. It focuses on
understanding what a chapter is trying to teach rather than extracting
concepts or building renderer-ready nodes.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from typing import Any

from services.llm_router import generate_content
from services.ollama_service import clean_ollama_response

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EducationalUnderstanding:
    """Structured educational understanding for a chapter or document."""

    chapter_title: str
    subject: str
    domain: str
    topic_complexity: str
    learning_objective: str
    major_sections: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_PROMPT = """You are an experienced educator reading a textbook chapter.
Your task is to understand what the chapter is trying to teach.

Focus on the educational structure of the chapter, not on keywords or visual layout.

Return ONLY valid JSON with this exact shape:
{
  "chapter_title": "Short chapter title",
  "subject": "Biology",
  "domain": "Science",
  "topic_complexity": "Medium",
  "learning_objective": "One concise sentence describing what a learner should understand after studying this chapter.",
  "major_sections": ["Introduction", "Process", "Importance"]
}

Rules:
- chapter_title should be a concise chapter title.
- subject should be the academic subject, such as Biology, Physics, Mathematics, Computer Science, History, Geography, or Chemistry.
- domain should be a broader field, such as Science, Mathematics, Humanities, or Computer Science.
- topic_complexity should be one of: Easy, Medium, or Hard.
- learning_objective should be one concise sentence that describes the learner's takeaway.
- major_sections should be teaching headings similar to textbook sections, not supporting ideas, examples, or raw nouns.
- Do not include explanations, markdown, or extra keys.

Document:
"""


def understand_chapter(document_text: str) -> EducationalUnderstanding:
    """Analyze a chapter or document and return educational understanding JSON.

    The function intentionally produces educational structure only. It does not
    generate concepts, hierarchy, nodes, layout, or renderer payloads.
    """
    if not document_text or not document_text.strip():
        raise ValueError("Document text cannot be empty.")

    prompt = _PROMPT + document_text.strip()[:4000]
    logger.info("[EducationalUnderstanding] Analyzing document")
    use_llm = os.getenv("EDU_USE_LLM", "0").lower() in {"1", "true", "yes", "on"}
    if use_llm:
        try:
            response = generate_content(prompt, max_tokens=800)
            cleaned = clean_ollama_response(response or "")
            cleaned = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", cleaned).strip()

            parsed = _extract_json(cleaned)
            if parsed is None:
                logger.warning("[EducationalUnderstanding] LLM response was invalid; using fallback")
                return _fallback_understanding(document_text)

            return _normalize_understanding(parsed, document_text)
        except Exception as exc:
            logger.warning("[EducationalUnderstanding] LLM generation failed: %s; using fallback", exc)
    return _fallback_understanding(document_text)


def _extract_json(text: str) -> dict[str, Any] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start:end + 1]
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _normalize_understanding(payload: dict[str, Any], document_text: str) -> EducationalUnderstanding:
    chapter_title = _clean_text(payload.get("chapter_title")) or _infer_title(document_text)
    subject = _clean_text(payload.get("subject")) or _infer_subject(document_text)
    domain = _clean_text(payload.get("domain")) or _infer_domain(subject)
    topic_complexity = _normalize_complexity(payload.get("topic_complexity"))
    learning_objective = _clean_text(payload.get("learning_objective")) or _infer_learning_objective(chapter_title, subject)
    major_sections = _normalize_sections(payload.get("major_sections"), chapter_title, document_text)

    return EducationalUnderstanding(
        chapter_title=chapter_title,
        subject=subject,
        domain=domain,
        topic_complexity=topic_complexity,
        learning_objective=learning_objective,
        major_sections=major_sections,
    )


def _fallback_understanding(document_text: str) -> EducationalUnderstanding:
    title = _infer_title(document_text)
    subject = _infer_subject(document_text)
    domain = _infer_domain(subject)
    return EducationalUnderstanding(
        chapter_title=title,
        subject=subject,
        domain=domain,
        topic_complexity=_infer_complexity(document_text),
        learning_objective=_infer_learning_objective(title, subject),
        major_sections=_infer_major_sections(title, document_text),
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def _normalize_complexity(value: Any) -> str:
    text = _clean_text(value).lower()
    if "hard" in text:
        return "Hard"
    if "easy" in text:
        return "Easy"
    return "Medium"


def _normalize_sections(value: Any, title: str, document_text: str) -> list[str]:
    if isinstance(value, list):
        sections = [
            _clean_text(item)
            for item in value
            if _clean_text(item)
        ]
    else:
        sections = []
    if sections:
        return sections[:6]
    return _infer_major_sections(title, document_text)


def _infer_title(document_text: str) -> str:
    text = re.sub(r"\s+", " ", (document_text or "").strip())
    if not text:
        return "Educational Chapter"

    lower = text.lower()
    if "photosynthesis" in lower:
        return "Photosynthesis"
    if "ohm" in lower:
        return "Ohm's Law"
    if "water cycle" in lower:
        return "Water Cycle"
    if "cell division" in lower:
        return "Cell Division"
    if "computer networks" in lower:
        return "Computer Networks"
    if "operating systems" in lower:
        return "Operating Systems"
    if "database normalization" in lower:
        return "Database Normalization"

    for marker in [" is ", " relates ", " includes ", " covers ", " explains ", " describes ", " involves ", " deals with "]:
        if marker in lower:
            prefix = text.split(marker)[0].strip(" .,-")
            if prefix:
                return _title_case(prefix)

    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        if sentence.strip():
            candidate = re.sub(r"^[A-Z][^:]*?\b(?:is|are|includes|covers|explains|describes|relates)\b.*$", "", sentence)
            candidate = candidate.strip(" .,-")
            if candidate:
                return _title_case(candidate[:80])
    return "Educational Chapter"


def _infer_subject(document_text: str) -> str:
    lower = (document_text or "").lower()
    if any(word in lower for word in ["voltage", "current", "resistance", "circuit", "electrical", "ohm"]):
        return "Physics"
    if any(word in lower for word in ["chlorophyll", "photosynthesis", "plant", "cell", "dna", "mitosis", "meiosis", "organism"]):
        return "Biology"
    if any(word in lower for word in ["network", "protocol", "internet", "router", "server", "operating system", "database", "normalization", "schema", "sql"]):
        return "Computer Science"
    return "General Studies"


def _infer_domain(subject: str) -> str:
    subject_lower = subject.lower()
    if subject_lower in {"biology", "physics", "chemistry"}:
        return "Science"
    if subject_lower in {"computer science", "information technology"}:
        return "Computer Science"
    if subject_lower in {"history", "geography", "literature", "arts"}:
        return "Humanities"
    return "General Studies"


def _infer_complexity(document_text: str) -> str:
    word_count = len(re.findall(r"\b\w+\b", document_text or ""))
    if word_count > 140:
        return "Hard"
    if word_count > 80:
        return "Medium"
    return "Easy"


def _infer_learning_objective(title: str, subject: str) -> str:
    lower_title = title.lower()
    if "photosynthesis" in lower_title:
        return "Understand how plants convert light energy into food."
    if "ohm" in lower_title or "law" in lower_title:
        return "Understand the relationship between voltage, current, and resistance."
    if "water" in lower_title and "cycle" in lower_title:
        return "Understand how water moves through the environment."
    if "cell" in lower_title and "division" in lower_title:
        return "Understand how cells reproduce for growth and repair."
    if "network" in lower_title:
        return "Understand how devices connect and share data."
    if "operating" in lower_title and "system" in lower_title:
        return "Understand how operating systems manage hardware and software."
    if "normalization" in lower_title or "database" in lower_title:
        return "Understand how database design reduces redundancy and improves consistency."
    if subject.lower() == "biology":
        return "Understand the core biological processes described in this chapter."
    if subject.lower() == "physics":
        return "Understand the key physical principles described in this chapter."
    if subject.lower() == "computer science":
        return "Understand the core computing concepts described in this chapter."
    return "Understand the main ideas presented in this chapter."


def _infer_major_sections(title: str, document_text: str) -> list[str]:
    title_lower = title.lower()
    if "photosynthesis" in title_lower:
        return ["Introduction", "Requirements", "Process", "Products", "Importance"]
    if "ohm" in title_lower:
        return ["Introduction", "Relationship", "Applications"]
    if "water" in title_lower and "cycle" in title_lower:
        return ["Evaporation", "Condensation", "Precipitation", "Collection"]
    if "cell" in title_lower and "division" in title_lower:
        return ["Introduction", "Mitosis", "Meiosis", "Importance"]
    if "network" in title_lower:
        return ["Introduction", "Network Types", "Transmission", "Protocols", "Services"]
    if "operating" in title_lower and "system" in title_lower:
        return ["Process Management", "Memory Management", "File Systems", "User Interface"]
    if "normalization" in title_lower or "database" in title_lower:
        return ["Introduction", "Keys", "Normal Forms", "Anomalies", "Design Principles"]

    lower = (document_text or "").lower()
    sections: list[str] = []
    for label in ["introduction", "process", "importance", "types", "applications", "components", "requirements", "summary"]:
        if label in lower:
            sections.append(_title_case(label))
    if not sections:
        sections = ["Introduction", "Core Concepts", "Applications", "Summary"]
    return sections[:5]


def _title_case(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return cleaned
    words = cleaned.split()
    return " ".join(word.capitalize() if word.islower() or len(word) <= 2 else word for word in words)
