"""Educational Concept Labeling Engine (ECLE)

Converts validated educational learning points into textbook-style concept labels
using a section-aware multi-stage architecture.

The engine reasons over an entire educational section before assigning labels to
individual learning points, preserving the public interface used by the rest of
the pipeline.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from services.knowledge_organization_engine import (
    EducationalKnowledgeStructure,
    EducationalSection,
    LearningPoint,
)
from services.llm_router import generate_content
from services.ollama_service import clean_ollama_response

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SectionContext:
    chapter_title: str
    learning_objective: str
    section_title: str
    section_type: str
    pedagogical_role: str
    learning_points: list[LearningPoint]


@dataclass(frozen=True)
class SectionLabelingResult:
    section_summary: str
    learning_points: list[dict[str, str]]


_ALLOWED_EDUCATIONAL_ROLES = {
    "Definition",
    "Process",
    "Stage",
    "Input",
    "Output",
    "Relationship",
    "Formula",
    "Law",
    "Rule",
    "Mechanism",
    "Component",
    "Function",
    "Application",
    "Advantage",
    "Disadvantage",
    "Requirement",
    "Cause",
    "Effect",
    "Characteristic",
    "Example",
    "Comparison",
    "Classification",
}

_REJECTED_GENERIC_LABELS = {
    "water",
    "leaves",
    "plants",
    "voltage",
    "memory",
    "dna",
    "current",
    "resistance",
    "sunlight",
    "temperature",
    "wire",
    "root",
    "leaf",
    "plant",
}


def label_educational_knowledge(structure: EducationalKnowledgeStructure) -> EducationalKnowledgeStructure:
    if structure is None:
        raise ValueError("structure cannot be None")

    labeled_sections: list[EducationalSection] = []
    for section in structure.sections or []:
        if not section.learning_points:
            labeled_sections.append(section)
            continue

        context = _build_section_context(structure, section)
        primary_result = _analyze_section_with_llm(context)
        validated_result = _validate_and_refine_section_labels(context, primary_result)
        labeled_points = _map_labels_to_learning_points(section.learning_points, validated_result.learning_points)
        labeled_sections.append(
            EducationalSection(
                title=section.title,
                type=section.type,
                pedagogical_role=section.pedagogical_role,
                importance=section.importance,
                learning_points=labeled_points,
            )
        )

    return EducationalKnowledgeStructure(
        chapter_title=structure.chapter_title,
        learning_objective=structure.learning_objective,
        sections=labeled_sections,
    )


def _build_section_context(structure: EducationalKnowledgeStructure, section: EducationalSection) -> SectionContext:
    return SectionContext(
        chapter_title=_normalize_text(structure.chapter_title),
        learning_objective=_normalize_text(structure.learning_objective),
        section_title=_normalize_text(section.title),
        section_type=_normalize_text(section.type),
        pedagogical_role=_normalize_text(section.pedagogical_role),
        learning_points=[
            LearningPoint(text=_normalize_text(point.text), type=_normalize_text(point.type) or "Characteristic")
            for point in section.learning_points or []
            if _normalize_text(point.text)
        ],
    )


def _analyze_section_with_llm(context: SectionContext) -> SectionLabelingResult:
    prompt = _SECTION_PROMPT.format(
        chapter_title=context.chapter_title or "Unknown chapter",
        learning_objective=context.learning_objective or "Unknown objective",
        section_title=context.section_title or "Unknown section",
        section_type=context.section_type or "Unknown type",
        pedagogical_role=context.pedagogical_role or "Unknown role",
        learning_points="\n".join(f"{index + 1}. {point.text}" for index, point in enumerate(context.learning_points)),
    )
    response = _json_response(prompt, max_tokens=900)
    parsed = _parse_section_json(response)
    if parsed is None:
        raise ValueError(f"Unable to parse section labeling response for section: {context.section_title}")

    learning_point_entries = parsed.get("learning_points") or []
    if not isinstance(learning_point_entries, list):
        raise ValueError(f"Section labeling response missing learning_points for section: {context.section_title}")

    if len(learning_point_entries) != len(context.learning_points):
        raise ValueError(
            f"Section labeling response expected {len(context.learning_points)} learning points but received {len(learning_point_entries)}"
        )

    normalized_entries: list[dict[str, str]] = []
    for entry in learning_point_entries:
        if not isinstance(entry, dict):
            raise ValueError("Each learning point entry in the section response must be an object")
        original = _normalize_text(entry.get("original_learning_point"))
        if not original:
            raise ValueError("Section labeling response contains an empty original_learning_point")
        normalized_entries.append({
            "original_learning_point": original,
            "educational_role": _normalize_text(entry.get("educational_role")) or "Characteristic",
            "educational_concept": _normalize_text(entry.get("educational_concept")),
            "concept_label": _normalize_text(entry.get("concept_label")),
        })

    return SectionLabelingResult(
        section_summary=_normalize_text(parsed.get("section_summary")),
        learning_points=normalized_entries,
    )


def _validate_and_refine_section_labels(context: SectionContext, result: SectionLabelingResult) -> SectionLabelingResult:
    failed_indices: list[int] = []
    validated_entries: list[dict[str, str]] = []
    for index, entry in enumerate(result.learning_points):
        label = _cleanup_label(entry.get("concept_label", ""))
        if not label or _is_rejected_label(label):
            failed_indices.append(index)
            validated_entries.append(entry)
            continue
        validated_entries.append({
            **entry,
            "concept_label": label,
        })

    if not failed_indices:
        return SectionLabelingResult(section_summary=result.section_summary, learning_points=validated_entries)

    for failed_index in failed_indices:
        failed_entry = validated_entries[failed_index]
        refined_label = _refine_label(context, failed_entry)
        validated_entries[failed_index] = {
            **failed_entry,
            "concept_label": refined_label,
        }

    return SectionLabelingResult(section_summary=result.section_summary, learning_points=validated_entries)


def _map_labels_to_learning_points(original_points: list[LearningPoint], labeled_entries: list[dict[str, str]]) -> list[LearningPoint]:
    if len(original_points) != len(labeled_entries):
        raise ValueError("Section labeling result length does not match the number of learning points")

    mapped: list[LearningPoint] = []
    for point, entry in zip(original_points, labeled_entries):
        original_text = _normalize_text(point.text)
        entry_text = _normalize_text(entry.get("original_learning_point", ""))
        if original_text != entry_text:
            raise ValueError(
                f"Deterministic mapping failed for learning point: {original_text} != {entry_text}"
            )
        label = _cleanup_label(entry.get("concept_label", ""))
        if not label or _is_rejected_label(label):
            raise ValueError(f"Unable to generate a confident concept label for learning point: {original_text}")
        mapped.append(LearningPoint(text=label, type=point.type))
    return mapped


def _refine_label(context: SectionContext, entry: dict[str, str]) -> str:
    prompt = _REFINEMENT_PROMPT.format(
        chapter_title=context.chapter_title or "Unknown chapter",
        learning_objective=context.learning_objective or "Unknown objective",
        section_title=context.section_title or "Unknown section",
        section_type=context.section_type or "Unknown type",
        pedagogical_role=context.pedagogical_role or "Unknown role",
        educational_role=entry.get("educational_role", "Characteristic"),
        educational_concept=entry.get("educational_concept", ""),
        original_learning_point=entry.get("original_learning_point", ""),
        rejected_label=entry.get("concept_label", ""),
    )
    response = _llm_response(prompt, max_tokens=80)
    label = _cleanup_label(response)
    if not label or _is_rejected_label(label):
        raise ValueError(f"Unable to refine concept label for: {entry.get('original_learning_point', '')}")
    return label


def _json_response(prompt: str, *, max_tokens: int) -> str:
    response = generate_content(prompt, max_tokens=max_tokens)
    cleaned = clean_ollama_response(response or "")
    cleaned = _strip_code_blocks(cleaned)
    return cleaned


def _llm_response(prompt: str, *, max_tokens: int) -> str:
    response = generate_content(prompt, max_tokens=max_tokens)
    cleaned = clean_ollama_response(response or "")
    cleaned = _strip_code_blocks(cleaned)
    return _extract_first_line(cleaned)


def _parse_section_json(response: str) -> dict[str, Any] | None:
    cleaned = _strip_code_blocks(response)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return None
    normalized = _normalize_json_keys(parsed)
    return normalized if isinstance(normalized, dict) else None


def _normalize_json_keys(value: Any) -> Any:
    if isinstance(value, dict):
        normalized_dict: dict[str, Any] = {}
        for key, nested_value in value.items():
            canonical_key = _canonicalize_json_key(key)
            normalized_dict[canonical_key] = _normalize_json_keys(nested_value)
        return normalized_dict

    if isinstance(value, list):
        return [_normalize_json_keys(item) for item in value]

    return value


def _canonicalize_json_key(key: Any) -> str:
    text = str(key).strip()
    text = re.sub(r"(?<!^)(?=[A-Z])", "_", text)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_").lower()

    alias_map = {
        "section_summary": "section_summary",
        "sectionsummary": "section_summary",
        "section_summary": "section_summary",
        "learning_points": "learning_points",
        "learningpoints": "learning_points",
        "original_learning_point": "original_learning_point",
        "originallearningpoint": "original_learning_point",
        "educational_role": "educational_role",
        "educationalrole": "educational_role",
        "educational_concept": "educational_concept",
        "educationalconcept": "educational_concept",
        "concept_label": "concept_label",
        "conceptlabel": "concept_label",
    }
    return alias_map.get(text, text)


def _strip_code_blocks(text: str) -> str:
    return re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", text).strip()


def _extract_first_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return text.strip()


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def _cleanup_label(label: str) -> str:
    if not label:
        return ""
    cleaned = _extract_first_line(label)
    cleaned = re.sub(r"^(Concept label|Label|Answer|Response)\s*[:\-\s]*", "", cleaned, flags=re.I)
    cleaned = cleaned.strip(" .-–—:;,")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[^\w\s'’\-]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""
    words = [word for word in cleaned.split() if word]
    if len(words) > 4:
        cleaned = " ".join(words[:4])
    return cleaned


def _is_rejected_label(label: str) -> bool:
    if not label:
        return True
    normalized = _cleanup_label(label).lower()
    if not normalized:
        return True
    if normalized in _REJECTED_GENERIC_LABELS:
        return True
    if any(token in normalized for token in {"because", "when", "if", "then", "this", "that"}):
        return True
    return False


_SECTION_PROMPT = """You are an experienced textbook author preparing a mind map for a chapter.

