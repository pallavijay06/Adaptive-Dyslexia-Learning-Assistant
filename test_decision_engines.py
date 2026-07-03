from services.understanding_decision_engine import get_understanding_decision
from services.content_personalization_engine import get_content_personalization_decision
from services.learning_strategy_engine import get_learning_strategy_decision

USER_ID = 41

print("="*60)
print("UNDERSTANDING DECISION")
print("="*60)

understanding = get_understanding_decision(USER_ID)
print(understanding)

print()

print("="*60)
print("LEARNING STRATEGY")
print("="*60)

strategy = get_learning_strategy_decision(USER_ID)
print(strategy)

print()

print("="*60)
print("CONTENT PERSONALIZATION")
print("="*60)

document_concepts = [
    "Voltage",
    "Current",
    "Resistance",
    "Power"
]

content = get_content_personalization_decision(
    USER_ID,
    document_concepts
)

print(content)