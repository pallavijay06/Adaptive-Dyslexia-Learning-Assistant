from services.educational_validation_engine import ValidationReport, ValidatedEducationalKnowledgeStructure
from services.knowledge_organization_engine import EducationalSection, LearningPoint
from services.visualization_planning_engine import VisualizationPlanningEngine


def test_plan_builds_renderer_ready_layout_model():
    validated = ValidatedEducationalKnowledgeStructure(
        chapter_title="Photosynthesis",
        learning_objective="Understand how plants make food.",
        sections=[
            EducationalSection(
                title="Requirements",
                type="Core Concept",
                pedagogical_role="Definition",
                importance=0.95,
                learning_points=[
                    LearningPoint(text="Water", type="Requirement"),
                    LearningPoint(text="Sunlight", type="Requirement"),
                ],
            ),
            EducationalSection(
                title="Process",
                type="Process",
                pedagogical_role="Process",
                importance=0.9,
                learning_points=[
                    LearningPoint(text="Light absorption", type="Process Step"),
                ],
            ),
        ],
        report=ValidationReport(valid=True),
    )

    layout = VisualizationPlanningEngine().plan(validated)

    assert layout.center_node.label == "Photosynthesis"
    assert len(layout.branch_nodes) == 2
    assert len(layout.child_nodes) == 3
    assert layout.branch_nodes[0].branch_order == 0
    assert layout.branch_nodes[1].branch_order == 1
    assert layout.center_node.priority == "highest"
    assert all(branch.priority == "high" for branch in layout.branch_nodes)
    assert all(child.priority == "medium" for child in layout.child_nodes)
    assert layout.branch_nodes[0].visual_style["color"] == "#4C78A8"
    assert layout.branch_nodes[1].visual_style["color"] == "#F58518"
    assert layout.edges
    assert layout.center_node.node_type == "center"
    assert layout.branch_nodes[0].node_type == "branch"
    assert layout.child_nodes[0].node_type == "child"


def test_planner_canonicalizes_sentence_like_sections_into_textbook_themes():
    validated = ValidatedEducationalKnowledgeStructure(
        chapter_title="Photosynthesis",
        learning_objective="Understand the process of photosynthesis.",
        sections=[
            EducationalSection(
                title="Plants use air",
                type="Core Concept",
                pedagogical_role="Requirement",
                importance=0.82,
                learning_points=[
                    LearningPoint(text="Carbon Dioxide", type="Requirement"),
                    LearningPoint(text="Sunlight", type="Requirement"),
                    LearningPoint(text="Water", type="Requirement"),
                ],
            ),
            EducationalSection(
                title="Plants make food",
                type="Core Concept",
                pedagogical_role="Outcome",
                importance=0.78,
                learning_points=[
                    LearningPoint(text="Sugar Formation", type="Product"),
                    LearningPoint(text="Oxygen Release", type="Product"),
                ],
            ),
            EducationalSection(
                title="This process depends on chlorophyll",
                type="Process",
                pedagogical_role="Process",
                importance=0.88,
                learning_points=[
                    LearningPoint(text="Chlorophyll", type="Process"),
                    LearningPoint(text="Energy Conversion", type="Process"),
                ],
            ),
        ],
        report=ValidationReport(valid=True),
    )

    layout = VisualizationPlanningEngine().plan(validated)

    branch_labels = {branch.label for branch in layout.branch_nodes}
    assert "Requirements" in branch_labels
    assert "Process" in branch_labels
    assert "Importance" in branch_labels or "Outputs" in branch_labels or "Products" in branch_labels
    assert len(layout.branch_nodes) <= 4
    assert len(layout.child_nodes) <= 8
