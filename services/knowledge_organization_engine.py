"""Knowledge organization engine for the mind-map pipeline.

This module takes the output of the educational understanding engine and
organizes it into a textbook-like knowledge structure without producing
renderer-specific JSON or layout data.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from typing import Any

from services.educational_understanding_engine import EducationalUnderstanding
from services.llm_router import generate_content
from services.ollama_service import clean_ollama_response

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LearningPoint:
    text: str
    type: str


@dataclass(frozen=True)
class EducationalSection:
    title: str
    type: str
    pedagogical_role: str
    importance: float
    learning_points: list[LearningPoint]

    @property
    def items(self) -> list[str]:
        """Backward-compatible access to the learning-point texts."""
        return [point.text for point in self.learning_points]


@dataclass(frozen=True)
class EducationalKnowledgeStructure:
    chapter_title: str
    learning_objective: str
    sections: list[EducationalSection]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Backward-compatible aliases for the older generic naming.
KnowledgeSection = EducationalSection
KnowledgeStructure = EducationalKnowledgeStructure


_PROMPT = """You are an experienced textbook author organizing knowledge for a chapter.
You will be given the educational understanding of a chapter.
Your job is to organize the chapter into a clean textbook-like structure.

For each major educational section, identify the supporting educational ideas that naturally belong under that section.
Do NOT extract raw keywords from the document.
Do NOT summarize the document.
Do NOT generate renderer JSON, positions, colors, or layout data.
Do NOT duplicate ideas across sections.

Return ONLY valid JSON with this exact shape:
{
  "chapter_title": "Chapter title",
  "learning_objective": "The learning objective",
  "sections": [
    {
      "title": "Section title",
      "importance": 0.95,
      "items": ["Supporting idea 1", "Supporting idea 2"]
    }
  ]
}

Rules:
- Each section title must be one of the provided major sections.
- Each item should be a supporting educational idea that belongs under that section.
- Use 2 to 5 items per section.
- importance should be a float between 0.0 and 1.0.
- Keep the structure educational and textbook-like.
- Do not include markdown or extra keys.

