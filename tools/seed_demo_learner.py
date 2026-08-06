"""Seed a deterministic demo learner account and verify backend adaptive recommendation."""

import sys
from pathlib import Path

# Ensure the repository root is on sys.path when running this script directly.
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from flask import Flask

from services.auth_service import hash_password, normalize_email
from database.db import (
    init_db,
    get_user,
    save_user,
    save_learner_profile,
    save_adaptive_preferences,
    save_learning_mode_session,
    save_learning_history,
)
import sqlite3
from database.db import DATABASE_PATH
from services.master_decision_engine import get_adaptive_learning_plan
from services.recommendation_engine import RecommendationEngine
from backend.adaptive_routes import adaptive_bp


DEMO_EMAIL = "demo.learner@example.com"
DEMO_PASSWORD = "DemoLearner123!"


def seed_demo_learner() -> int:
    """Create or update a deterministic demo learner and return the user id."""
    init_db()

    email = normalize_email(DEMO_EMAIL)
    user = get_user(email)
    if user is None:
        user = save_user(
            name="Demo Learner",
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            age=14,
            grade="8",
            institution="Demo School",
            field_of_study="Science",
            preferred_language="English",
            learning_goal="Improve reading and comprehension",
            dyslexia_status="Diagnosed dyslexia",
        )
        print(f"Created demo learner account: {user.email} (user_id={user.id})")
    else:
        print(f"Demo learner account already exists: {user.email} (user_id={user.id})")

    save_learner_profile(
        user_id=user.id,
        total_study_time_minutes=10,
        documents_uploaded=1,
        unique_topics_studied=2,
        total_questions_asked=5,
        average_quiz_score=45.0,
        preferred_learning_mode="Simplified Notes",
        learning_frequency="occasional",
        confidence_level=0.45,
        explanation_complexity="moderate",
        prefers_examples=True,
        prefers_analogies=True,
        prefers_bullet_points=True,
        avg_response_length_preference=150,
        comprehension_score=55.0,
        comprehension_level="Average-High",
        quiz_accuracy_score=45.0,
        conceptual_answer_score=40.0,
        learning_support_score=80.0,
        first_attempt_score=40.0,
        response_efficiency_score=40.0,
        metric_breakdown={"note": "demo profile"},
        learner_model_metadata={"demo": True, "teaching_style": "Moderate, Structured, Practice-Oriented"},
        learning_behaviour_analytics_score=80.0,
        learning_behaviour_analytics_level="High",
        mode_engagement_score=80.0,
        mode_switching_score=80.0,
        feature_utilization_score=80.0,
        post_mode_improvement_score=80.0,
        mode_retention_score=80.0,
    )

    save_adaptive_preferences(
        user_id=user.id,
        preferred_explanation_complexity="moderate",
        prefers_visual_aids=False,
        prefers_audio=False,
        prefers_bullet_points=True,
        prefers_short_sentences=True,
        prefers_analogies=True,
        prefers_real_world_examples=True,
        avg_successful_response_length=150,
        response_time_patience=45,
        quiz_difficulty_preference="adaptive",
    )

    # Remove any existing learning mode sessions for this demo user
    # so the seed is deterministic, then insert a Simplified Notes session.
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("DELETE FROM learning_mode_sessions WHERE user_id = ?", (user.id,))
        conn.commit()

    save_learning_mode_session(
        session_id="demo_notes_session_1",
        user_id=user.id,
        modes_used=["Simplified Notes"],
        quiz_accuracy=85.0,
        comprehension_score=78.0,
    )

    return user.id


def verify_backend_recommendation(user_id: int) -> None:
    """Validate the seeded account via the adaptive plan backend API routes."""
    app = Flask(__name__)
    app.register_blueprint(adaptive_bp)

    with app.test_client() as client:
        response = client.post(
            "/adaptive-plan/generate",
            json={"user_id": user_id, "document_concepts": ["Photosynthesis", "Water Cycle"]},
        )
        body = response.get_json() or {}
        print("/adaptive-plan/generate status:", response.status_code)
        print("generate body.summary.recommended_learning_mode:", body.get("plan", {}).get("decision_summary", {}).get("recommended_learning_mode"))
        print("generate body.learning_strategy:", body.get("plan", {}).get("decision_summary", {}).get("learning_strategy"))

        current = client.get(f"/adaptive-plan/current/{user_id}")
        current_body = current.get_json() or {}
        print("/adaptive-plan/current status:", current.status_code)
        print("current summary.recommended_learning_mode:", current_body.get("summary", {}).get("recommended_learning_mode"))
        print("current summary.learning_strategy:", current_body.get("summary", {}).get("learning_strategy"))

        path = client.get(f"/adaptive-plan/learning-path/{user_id}")
        path_body = path.get_json() or {}
        print("/adaptive-plan/learning-path status:", path.status_code)
        print("learning_path summary.recommended_learning_mode:", path_body.get("summary", {}).get("recommended_learning_mode"))
        print("learning_path summary.learning_strategy:", path_body.get("summary", {}).get("learning_strategy"))
        print("learning_path steps:", path_body.get("learning_path"))

        # Verify the learning path contains Simplified Notes followed immediately by a Quiz
        learning_path = path_body.get('learning_path') or []
        simplified_index = next((i for i, s in enumerate(learning_path) if s.get('action') == 'learning_mode' and s.get('mode') == 'Simplified Notes'), None)
        seq_ok = False
        if simplified_index is not None and simplified_index + 1 < len(learning_path):
            seq_ok = learning_path[simplified_index + 1].get('action') == 'quiz'

        print("Simplified Notes -> Quiz sequence present:", seq_ok)

        direct = RecommendationEngine.recommend_learning_mode(user_id)
        print("Direct RecommendationEngine output:", direct)

        if current.status_code != 200 or current_body.get("summary", {}).get("recommended_learning_mode") is None:
            raise RuntimeError("Demo learner backend recommendation verification failed.")
        if not seq_ok:
            raise RuntimeError("Demo learner backend learning path did not contain Simplified Notes -> Quiz sequence.")


if __name__ == "__main__":
    demo_user_id = seed_demo_learner()
    print(f"Demo learner ready: {DEMO_EMAIL} / {DEMO_PASSWORD} (user_id={demo_user_id})")
    verify_backend_recommendation(demo_user_id)
    print("Demo learner backend recommendation verified successfully.")