Analyze the ENTIRE educational section as a coherent unit before assigning labels.
You must understand:
- what the section teaches
- how the learning points relate
- which concepts belong together
- how the concepts differ

Return ONLY valid JSON with this exact structure:
{
  "section_summary": "...",
  "learning_points": [
    {
      "original_learning_point": "...",
      "educational_role": "...",
      "educational_concept": "...",
      "concept_label": "..."
    }
  ]
}

Rules:
- Preserve the original ordering of the learning points.
- Each learning point must appear exactly once.
- The educational role must be a concise educational role such as Definition, Process, Formula, Mechanism, Requirement, Application, Characteristic, or Example.
- The educational concept must be the actual textbook concept, not a keyword list and not a sentence fragment.
- The concept label must be 1 to 4 words, student-friendly, textbook-style, and a noun phrase.
- Do not include markdown or extra keys.

Chapter: {chapter_title}
Learning objective: {learning_objective}
Section title: {section_title}
Section type: {section_type}
Pedagogical role: {pedagogical_role}
Learning points:
{learning_points}

JSON:
"""

_REFINEMENT_PROMPT = """You are an experienced textbook author.

The previous concept label for this learning point was not sufficiently educational.
Refine it using the same section context.
Requirements:
- 1 to 4 words
- textbook heading
- student-friendly
- noun phrase
- not a generic physical object or isolated entity

Chapter: {chapter_title}
Learning objective: {learning_objective}
Section title: {section_title}
Section type: {section_type}
Pedagogical role: {pedagogical_role}
Educational role: {educational_role}
Educational concept: {educational_concept}
Original learning point: {original_learning_point}
Rejected label: {rejected_label}

Improved label:
"""
