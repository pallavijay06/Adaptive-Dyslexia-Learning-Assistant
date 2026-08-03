"""Educational Knowledge Compression Engine

Converts educational learning points into short, visual learning units
suitable for mind map nodes. The transformation is pedagogical: it
extracts the single phrase a teacher would write inside a node.

This module exposes `compress_educational_knowledge` which accepts an
`EducationalKnowledgeStructure` and returns a new one with compressed
`LearningPoint.text` values (1-4 words, visual, standalone).
"""
from __future__ import annotations

import re
import logging
from typing import Any

from services.knowledge_organization_engine import (
    EducationalKnowledgeStructure,
    EducationalSection,
    LearningPoint,
)

logger = logging.getLogger(__name__)


def compress_educational_knowledge(structure: EducationalKnowledgeStructure) -> EducationalKnowledgeStructure:
    if structure is None:
        raise ValueError("structure cannot be None")

    new_sections: list[EducationalSection] = []
    for section in structure.sections or []:
        compressed_points: list[LearningPoint] = []
        for point in section.learning_points or []:
            original = (point.text or "").strip()
            compressed = _compress_point_to_visual_unit(original)
            if not compressed:
                # fallback to a short cleaned noun phrase
                compressed = _short_noun_phrase(original)
            compressed_points.append(LearningPoint(text=compressed, type="VisualUnit"))

        new_sections.append(
            EducationalSection(
                title=section.title,
                type=section.type,
                pedagogical_role=section.pedagogical_role,
                importance=section.importance,
                learning_points=compressed_points,
            )
        )

    return EducationalKnowledgeStructure(
        chapter_title=structure.chapter_title,
        learning_objective=structure.learning_objective,
        sections=new_sections,
    )


_STOP_WORDS = set(
    [
        "the",
        "a",
        "an",
        "is",
        "are",
        "of",
        "in",
        "on",
        "for",
        "to",
        "with",
        "by",
        "as",
        "that",
        "this",
        "be",
        "from",
        "during",
        "through",
        "into",
        "it",
        "its",
    ]
)


def _compress_point_to_visual_unit(text: str) -> str:
    if not text:
        return ""

    low = text.lower()

    # 1) Formula detection: attempt to map 'X equals Y times Z' -> 'X = Y × Z'
    if "=" in text or " equals " in low or "multiplied by" in low or " times " in low or "×" in text:
        return _to_formula_like(text)

    # 2) Conversion pattern: 'X converts Y into Z' or 'converts Y to Z' -> 'Y → Z'
    m = re.search(r"(?:converts?|transform?s?)\s+(?:the\s+)?([\w\s-]+?)\s+(?:into|to)\s+([\w\s-]+)", low)
    if m:
        a = _short_noun_phrase(m.group(1))
        b = _short_noun_phrase(m.group(2))
        if a and b:
            return f"{a} → {b}"

    # 3) Active subject-action-object: 'Chlorophyll captures sunlight' -> 'Chlorophyll'
    m2 = re.match(r"^([A-Z][\w\- ]{0,40}?)\s+(?:[a-z]+ed|[a-z]+s?)\s+([\w\s-]{1,80})", text)
    if m2:
        subj = m2.group(1).strip()
        # If subject is a meaningful term, prefer it
        if len(subj.split()) <= 3:
            return _title_case(subj)

    # 4) Passive production: 'Glucose is produced' -> 'Glucose Formation'
    if re.search(r"\b(is|are|was|were)\s+(produced|synthesized|formed|created|generated|released)\b", low):
        noun = _first_noun_like(text) or _short_noun_phrase(text)
        if noun:
            return f"{noun} Formation"

    # 5) One-word verbs that indicate a stage: evaporates -> Evaporation
    m3 = re.search(r"\b(evaporat|condens|replicat|divid|mitos|meios)\w*\b", low)
    if m3:
        verb = m3.group(0)
        mapped = _verb_to_noun(verb)
        if mapped:
            return mapped

    # 6) If text already short (<=4 words) and noun-phrase-like, return cleaned title case
    words = [w for w in re.findall(r"[A-Za-z0-9%°μ]+", text) if w.lower() not in _STOP_WORDS]
    if 1 <= len(words) <= 4:
        return _title_case(" ".join(words))

    # 7) Extract prominent capitalized token(s)
    cap = re.findall(r"\b([A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)*)\b", text)
    if cap:
        candidate = cap[0]
        if len(candidate.split()) <= 4:
            return candidate

    # 8) Fall back to the shortest meaningful noun phrase
    return _short_noun_phrase(text)


def _to_formula_like(text: str) -> str:
    # Extract candidate nouns and map to initials: Voltage -> V
    tokens = re.findall(r"[A-Za-z0-9]+", text)
    nouns = [t for t in tokens if len(t) > 0]
    if not nouns:
        return text[:20]
    # Try to find three main nouns by removing common words
    filtered = [t for t in nouns if t.lower() not in _STOP_WORDS]
    if not filtered:
        filtered = nouns
    # Use up to 3 tokens
    picks = filtered[:3]
    # Map picks to uppercase initials if they look like words; keep full if short
    initials = []
    for p in picks:
        if len(p) == 1 or p.isupper():
            initials.append(p)
        else:
            initials.append(p[0].upper())
    if len(initials) == 1:
        return initials[0]
    if len(initials) == 2:
        return f"{initials[0]} = {initials[1]}"
    return f"{initials[0]} = {initials[1]} × {initials[2]}"


def _first_noun_like(text: str) -> str:
    # heuristic: largest capitalized word or first long noun-like token
    m = re.search(r"\b([A-Z][a-z0-9]{2,}(?:\s+[A-Z][a-z0-9]{2,})*)\b", text)
    if m:
        return _title_case(m.group(1))
    tokens = re.findall(r"[A-Za-z0-9]+", text)
    for t in tokens:
        if t.lower() not in _STOP_WORDS and len(t) > 3:
            return _title_case(t)
    return ""


def _short_noun_phrase(text: str, max_words: int = 3) -> str:
    words = [w for w in re.findall(r"[A-Za-z0-9]+", text) if w.lower() not in _STOP_WORDS]
    if not words:
        return ""
    candidate = " ".join(words[:max_words])
    return _title_case(candidate)


def _title_case(s: str) -> str:
    return " ".join([w.capitalize() for w in re.split(r"\s+", s.strip()) if w])


def _verb_to_noun(verb: str) -> str:
    verb = verb.lower()
    mapping = {
        "evaporat": "Evaporation",
        "condens": "Condensation",
        "replicat": "Replication",
        "divid": "Division",
        "mitos": "Mitosis",
        "meios": "Meiosis",
    }
    for k, v in mapping.items():
        if k in verb:
            return v
    return ""
