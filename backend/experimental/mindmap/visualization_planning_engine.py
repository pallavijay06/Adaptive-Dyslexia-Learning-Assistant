"""Visualization planning orchestrator for renderer-ready mind map model generation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from services.educational_validation_engine import ValidatedEducationalKnowledgeStructure
from services.visualization_planning_stages import (
    EducationalBranchRenamingEngine,
    EducationalBranchSelectionEngine,
    EducationalSequencingEngine,
    HierarchyOptimizationEngine,
    LayoutPlanningEngine,
    SemanticChildAssignmentEngine,
    FinalLayoutBranch,
    SelectedEducationalStructure,
)


@dataclass(frozen=True)
class VisualizationNode:
    id: str
    label: str
    node_type: str
    priority: str
    visual_style: dict[str, Any]
    display_label: str
    branch_order: int | None = None
    parent_id: str | None = None


@dataclass(frozen=True)
class VisualizationEdge:
    source: str
    target: str
    edge_type: str = "branch"


@dataclass(frozen=True)
class MindMapLayoutModel:
    center_node: VisualizationNode
    branch_nodes: list[VisualizationNode] = field(default_factory=list)
    child_nodes: list[VisualizationNode] = field(default_factory=list)
    edges: list[VisualizationEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "center_node": {
                "id": self.center_node.id,
                "label": self.center_node.label,
                "node_type": self.center_node.node_type,
                "priority": self.center_node.priority,
                "visual_style": self.center_node.visual_style,
                "display_label": self.center_node.display_label,
            },
            "branch_nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "node_type": node.node_type,
                    "priority": node.priority,
                    "visual_style": node.visual_style,
                    "display_label": node.display_label,
                    "branch_order": node.branch_order,
                    "parent_id": node.parent_id,
                }
                for node in self.branch_nodes
            ],
            "child_nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "node_type": node.node_type,
                    "priority": node.priority,
                    "visual_style": node.visual_style,
                    "display_label": node.display_label,
                    "branch_order": node.branch_order,
                    "parent_id": node.parent_id,
                }
                for node in self.child_nodes
            ],
            "edges": [
                {"source": edge.source, "target": edge.target, "edge_type": edge.edge_type}
                for edge in self.edges
            ],
        }


class VisualizationPlanningEngine:
    """Orchestrates the deterministic multi-stage visualization planning pipeline."""

    def __init__(self) -> None:
        self.last_plan_report: dict[str, Any] = {}
        self.selection_engine = EducationalBranchSelectionEngine()
        self.rename_engine = EducationalBranchRenamingEngine()
        self.hierarchy_engine = HierarchyOptimizationEngine()
        self.child_assignment_engine = SemanticChildAssignmentEngine()
        self.sequence_engine = EducationalSequencingEngine()
        self.layout_engine = LayoutPlanningEngine()

    def plan(self, structure: ValidatedEducationalKnowledgeStructure) -> MindMapLayoutModel:
        selected = self.selection_engine.plan(structure)
        renamed = self.rename_engine.plan(selected)
        optimized = self.hierarchy_engine.plan(renamed)
        reassigned = self.child_assignment_engine.plan(optimized)
        sequenced = self.sequence_engine.plan(reassigned)
        final_branches = self.layout_engine.plan(sequenced)

        self.last_plan_report = {
            "stage_1_selected_branches": self.selection_engine.selected_titles,
            "stage_2_renamed_branches": self.rename_engine.renamed_titles,
            "stage_3_hierarchy_changes": self.hierarchy_engine.changes,
            "stage_4_reassignments": [
                {"concept": concept, "from": source, "to": target}
                for concept, source, target in self.child_assignment_engine.reassignments
            ],
            "stage_5_ordered_branches": [branch.title for branch in sequenced.branches],
        }

        return self._build_layout(structure.chapter_title, final_branches)

    def _build_layout(self, chapter_title: str, branches: list[FinalLayoutBranch]) -> MindMapLayoutModel:
        center_label = _safe_title(chapter_title)
        center_node = VisualizationNode(
            id="center",
            label=center_label,
            node_type="center",
            priority="highest",
            visual_style={"color": "#4C78A8", "shape": "circle", "font_weight": "bold"},
            display_label=center_label,
        )

        branch_nodes: list[VisualizationNode] = []
        child_nodes: list[VisualizationNode] = []
        edges: list[VisualizationEdge] = []

        for branch in branches:
            branch_id = branch.id
            branch_node = VisualizationNode(
                id=branch_id,
                label=_safe_title(branch.title),
                node_type="branch",
                priority=self._branch_priority(branch.importance),
                visual_style=self._style_for_branch(branch),
                display_label=_safe_title(branch.title),
                branch_order=branch.branch_order,
                parent_id=center_node.id,
            )
            branch_nodes.append(branch_node)
            edges.append(VisualizationEdge(source=center_node.id, target=branch_id, edge_type="branch"))

            for child_index, point in enumerate(branch.learning_points):
                child_id = f"{branch_id}-child-{child_index}"
                child_node = VisualizationNode(
                    id=child_id,
                    label=_safe_title(point["text"]),
                    node_type="child",
                    priority=self._child_priority(point, branch),
                    visual_style=self._style_for_child(point, branch),
                    display_label=_safe_title(point["text"]),
                    branch_order=branch.branch_order,
                    parent_id=branch_id,
                )
                child_nodes.append(child_node)
                edges.append(VisualizationEdge(source=branch_id, target=child_id, edge_type="child"))

        return MindMapLayoutModel(
            center_node=center_node,
            branch_nodes=branch_nodes,
            child_nodes=child_nodes,
            edges=edges,
        )

    def _branch_priority(self, importance: float) -> str:
        if importance >= 0.85:
            return "high"
        if importance >= 0.6:
            return "medium"
        return "low"

    def _child_priority(self, point: dict[str, Any], branch: FinalLayoutBranch) -> str:
        return "medium"

    def _style_for_branch(self, branch: FinalLayoutBranch) -> dict[str, Any]:
        role = _normalize_text(branch.pedagogical_role).lower()
        style = {"shape": "rounded", "font_weight": "bold"}
        if "definition" in role:
            style["color"] = "#4C78A8"
        elif "process" in role:
            style["color"] = "#F58518"
        elif "application" in role:
            style["color"] = "#72B7B2"
        elif "requirement" in role or "input" in role or "prerequisite" in role:
            style["color"] = "#B279A2"
        elif "advantage" in role or "benefit" in role:
            style["color"] = "#54A24B"
        else:
            style["color"] = "#79706E"
        return style

    def _style_for_child(self, point: dict[str, Any], branch: FinalLayoutBranch) -> dict[str, Any]:
        return {"shape": "ellipse", "font_weight": "normal", "color": "#9D755D"}


def _safe_title(value: str) -> str:
    text = _normalize_text(value)
    return text if text else "Untitled"


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return re.sub(r"\s+", " ", text)
