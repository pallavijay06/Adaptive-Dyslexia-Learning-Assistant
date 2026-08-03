"""Deterministic validation layer for the educational knowledge model.

This module validates and normalizes an EducationalKnowledgeStructure without
changing educational meaning or generating new content. It is intentionally a
pure Python quality gate for downstream visualization stages.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from services.knowledge_organization_engine import (
    EducationalKnowledgeStructure,
    EducationalSection,
    LearningPoint,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "warnings": self.warnings,
            "errors": self.errors,
        }


@dataclass(frozen=True)
class ValidatedEducationalKnowledgeStructure:
    chapter_title: str
    learning_objective: str
    sections: list[EducationalSection]
    report: ValidationReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapter_title": self.chapter_title,
            "learning_objective": self.learning_objective,
            "sections": [
                {
                    "title": section.title,
                    "type": section.type,
                    "pedagogical_role": section.pedagogical_role,
                    "importance": section.importance,
                    "learning_points": [
                        {"text": point.text, "type": point.type}
                        for point in section.learning_points
                    ],
                }
                for section in self.sections
            ],
            "report": self.report.to_dict(),
        }


class TitleValidator:
    """Validate chapter titles for educational meaningfulness."""

    GENERIC_TITLES = {"general", "document", "untitled", "topic", "default", "content", "lesson", "unknown"}

    def validate(self, title: str, report: ValidationReport) -> str:
        normalized = _normalize_text(title)
        if not normalized:
            report.errors.append("Chapter title is missing")
            return "Untitled Chapter"
        if normalized.lower() in self.GENERIC_TITLES:
            report.errors.append(f"Chapter title is too generic: {normalized}")
            return "Untitled Chapter"
        return normalized


class SectionValidator:
    """Validate that every section has meaningful educational metadata."""

    GENERIC_SECTION_TITLES = {"miscellaneous", "other", "general", "random", "extra", "unknown"}

    def validate(self, section: EducationalSection, report: ValidationReport) -> EducationalSection | None:
        title = _normalize_text(section.title)
        if not title:
            report.warnings.append("Removed empty section")
            return None
        if title.lower() in self.GENERIC_SECTION_TITLES:
            report.warnings.append(f"Removed generic section title: {title}")
            return None
        section_type = _normalize_text(section.type) or "Core Concept"
        pedagogical_role = _normalize_text(section.pedagogical_role) or "Core Learning"
        importance = _clamp_importance(section.importance)
        return EducationalSection(
            title=title,
            type=section_type,
            pedagogical_role=pedagogical_role,
            importance=importance,
            learning_points=list(section.learning_points or []),
        )


class LearningPointValidator:
    """Validate learning points and remove empty or non-educational content."""

    INSTRUCTIONAL_PHRASES = (
        "let's learn",
        "today we will",
        "this chapter explains",
        "in this lesson",
        "welcome",
        "now let's understand",
        "click below",
        "read carefully",
        "continue reading",
    )

    def validate(self, point: LearningPoint, report: ValidationReport) -> LearningPoint | None:
        text = _normalize_text(point.text)
        if not text:
            report.warnings.append("Removed empty learning point")
            return None
        if _looks_instructional(text):
            report.warnings.append(f"Removed instructional text: {text}")
            return None
        if _looks_like_ui_label(text):
            report.warnings.append(f"Removed UI-like learning point: {text}")
            return None
        if _is_punctuation_only(text) or _is_number_only(text) or _is_single_character(text):
            report.warnings.append(f"Removed invalid learning point: {text}")
            return None
        point_type = _normalize_text(point.type) or "Characteristic"
        return LearningPoint(text=text, type=point_type)


class DuplicateValidator:
    """Remove duplicate sections and duplicate learning points within a section."""

    def validate(self, sections: list[EducationalSection], report: ValidationReport) -> list[EducationalSection]:
        kept_sections: list[EducationalSection] = []
        seen_section_titles: set[str] = set()
        for section in sections:
            title_key = _normalize_text(section.title).lower()
            if not title_key:
                continue
            if title_key in seen_section_titles:
                report.warnings.append(f"Duplicate section removed: {section.title}")
                continue
            seen_section_titles.add(title_key)
            kept_learning_points: list[LearningPoint] = []
            seen_points: set[str] = set()
            for point in section.learning_points:
                point_text = _normalize_text(point.text).lower()
                if not point_text:
                    continue
                if point_text in seen_points:
                    report.warnings.append(f"Duplicate learning point removed: {point.text}")
                    continue
                seen_points.add(point_text)
                kept_learning_points.append(point)
            kept_sections.append(
                EducationalSection(
                    title=section.title,
                    type=section.type,
                    pedagogical_role=section.pedagogical_role,
                    importance=section.importance,
                    learning_points=kept_learning_points,
                )
            )
        return kept_sections


class ImportanceValidator:
    """Ensure importance values are numeric and within the required range."""

    def validate(self, section: EducationalSection, report: ValidationReport) -> EducationalSection:
        return EducationalSection(
            title=section.title,
            type=section.type,
            pedagogical_role=section.pedagogical_role,
            importance=_clamp_importance(section.importance),
            learning_points=section.learning_points,
        )


class PedagogicalRoleValidator:
    """Validate the educational role of sections."""

    VALID_ROLES = {
        "definition",
        "introduction",
        "core concept",
        "process",
        "relationship",
        "mechanism",
        "formula",
        "outcome",
        "application",
        "summary",
        "revision",
    }

    def validate(self, section: EducationalSection, report: ValidationReport) -> EducationalSection:
        role = _normalize_text(section.pedagogical_role).lower()
        if role not in self.VALID_ROLES:
            report.warnings.append(f"Replaced invalid pedagogical role: {section.pedagogical_role}")
            role = "core learning"
        return EducationalSection(
            title=section.title,
            type=section.type,
            pedagogical_role=role.title(),
            importance=section.importance,
            learning_points=section.learning_points,
        )


class NormalizationValidator:
    """Normalize educational text while preserving meaning."""

    def validate(self, section: EducationalSection, report: ValidationReport) -> EducationalSection:
        normalized_points = []
        for point in section.learning_points:
            text = _normalize_text(point.text)
            if text:
                normalized_points.append(LearningPoint(text=text, type=_normalize_text(point.type) or "Characteristic"))
        return EducationalSection(
            title=_normalize_text(section.title),
            type=_normalize_text(section.type) or "Core Concept",
            pedagogical_role=_normalize_text(section.pedagogical_role) or "Core Learning",
            importance=section.importance,
            learning_points=normalized_points,
        )


class ValidationReportBuilder:
    """Build the validation report from the validator outputs."""

    def build(self, report: ValidationReport) -> ValidationReport:
        return ValidationReport(valid=not report.errors, warnings=report.warnings, errors=report.errors)


class EducationalValidationEngine:
    """Deterministic validator for an EducationalKnowledgeStructure."""

    def __init__(self) -> None:
        self.title_validator = TitleValidator()
        self.section_validator = SectionValidator()
        self.learning_point_validator = LearningPointValidator()
        self.duplicate_validator = DuplicateValidator()
        self.importance_validator = ImportanceValidator()
        self.pedagogical_role_validator = PedagogicalRoleValidator()
        self.normalization_validator = NormalizationValidator()
        self.report_builder = ValidationReportBuilder()

    def validate(self, structure: EducationalKnowledgeStructure) -> ValidatedEducationalKnowledgeStructure:
        report = ValidationReport(valid=True, warnings=[], errors=[])
        chapter_title = self.title_validator.validate(structure.chapter_title, report)
        learning_objective = _normalize_text(structure.learning_objective) or "Understand the main ideas in this chapter."

        validated_sections: list[EducationalSection] = []
        for section in structure.sections or []:
            validated_section = self.section_validator.validate(section, report)
            if validated_section is None:
                continue
            validated_section = self.importance_validator.validate(validated_section, report)
            validated_section = self.pedagogical_role_validator.validate(validated_section, report)
            cleaned_points = []
            for point in validated_section.learning_points or []:
                cleaned_point = self.learning_point_validator.validate(point, report)
                if cleaned_point is not None:
                    cleaned_points.append(cleaned_point)
            validated_section = EducationalSection(
                title=validated_section.title,
                type=validated_section.type,
                pedagogical_role=validated_section.pedagogical_role,
                importance=validated_section.importance,
                learning_points=cleaned_points,
            )
            validated_sections.append(validated_section)

        validated_sections = self.duplicate_validator.validate(validated_sections, report)
        normalized_sections = []
        for section in validated_sections:
            normalized_sections.append(self.normalization_validator.validate(section, report))

        report = self.report_builder.build(report)
        return ValidatedEducationalKnowledgeStructure(
            chapter_title=chapter_title,
            learning_objective=learning_objective,
            sections=normalized_sections,
            report=report,
        )


def validate_educational_knowledge(structure: EducationalKnowledgeStructure) -> ValidatedEducationalKnowledgeStructure:
    return EducationalValidationEngine().validate(structure)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\t\n\r]+", " ", text)
    return text.strip().rstrip(".,;:!?")


def _clamp_importance(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 2)
    except Exception:
        return 0.9


def _looks_instructional(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in LearningPointValidator.INSTRUCTIONAL_PHRASES)


def _looks_like_ui_label(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in ["button", "click", "menu", "tab", "next", "back", "home", "settings", "submit"])


def _is_punctuation_only(text: str) -> bool:
    return bool(re.fullmatch(r"[^\w]+", text))


def _is_number_only(text: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)?", text))


def _is_single_character(text: str) -> bool:
    return len(text) <= 1
