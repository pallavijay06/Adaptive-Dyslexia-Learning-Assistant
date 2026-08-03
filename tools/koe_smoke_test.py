from services.knowledge_organization_engine import organize_knowledge
from services.educational_understanding_engine import EducationalUnderstanding

text = "Ohm's Law relates voltage, current, and resistance in an electrical circuit. Voltage drives current. Resistance opposes current. The formula is V = I * R. Applications include circuit analysis and electrical design."
under = EducationalUnderstanding(chapter_title="Ohm's Law", subject="Physics", domain="Science", topic_complexity="Hard", learning_objective="Understand the relationship between voltage, current, and resistance.", major_sections=["Introduction","Relationship","Applications"])
ks = organize_knowledge(under, text)
print(ks.to_dict())
