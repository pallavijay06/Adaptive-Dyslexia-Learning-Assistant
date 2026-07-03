from services.learning_strategy_engine import get_learning_strategy_decision_from_data


def test_high_performing_learner_uses_minimal_path():
    mode_effectiveness = {
        "mode_rankings": [
            {"mode": "Visual", "effectiveness": 88.0},
            {"mode": "Audio", "effectiveness": 38.0},
            {"mode": "Simplified Notes", "effectiveness": 30.0},
            {"mode": "AI Tutor", "effectiveness": 20.0},
        ],
        "recommended_mode": "Visual",
    }
    lba_data = {
        "learning_behaviour_analytics_score": 82.0,
        "mode_engagement_score": 80.0,
        "mode_switching_score": 70.0,
        "feature_utilization_score": 75.0,
        "post_mode_improvement_score": 78.0,
        "mode_retention_score": 74.0,
    }

    decision = get_learning_strategy_decision_from_data(mode_effectiveness, lba_data)

    assert decision.primary_learning_mode == "Visual"
    assert decision.support_learning_mode is None
    assert decision.ai_tutor_required is False
    assert decision.recommended_quiz_timing == "After Learning"


def test_average_learner_adds_support_mode_when_gap_is_small():
    mode_effectiveness = {
        "mode_rankings": [
            {"mode": "Simplified Notes", "effectiveness": 72.0},
            {"mode": "Audio", "effectiveness": 68.0},
            {"mode": "Visual", "effectiveness": 35.0},
            {"mode": "AI Tutor", "effectiveness": 20.0},
        ],
        "recommended_mode": "Simplified Notes",
    }
    lba_data = {
        "learning_behaviour_analytics_score": 58.0,
        "mode_engagement_score": 56.0,
        "mode_switching_score": 60.0,
        "feature_utilization_score": 55.0,
        "post_mode_improvement_score": 54.0,
        "mode_retention_score": 60.0,
    }

    decision = get_learning_strategy_decision_from_data(mode_effectiveness, lba_data)

    assert decision.primary_learning_mode == "Simplified Notes"
    assert decision.support_learning_mode == "Audio"
    assert decision.ai_tutor_required is False
    assert decision.recommended_quiz_timing == "After Learning"


def test_struggling_learner_uses_quiz_then_tutor():
    mode_effectiveness = {
        "mode_rankings": [
            {"mode": "Simplified Notes", "effectiveness": 76.0},
            {"mode": "Audio", "effectiveness": 70.0},
            {"mode": "Visual", "effectiveness": 35.0},
            {"mode": "AI Tutor", "effectiveness": 25.0},
        ],
        "recommended_mode": "Simplified Notes",
    }
    lba_data = {
        "learning_behaviour_analytics_score": 34.0,
        "mode_engagement_score": 32.0,
        "mode_switching_score": 42.0,
        "feature_utilization_score": 38.0,
        "post_mode_improvement_score": 28.0,
        "mode_retention_score": 30.0,
    }

    decision = get_learning_strategy_decision_from_data(mode_effectiveness, lba_data)

    assert decision.primary_learning_mode == "Simplified Notes"
    assert decision.support_learning_mode is None
    assert decision.ai_tutor_required is True
    assert decision.recommended_quiz_timing == "After Revision"
