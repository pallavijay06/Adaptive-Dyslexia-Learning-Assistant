from services.educational_validation_engine import EducationalValidationEngine
from services.knowledge_organization_engine import EducationalKnowledgeStructure, EducationalSection, LearningPoint


def test_validation_engine_removes_invalid_content_and_reports_warnings():
    structure = EducationalKnowledgeStructure(
        chapter_title="General",
        learning_objective="   ",
        sections=[
            EducationalSection(
                title="Requirements",
                type="Core Concept",
                pedagogical_role="Core Concept",
                importance=1.5,
                learning_points=[
                    LearningPoint(text="Water", type="Requirement"),
                    LearningPoint(text="Water", type="Requirement"),
                    LearningPoint(text="   ", type="Requirement"),
                    LearningPoint(text="Click below", type="Requirement"),
                ],
            ),
            EducationalSection(
                title="Requirements",
                type="Core Concept",
                pedagogical_role="Core Concept",
                importance=0.2,
                learning_points=[LearningPoint(text="Carbon Dioxide", type="Requirement")],
            ),
            EducationalSection(
                title="Miscellaneous",
                type="Core Concept",
                pedagogical_role="Random",
                importance=-0.4,
                learning_points=[LearningPoint(text="", type="Requirement")],
            ),
        ],
    )

    validated = EducationalValidationEngine().validate(structure)

    assert validated.chapter_title == "Untitled Chapter"
    assert validated.learning_objective == "Understand the main ideas in this chapter."
    assert len(validated.sections) == 1
    assert validated.sections[0].title == "Requirements"
    assert validated.sections[0].learning_points[0].text == "Water"
    assert validated.report.valid is False
    assert validated.report.errors
    assert validated.report.warnings


def test_validation_engine_rejects_instructional_text():
    structure = EducationalKnowledgeStructure(
        chapter_title="Photosynthesis",
        learning_objective="Understand the process.",
        sections=[
            EducationalSection(
                title="Process",
                type="Process",
                pedagogical_role="Process",
                importance=0.9,
                learning_points=[
                    LearningPoint(text="Let's learn how plants work", type="Process Step"),
                    LearningPoint(text="Light Absorption", type="Process Step"),
                ],
            )
        ],
    )

    validated = EducationalValidationEngine().validate(structure)

    assert validated.sections[0].learning_points[0].text == "Light Absorption"
    assert validated.report.warnings
