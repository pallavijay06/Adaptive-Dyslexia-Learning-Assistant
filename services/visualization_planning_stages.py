"""Deterministic multi-stage educational visualization planning pipeline.

This module contains discrete planning stages for selecting, renaming,
optimizing, assigning, sequencing, and laying out educational mind map branches.
Each stage is intentionally single-responsibility and the pipeline is
orchestrated by the VisualizationPlanningEngine.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from services.educational_validation_engine import ValidatedEducationalKnowledgeStructure
from services.llm_router import generate_content

logger = logging.getLogger(__name__)


@dataclass
class SelectedBranch:
    id: str
    title: str
    type: str
    pedagogical_role: str
    importance: float
    source_section: str
    source_index: int
    learning_points: list[dict[str, Any]]


@dataclass(frozen=True)
class SelectedEducationalStructure:
    chapter_title: str
    learning_objective: str
    branches: list[SelectedBranch]


@dataclass(frozen=True)
class RenamedBranch:
    id: str
    title: str
    type: str
    pedagogical_role: str
    importance: float
    source_section: str
    source_index: int
    learning_points: list[dict[str, Any]]


@dataclass(frozen=True)
class OptimizedBranch:
    id: str
    title: str
    type: str
    pedagogical_role: str
    importance: float
    source_section: str
    source_index: int
    learning_points: list[dict[str, Any]]


@dataclass(frozen=True)
class SequencedBranch:
    id: str
    title: str
    type: str
    pedagogical_role: str
    importance: float
    source_section: str
    source_index: int
    learning_points: list[dict[str, Any]]


@dataclass(frozen=True)
class FinalLayoutBranch:
    id: str
    title: str
    type: str
    pedagogical_role: str
    importance: float
    source_section: str
    source_index: int
    learning_points: list[dict[str, Any]]
    branch_order: int


class EducationalBranchSelectionEngine:
    GENERIC_REJECT_TITLES = {
        "summary",
        "revision",
        "miscellaneous",
        "misc",
        "notes",
        "note",
        "overview",
        "introduction",
    }

    PRESERVE_TYPES = {
        "Formula",
        "Definition",
        "Process",
        "Core Concept",
    }

    def __init__(self) -> None:
        self.selected_titles: list[str] = []

    def plan(self, structure: ValidatedEducationalKnowledgeStructure) -> SelectedEducationalStructure:
        branches: list[SelectedBranch] = []
        for index, section in enumerate(structure.sections or []):
            title = _normalize_text(section.title)
            if not title:
                continue

            if title.lower() in self.GENERIC_REJECT_TITLES:
                if section.type not in self.PRESERVE_TYPES:
                    continue
                if len(section.learning_points or []) < 2:
                    continue

            if self._is_tiny_branch(section):
                if section.type not in self.PRESERVE_TYPES:
                    continue

            canonical_title = _canonical_branch_title(section)
            if not canonical_title:
                continue

            if self._is_repeated_branch(section, branches):
                continue

            if self._is_summary_or_revision(section):
                continue

            branches.append(SelectedBranch(
                id=f"branch-{index}",
                title=canonical_title,
                type=section.type,
                pedagogical_role=section.pedagogical_role,
                importance=max(0.0, min(1.0, float(section.importance or 0.0))),
                source_section=title,
                source_index=index,
                learning_points=[
                    {
                        "text": _normalize_text(point.text),
                        "type": _normalize_text(point.type) or "Concept",
                    }
                    for point in section.learning_points or []
                    if _normalize_text(point.text)
                ],
            ))

        if not branches:
            branches = self._fallback_to_everything(structure)

        self.selected_titles = [branch.title for branch in branches]
        return SelectedEducationalStructure(
            chapter_title=_normalize_text(structure.chapter_title),
            learning_objective=_normalize_text(structure.learning_objective),
            branches=branches,
        )

    def _is_tiny_branch(self, section: Any) -> bool:
        return len(section.learning_points or []) <= 1 and section.importance < 0.65

    def _is_repeated_branch(self, section: Any, existing: list[SelectedBranch]) -> bool:
        normalized = _normalize_text(section.title).lower()
        for branch in existing:
            if branch.title.lower() == normalized:
                return True
        return False

    def _is_summary_or_revision(self, section: Any) -> bool:
        normalized = _normalize_text(section.title).lower()
        return normalized in {"summary", "revision", "conclusion", "overview"}

    def _fallback_to_everything(self, structure: ValidatedEducationalKnowledgeStructure) -> list[SelectedBranch]:
        return [
            SelectedBranch(
                id=f"branch-{index}",
                title=_normalize_text(section.title) or f"Branch {index + 1}",
                type=section.type,
                pedagogical_role=section.pedagogical_role,
                importance=max(0.0, min(1.0, float(section.importance or 0.0))),
                source_section=_normalize_text(section.title),
                source_index=index,
                learning_points=[
                    {
                        "text": _normalize_text(point.text),
                        "type": _normalize_text(point.type) or "Concept",
                    }
                    for point in section.learning_points or []
                    if _normalize_text(point.text)
                ],
            )
            for index, section in enumerate(structure.sections or [])
        ]


class EducationalBranchRenamingEngine:
    PROMPT_TEMPLATE = (
        "You are an experienced educational content designer. "
        "A teacher must assign a concise textbook-quality branch title to a learning section. "
        "Use the learning objective, section title, learning points, and pedagogical role. "
        "Return only the branch title as plain text."
    )

    def __init__(self) -> None:
        self.renamed_titles: list[str] = []

    def plan(self, selected: SelectedEducationalStructure) -> SelectedEducationalStructure:
        renamed_branches: list[SelectedBranch] = []
        for branch in selected.branches:
            title = self._rename_branch(selected.learning_objective, branch)
            renamed_branches.append(SelectedBranch(
                id=branch.id,
                title=title,
                type=branch.type,
                pedagogical_role=branch.pedagogical_role,
                importance=branch.importance,
                source_section=branch.source_section,
                source_index=branch.source_index,
                learning_points=branch.learning_points,
            ))
        self.renamed_titles = [branch.title for branch in renamed_branches]
        return SelectedEducationalStructure(
            chapter_title=selected.chapter_title,
            learning_objective=selected.learning_objective,
            branches=renamed_branches,
        )

    def _rename_branch(self, learning_objective: str, branch: SelectedBranch) -> str:
        canonical = _canonical_branch_title_from_payload(branch.title, branch.pedagogical_role, branch.type)
        if canonical:
            return canonical

        prompt = (
            f"Learning objective: {learning_objective}\n"
            f"Section title: {branch.title}\n"
            f"Pedagogical role: {branch.pedagogical_role}\n"
            f"Learning points:\n"
        )
        for point in branch.learning_points:
            prompt += f"- {point['text']} ({point['type']})\n"
        prompt += (
            "\nProvide one concise textbook-quality branch title. "
            "Do not include bullets, punctuation, or explanation."
        )

        try:
            response = generate_content(prompt, max_tokens=80)
            cleaned = _normalize_text(response)
            if not cleaned:
                raise ValueError("Empty branch title from LLM")
            return cleaned
        except Exception:
            return self._fallback_title(branch)

    def _fallback_title(self, branch: SelectedBranch) -> str:
        title = _normalize_text(branch.title)
        canonical = _canonical_branch_title_from_payload(title, branch.pedagogical_role, branch.type)
        if canonical:
            return canonical
        return title


class HierarchyOptimizationEngine:
    def __init__(self) -> None:
        self.changes: list[str] = []

    def plan(self, selected: SelectedEducationalStructure) -> SelectedEducationalStructure:
        branches = [SelectedBranch(**{**branch.__dict__}) for branch in selected.branches]
        branches = self._merge_similar_branches(branches)
        branches = self._merge_weak_singleton_branches(branches)
        branches = self._split_broad_branches(branches)
        branches = [branch for branch in branches if branch.learning_points]
        return SelectedEducationalStructure(
            chapter_title=selected.chapter_title,
            learning_objective=selected.learning_objective,
            branches=branches,
        )

    def _merge_similar_branches(self, branches: list[SelectedBranch]) -> list[SelectedBranch]:
        merged: list[SelectedBranch] = []
        while branches:
            base = branches.pop(0)
            group = [base]
            i = 0
            while i < len(branches):
                if _educational_overlap(base, branches[i]) >= 0.5:
                    group.append(branches.pop(i))
                else:
                    i += 1
            if len(group) == 1:
                merged.append(base)
            else:
                merged_branch = self._merge_branch_group(group)
                merged.append(merged_branch)
        return merged

    def _merge_branch_group(self, branches: list[SelectedBranch]) -> SelectedBranch:
        branches = sorted(branches, key=lambda branch: (-branch.importance, branch.title))
        representative = branches[0]
        merged_points = []
        seen: set[str] = set()
        for branch in branches:
            for point in branch.learning_points:
                normalized = point["text"].lower()
                if normalized not in seen:
                    merged_points.append(point)
                    seen.add(normalized)
        merged = SelectedBranch(
            id=representative.id,
            title=representative.title,
            type=representative.type,
            pedagogical_role=representative.pedagogical_role,
            importance=max(branch.importance for branch in branches),
            source_section=representative.source_section,
            source_index=representative.source_index,
            learning_points=merged_points,
        )
        self.changes.append(
            f"Merged branches {[branch.title for branch in branches]} into {merged.title}"
        )
        return merged

    def _split_broad_branches(self, branches: list[SelectedBranch]) -> list[SelectedBranch]:
        result: list[SelectedBranch] = []
        for branch in branches:
            if len(branch.learning_points) >= 5 and _contains_multiple_ideas(branch.learning_points):
                groups = _split_learning_points(branch.learning_points)
                if len(groups) > 1:
                    for group_index, group in enumerate(groups):
                        new_title = f"{branch.title} ({group_index + 1})"
                        self.changes.append(
                            f"Split branch {branch.title} into {len(groups)} branches"
                        )
                        result.append(SelectedBranch(
                            id=f"{branch.id}-{group_index}",
                            title=new_title,
                            type=branch.type,
                            pedagogical_role=branch.pedagogical_role,
                            importance=branch.importance,
                            source_section=branch.source_section,
                            source_index=branch.source_index,
                            learning_points=group,
                        ))
                    continue
            result.append(branch)
        return result

    def _merge_weak_singleton_branches(self, branches: list[SelectedBranch]) -> list[SelectedBranch]:
        result: list[SelectedBranch] = []
        for branch in branches:
            if len(branch.learning_points) == 1 and branch.importance < 0.55:
                best_neighbor = self._best_neighbor_for_merge(branch, branches)
                if best_neighbor and best_neighbor.title != branch.title:
                    self.changes.append(
                        f"Merged weak singleton branch '{branch.title}' into '{best_neighbor.title}'"
                    )
                    best_neighbor.learning_points.append(branch.learning_points[0])
                    best_neighbor.importance = max(best_neighbor.importance, branch.importance)
                    continue
            result.append(branch)
        return result

    def _best_neighbor_for_merge(self, branch: SelectedBranch, branches: list[SelectedBranch]) -> SelectedBranch | None:
        candidates = [candidate for candidate in branches if candidate.title != branch.title]
        if not candidates:
            return None
        best = max(candidates, key=lambda candidate: _semantic_relevance_score(branch.learning_points[0], candidate))
        return best


class SemanticChildAssignmentEngine:
    def __init__(self) -> None:
        self.reassignments: list[tuple[str, str, str]] = []

    def plan(self, structure: SelectedEducationalStructure) -> SelectedEducationalStructure:
        branches = [SelectedBranch(**{**branch.__dict__}) for branch in structure.branches]
        for source_branch in branches:
            for point in source_branch.learning_points[:]:
                target = self._best_branch_for_learning_point(point, branches)
                if target and target.title != source_branch.title:
                    self.reassignments.append((point["text"], source_branch.title, target.title))
                    source_branch.learning_points = [p for p in source_branch.learning_points if p is not point]
                    target.learning_points.append(point)
        final_branches = [branch for branch in branches if branch.learning_points]
        return SelectedEducationalStructure(
            chapter_title=structure.chapter_title,
            learning_objective=structure.learning_objective,
            branches=final_branches,
        )

    def _best_branch_for_learning_point(self, point: dict[str, Any], branches: list[SelectedBranch]) -> SelectedBranch | None:
        best: SelectedBranch | None = None
        best_score = -1.0
        for branch in branches:
            score = _semantic_relevance_score(point, branch)
            if score > best_score:
                best_score = score
                best = branch
        return best


class EducationalSequencingEngine:
    ORDER = [
        "Definition",
        "Requirements",
        "Components",
        "Process",
        "Products",
        "Importance",
        "Examples",
        "Summary",
    ]

    ORDER_KEYWORDS = {
        "Definition": {"definition", "define", "meaning", "term"},
        "Requirements": {"requirements", "requirement", "prerequisite", "need", "input"},
        "Components": {"components", "parts", "structure", "elements", "characteristics"},
        "Process": {"process", "steps", "sequence", "flow", "mechanism", "cycle"},
        "Products": {"products", "product", "output", "outputs", "result", "results"},
        "Importance": {"importance", "significance", "value", "why it matters", "benefit", "application"},
        "Examples": {"example", "case", "illustration", "sample"},
        "Summary": {"summary", "conclusion", "recap", "review"},
    }

    def __init__(self) -> None:
        self.ordered_titles: list[str] = []

    def plan(self, structure: SelectedEducationalStructure) -> SelectedEducationalStructure:
        ordered = sorted(
            structure.branches,
            key=lambda branch: (self._order_index(branch.title), -branch.importance, branch.title.lower()),
        )
        self.ordered_titles = [branch.title for branch in ordered]
        return SelectedEducationalStructure(
            chapter_title=structure.chapter_title,
            learning_objective=structure.learning_objective,
            branches=ordered,
        )

    def _order_index(self, title: str) -> int:
        normalized = _normalize_text(title).lower()
        for index, name in enumerate(self.ORDER):
            keywords = self.ORDER_KEYWORDS.get(name, {name.lower()})
            if any(keyword in normalized for keyword in keywords):
                return index
        return len(self.ORDER)


class LayoutPlanningEngine:
    def plan(self, structure: SelectedEducationalStructure) -> list[FinalLayoutBranch]:
        final_branches: list[FinalLayoutBranch] = []
        for index, branch in enumerate(structure.branches):
            final_branches.append(FinalLayoutBranch(
                id=f"branch-{index}",
                title=branch.title,
                type=branch.type,
                pedagogical_role=branch.pedagogical_role,
                importance=branch.importance,
                source_section=branch.source_section,
                source_index=branch.source_index,
                learning_points=branch.learning_points,
                branch_order=index,
            ))
        return final_branches


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)


def _canonical_branch_title(section: Any) -> str:
    title = _normalize_text(section.title)
    pedagogical_role = _normalize_text(section.pedagogical_role).lower()
    section_type = _normalize_text(section.type).lower()
    combined = f"{title} {pedagogical_role} {section_type}".lower()
    return _canonical_branch_title_from_payload(title, pedagogical_role, section_type)


def _canonical_branch_title_from_payload(title: str, pedagogical_role: str, section_type: str) -> str | None:
    text = f"{_normalize_text(title)} {_normalize_text(pedagogical_role)} {_normalize_text(section_type)}".lower()

    label_map = {
        "definition": "Definition",
        "requirements": "Requirements",
        "requirement": "Requirements",
        "components": "Components",
        "component": "Components",
        "process": "Process",
        "product": "Products",
        "products": "Products",
        "output": "Products",
        "outputs": "Products",
        "importance": "Importance",
        "significance": "Importance",
        "applications": "Applications",
        "application": "Applications",
        "example": "Examples",
        "examples": "Examples",
        "summary": "Summary",
    }

    for keyword, label in label_map.items():
        if keyword in text:
            return label

    if any(token in text for token in {"parts", "elements", "structure", "ingredients", "characteristics"}):
        return "Components"
    if any(token in text for token in {"energy", "cycle", "mechanism", "steps", "sequence", "transformation"}):
        return "Process"
    if any(token in text for token in {"result", "outcome", "effect", "consequence"}):
        return "Products"
    if any(token in text for token in {"why", "benefit", "value", "purpose", "relevance"}):
        return "Importance"
    if any(token in text for token in {"case", "illustration", "sample", "example"}):
        return "Examples"
    return None


def _educational_overlap(left: SelectedBranch, right: SelectedBranch) -> float:
    left_points = {point["text"].lower() for point in left.learning_points}
    right_points = {point["text"].lower() for point in right.learning_points}
    if not left_points or not right_points:
        return 0.0
    shared = left_points & right_points
    return len(shared) / max(len(left_points), len(right_points))


def _contains_multiple_ideas(points: list[dict[str, Any]]) -> bool:
    normalized_texts = [point["text"].lower() for point in points]
    unique_terms = set(" ".join(normalized_texts).split())
    return len(unique_terms) > 12


def _split_learning_points(points: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    midpoint = max(1, len(points) // 2)
    return [points[:midpoint], points[midpoint:]]


def _is_branch_worthy_point(point: dict[str, Any]) -> bool:
    text = point["text"].lower()
    return any(keyword in text for keyword in ["process", "formula", "definition", "application", "requirement", "component", "importance"])


def _semantic_relevance_score(point: dict[str, Any], branch: SelectedBranch) -> float:
    score = 0.0
    text = point["text"].lower()
    title = branch.title.lower()
    if title in text or text in title:
        score += 0.6
    keywords = ["formula", "definition", "process", "application", "requirements", "components", "advantages", "importance"]
    if any(keyword in title for keyword in keywords):
        score += 0.3 if any(keyword_in_text(keyword, text) for keyword in keywords) else 0.0
    if branch.type == "Formula" and "formula" in text:
        score += 0.4
    if branch.type == "Definition" and "definition" in text:
        score += 0.4
    if branch.type == "Process" and any(step_word in text for step_word in ["step", "stage", "first", "then", "next", "finally"]):
        score += 0.4
    if branch.type == "Applications" and any(app_word in text for app_word in ["use", "used", "application", "practice", "deploy", "implement"]):
        score += 0.3
    return min(score, 1.0)


def keyword_in_text(keyword: str, text: str) -> bool:
    return keyword.lower() in text