Educational understanding:
"""


def organize_knowledge(understanding: EducationalUnderstanding, document_text: str | None = None) -> EducationalKnowledgeStructure:
    """Organize educational understanding into a textbook-style educational model."""
    if understanding is None:
        raise ValueError("Educational understanding cannot be None.")
    logger.info("[KnowledgeOrganization] Organizing knowledge (algorithmic organizer)")

    text = (document_text or "").strip()

    # Prefer an LLM-generated structure when explicitly enabled and available.
    use_llm = os.getenv("EDU_USE_LLM", "0").lower() in {"1", "true", "yes", "on"}
    if use_llm:
        try:
            prompt = _PROMPT + json.dumps(understanding.to_dict(), ensure_ascii=False)
            response = generate_content(prompt, max_tokens=900)
            cleaned = clean_ollama_response(response or "")
            cleaned = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", cleaned).strip()
            parsed = _extract_json(cleaned)
            if parsed is not None:
                # If LLM returns a valid payload, normalize and use it.
                return _normalize_structure(parsed, understanding)
        except Exception as exc:
            logger.warning("[KnowledgeOrganization] LLM generation failed: %s; falling back to algorithmic organizer", exc)

    # Algorithmic, teacher-inspired organizer (deterministic)
    sections = _derive_educational_structure(understanding, text)
    if not sections:
        return _fallback_structure(understanding)

    return EducationalKnowledgeStructure(
        chapter_title=understanding.chapter_title,
        learning_objective=understanding.learning_objective,
        sections=sections,
    )


def _derive_educational_structure(understanding: EducationalUnderstanding, text: str) -> list[EducationalSection]:
    """Derive a dynamic set of pedagogical sections from the chapter text.

    This function detects which pedagogical categories are relevant to the
    topic (e.g., Purpose, Process, Components, Formula, Applications) and
    extracts representative learning points for each category. It avoids
    using document-outline headings and does not rely on fixed templates.
    """
    if not text:
        return []

    lower = text.lower()

    # Candidate detectors: each maps to a category name and keywords to search for.
    detectors = [
        ("Definition", ["is a", "is an", "definition", "refers to", "means"]),
        ("Purpose", ["important", "purpose", "why", "help", "used to"]),
        ("Components", ["consists of", "composed of", "parts", "components", "elements"]),
        ("Process", ["process", "steps", "stages", "first", "then", "finally", "sequence"]),
        ("Inputs", ["input", "requires", "needs", "requires", "needs", "depends on", "supply"]),
        ("Outputs", ["output", "produce", "result", "produces", "yields", "forms"]),
        ("Formula", ["=", "formula", "v =", "= i", "= r", "equals"]),
        ("Variables", ["voltage", "current", "resistance", "variable", "unit", "measure"]),
        ("Applications", ["application", "used in", "engineer", "practice", "use", "design", "apply"]),
        ("Types", ["type", "types", "kinds", "classification", "class of"]),
        ("Relationships", ["relationship", "relates", "between", "interact", "depend", "correlat"]),
        ("Importance", ["important", "significant", "key reason", "why it matters", "value"]),
    ]

    # Avoid document-outline terms as categories
    outline_terms = {"introduction", "overview", "summary", "conclusion", "additional", "notes"}

    selected: list[tuple[str, float]] = []
    for name, keywords in detectors:
        score = 0.0
        for kw in keywords:
            if kw in lower:
                score += 1.0
        # boost score if chapter title or objective contains category hints
        if name.lower() in (understanding.chapter_title or "").lower() or name.lower() in (understanding.learning_objective or "").lower():
            score += 0.5
        if score > 0:
            if name.lower() not in outline_terms:
                selected.append((name, score))

    # Always try to include a 'Concept' or 'Core Concept' node if nothing else
    if not selected:
        selected.append(("Core Concept", 1.0))

    # Sort categories by score descending
    selected.sort(key=lambda x: x[1], reverse=True)

    # Extract candidate sentences for building learning points
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]

    sections: list[EducationalSection] = []
    used_points = set()

    for idx, (category, score) in enumerate(selected):
        importance = round(max(0.6, min(0.98, 0.9 * (score + 0.2))), 2)

        # build learning points by selecting sentences that contain category keywords
        points: list[str] = []
        cat_kw = [kw for name, kws in detectors for (n, k) in [(name, kws)] if name == category for kw in (k if isinstance(k, list) else [k])]
        # find sentences that contain any keyword or contain chapter key terms
        for s in sentences:
            low = s.lower()
            matched = any(kw in low for kw in cat_kw)
            # also match if the sentence mentions the chapter title or typical concept words
            if not matched and any(token in low for token in (understanding.chapter_title or "").lower().split()[:3]):
                matched = True
            if matched:
                short = _extract_candidate_point(s)
                if short and short not in used_points:
                    points.append(short)
                    used_points.add(short)
            if len(points) >= 5:
                break

        # if not enough points found, try to extract noun-phrase style candidates
        if len(points) < 2:
            for s in sentences:
                nouns = re.findall(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*)\b", s)
                for n in nouns:
                    nshort = n.strip()
                    if nshort and nshort not in used_points:
                        points.append(nshort)
                        used_points.add(nshort)
                        if len(points) >= 5:
                            break
                if len(points) >= 5:
                    break

        # last resort: fallback learning points for known topics
        if not points:
            points = _fallback_learning_points(category.lower(), understanding)

        learning_points = [LearningPoint(text=_clean_text(p), type=_infer_learning_point_type(p, None)) for p in points[:5]]

        sections.append(
            EducationalSection(
                title=category,
                type=_infer_section_type(category, None),
                pedagogical_role=_infer_pedagogical_role(category, None),
                importance=importance,
                learning_points=learning_points,
            )
        )

    return sections


def _extract_candidate_point(sentence: str) -> str:
    """Extract a concise candidate learning point from a sentence."""
    s = sentence.strip()
    # remove leading discourse words
    s = re.sub(r"^(in summary[:\-\s]*|therefore[:,\-\s]*|thus[:,\-\s]*|note[:,\-\s]*|example[:,\-\s]*)", "", s, flags=re.I)
    # shorten long sentences to first clause
    parts = re.split(r"[,;:\-]", s)
    candidate = parts[0].strip()
    # truncate to 140 chars
    if len(candidate) > 140:
        candidate = candidate[:137].rsplit(" ", 1)[0] + "..."
    return candidate


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


def _normalize_structure(payload: dict[str, Any], understanding: EducationalUnderstanding) -> EducationalKnowledgeStructure:
    sections = []
    for section_payload in payload.get("sections", []) or []:
        if not isinstance(section_payload, dict):
            continue
        title = _clean_text(section_payload.get("title"))
        if not title:
            continue
        section_type = _infer_section_type(title, section_payload.get("type"))
        pedagogical_role = _infer_pedagogical_role(title, section_payload.get("pedagogical_role"))
        importance = _normalize_importance(section_payload.get("importance"))
        raw_points = section_payload.get("learning_points") or section_payload.get("items") or []
        learning_points = []
        for point in raw_points:
            if isinstance(point, dict):
                text = _clean_text(point.get("text"))
                point_type = _infer_learning_point_type(text, point.get("type"))
            else:
                text = _clean_text(point)
                point_type = _infer_learning_point_type(text, None)
            if text:
                learning_points.append(LearningPoint(text=text, type=point_type))
        if not learning_points:
            fallback_points = _fallback_learning_points(title, understanding)
            learning_points = [LearningPoint(text=point, type=_infer_learning_point_type(point, None)) for point in fallback_points]
        sections.append(
            EducationalSection(
                title=title,
                type=section_type,
                pedagogical_role=pedagogical_role,
                importance=importance,
                learning_points=learning_points[:5],
            )
        )

    if not sections:
        sections = _fallback_sections(understanding)

    return EducationalKnowledgeStructure(
        chapter_title=_clean_text(payload.get("chapter_title")) or understanding.chapter_title,
        learning_objective=_clean_text(payload.get("learning_objective")) or understanding.learning_objective,
        sections=sections,
    )


def _fallback_structure(understanding: EducationalUnderstanding) -> EducationalKnowledgeStructure:
    return EducationalKnowledgeStructure(
        chapter_title=understanding.chapter_title,
        learning_objective=understanding.learning_objective,
        sections=_fallback_sections(understanding),
    )


def _fallback_sections(understanding: EducationalUnderstanding) -> list[EducationalSection]:
    sections = []
    for index, title in enumerate(understanding.major_sections):
        importance = max(0.85, 0.95 - (index * 0.03))
        sections.append(
            EducationalSection(
                title=title,
                type=_infer_section_type(title, None),
                pedagogical_role=_infer_pedagogical_role(title, None),
                importance=round(importance, 2),
                learning_points=[
                    LearningPoint(text=point, type=_infer_learning_point_type(point, None))
                    for point in _fallback_learning_points(title, understanding)
                ],
            )
        )
    return sections


def _fallback_learning_points(title: str, understanding: EducationalUnderstanding) -> list[str]:
    lower = title.lower()
    chapter_lower = understanding.chapter_title.lower()

    if "photosynthesis" in chapter_lower:
        mapping = {
            "introduction": ["Definition", "Purpose"],
            "requirements": ["Sunlight", "Water", "Carbon Dioxide"],
            "process": ["Light Absorption", "Glucose Formation", "Oxygen Release"],
            "products": ["Glucose", "Oxygen"],
            "importance": ["Food Production", "Oxygen Supply"],
        }
        return mapping.get(lower, ["Core Idea", "Main Process"])

    if "ohm" in chapter_lower or "law" in chapter_lower:
        mapping = {
            "introduction": ["Definition", "Purpose"],
            "formula": ["V = IR", "Variables"],
            "voltage": ["Electrical Potential", "Unit"],
            "current": ["Charge Flow", "Unit"],
            "resistance": ["Opposition to Current", "Unit"],
            "applications": ["Circuit Analysis", "Electrical Design"],
        }
        return mapping.get(lower, ["Core Relationship", "Practical Use"])

    if "water" in chapter_lower and "cycle" in chapter_lower:
        mapping = {
            "evaporation": ["Heat Energy", "Surface Water"],
            "condensation": ["Cooling", "Cloud Formation"],
            "precipitation": ["Rainfall", "Snowfall"],
            "collection": ["Groundwater", "Lakes and Oceans"],
        }
        return mapping.get(lower, ["Water Movement", "Environmental Role"])

    if "cell" in chapter_lower and "division" in chapter_lower:
        mapping = {
            "introduction": ["Purpose", "Overview"],
            "mitosis": ["Chromosome Replication", "Daughter Cells"],
            "meiosis": ["Genetic Variation", "Gamete Formation"],
            "importance": ["Growth", "Repair"],
        }
        return mapping.get(lower, ["Cell Reproduction", "Biological Significance"])

    if "network" in chapter_lower:
        mapping = {
            "introduction": ["Purpose", "Basic Communication"],
            "network types": ["LAN", "WAN"],
            "transmission": ["Signal Transfer", "Media"],
            "protocols": ["Communication Rules", "Data Exchange"],
            "services": ["Sharing Resources", "Internet Access"],
        }
        return mapping.get(lower, ["Connectivity", "Data Transfer"])

    if "operating" in chapter_lower and "system" in chapter_lower:
        mapping = {
            "process management": ["Scheduling", "Execution"],
            "memory management": ["Allocation", "Storage"],
            "file systems": ["Organization", "Access"],
            "user interface": ["Interaction", "Control"],
        }
        return mapping.get(lower, ["System Control", "Resource Management"])

    if "normalization" in chapter_lower or "database" in chapter_lower:
        mapping = {
            "introduction": ["Data Organization", "Redundancy Reduction"],
            "keys": ["Primary Keys", "Foreign Keys"],
            "normal forms": ["First Normal Form", "Second Normal Form"],
            "anomalies": ["Update Anomaly", "Delete Anomaly"],
            "design principles": ["Consistency", "Integrity"],
        }
        return mapping.get(lower, ["Database Structure", "Data Integrity"])

    return ["Core Idea", "Supporting Principle"]


def _infer_section_type(title: str, provided: Any) -> str:
    text = _clean_text(provided or title).lower()
    if any(token in text for token in ["definition", "purpose", "intro"]):
        return "Definition"
    if any(token in text for token in ["formula", "equation", "law"]):
        return "Formula"
    if any(token in text for token in ["process", "mechanism", "step"]):
        return "Process"
    if any(token in text for token in ["requirement", "input"]):
        return "Core Concept"
    if any(token in text for token in ["product", "output", "result"]):
        return "Outcome"
    if any(token in text for token in ["application", "applications", "use", "uses"]):
        return "Application"
    if any(token in text for token in ["summary", "revision"]):
        return "Summary"
    if any(token in text for token in ["comparison", "classification", "type", "types"]):
        return "Classification"
    return "Core Concept"


def _infer_pedagogical_role(title: str, provided: Any) -> str:
    text = _clean_text(provided or title).lower()
    if any(token in text for token in ["definition", "intro", "introduction"]):
        return "Definition"
    if any(token in text for token in ["requirement", "prereq", "prerequisite"]):
        return "Prerequisites"
    if any(token in text for token in ["process", "mechanism", "step"]):
        return "Process"
    if any(token in text for token in ["product", "output", "result", "outcome"]):
        return "Outcome"
    if any(token in text for token in ["application", "applications", "use", "uses"]):
        return "Applications"
    if any(token in text for token in ["summary", "revision"]):
        return "Summary"
    return "Core Learning"


def _infer_learning_point_type(text: str, provided: Any) -> str:
    value = _clean_text(provided or text).lower()
    if any(token in value for token in ["requirement", "input", "water", "sunlight", "carbon"]):
        return "Requirement"
    if any(token in value for token in ["formula", "equation", "voltage", "current", "resistance", "v =", "i", "r"]):
        return "Formula Component"
    if any(token in value for token in ["process", "absorption", "formation", "release", "step"]):
        return "Process Step"
    if any(token in value for token in ["product", "output", "glucose", "oxygen"]):
        return "Product"
    if any(token in value for token in ["definition", "purpose", "overview"]):
        return "Definition"
    if any(token in value for token in ["application", "use", "design", "analysis"]):
        return "Application"
    if any(token in value for token in ["advantage", "benefit"]):
        return "Advantage"
    if any(token in value for token in ["disadvantage", "limitation"]):
        return "Disadvantage"
    if any(token in value for token in ["classification", "type", "kind", "category"]):
        return "Classification"
    if any(token in value for token in ["principle", "rule", "mechanism", "relationship"]):
        return "Principle"
    return "Characteristic"


def _normalize_importance(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except Exception:
        return 0.9


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)
