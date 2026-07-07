"""Progress Dashboard API routes — exposes existing progress_dashboard_service."""

from __future__ import annotations

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from database.db import get_user_by_id
from services.progress_dashboard_service import get_dashboard_data

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")
logger = logging.getLogger(__name__)


def _serialize(obj):
    """Recursively make dashboard data JSON-serialisable."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialize(getattr(obj, k)) for k in obj.__dataclass_fields__}
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    if isinstance(obj, set):
        return [_serialize(i) for i in sorted(obj)]
    return obj


@dashboard_bp.get("/<int:user_id>")
def full_dashboard(user_id: int):
    """Return the complete progress dashboard for a learner."""
    user = get_user_by_id(user_id)
    if user is None:
        return jsonify({"success": False, "error": "User not found."}), 404

    try:
        data = get_dashboard_data(user_id)
        # Remove ORM objects — keep only serialisable data
        data.pop("user", None)
        data.pop("profile", None)
        return jsonify({"success": True, "dashboard": _serialize(data)}), 200
    except Exception:
        logger.exception("Dashboard generation failed for user %s", user_id)
        return jsonify({"success": False, "error": "Dashboard generation failed."}), 500


@dashboard_bp.get("/<int:user_id>/overview")
def dashboard_overview(user_id: int):
    """Return only the overview section of the dashboard."""
    try:
        data = get_dashboard_data(user_id)
        return jsonify({"success": True, "overview": _serialize(data.get("overview", {}))}), 200
    except Exception:
        logger.exception("Dashboard overview failed for user %s", user_id)
        return jsonify({"success": False, "error": "Dashboard overview failed."}), 500


@dashboard_bp.get("/<int:user_id>/progress")
def dashboard_progress(user_id: int):
    """Return the progress metrics section."""
    try:
        data = get_dashboard_data(user_id)
        return jsonify({"success": True, "progress": _serialize(data.get("progress", {}))}), 200
    except Exception:
        logger.exception("Dashboard progress failed for user %s", user_id)
        return jsonify({"success": False, "error": "Dashboard progress failed."}), 500


@dashboard_bp.get("/<int:user_id>/quiz-performance")
def dashboard_quiz_performance(user_id: int):
    """Return quiz performance data."""
    try:
        data = get_dashboard_data(user_id)
        return jsonify({"success": True, "quiz_performance": _serialize(data.get("quiz_performance", {}))}), 200
    except Exception:
        logger.exception("Dashboard quiz performance failed for user %s", user_id)
        return jsonify({"success": False, "error": "Dashboard quiz performance failed."}), 500


@dashboard_bp.get("/<int:user_id>/concept-mastery")
def dashboard_concept_mastery(user_id: int):
    """Return concept mastery rows."""
    try:
        data = get_dashboard_data(user_id)
        return jsonify({
            "success": True,
            "concept_mastery": _serialize(data.get("concept_mastery", [])),
            "weak_concepts": _serialize(data.get("weak_concepts", [])),
        }), 200
    except Exception:
        logger.exception("Dashboard concept mastery failed for user %s", user_id)
        return jsonify({"success": False, "error": "Dashboard concept mastery failed."}), 500


@dashboard_bp.get("/<int:user_id>/learning-modes")
def dashboard_learning_modes(user_id: int):
    """Return learning mode usage and effectiveness."""
    try:
        data = get_dashboard_data(user_id)
        return jsonify({
            "success": True,
            "learning_mode_usage": _serialize(data.get("learning_mode_usage", [])),
            "learning_mode_effectiveness": _serialize(data.get("learning_mode_effectiveness", {})),
            "favorite_mode": data.get("favorite_mode"),
        }), 200
    except Exception:
        logger.exception("Dashboard learning modes failed for user %s", user_id)
        return jsonify({"success": False, "error": "Dashboard learning modes failed."}), 500


@dashboard_bp.get("/<int:user_id>/recommendations")
def dashboard_recommendations(user_id: int):
    """Return dashboard recommendations, badges, and insights."""
    try:
        data = get_dashboard_data(user_id)
        return jsonify({
            "success": True,
            "recommendations": _serialize(data.get("recommendations", [])),
            "badges": data.get("badges", []),
            "insights": data.get("insights", []),
        }), 200
    except Exception:
        logger.exception("Dashboard recommendations failed for user %s", user_id)
        return jsonify({"success": False, "error": "Dashboard recommendations failed."}), 500


@dashboard_bp.get("/<int:user_id>/timeline")
def dashboard_timeline(user_id: int):
    """Return the activity timeline."""
    try:
        data = get_dashboard_data(user_id)
        return jsonify({
            "success": True,
            "timeline": _serialize(data.get("timeline", [])),
            "timeline_days": _serialize(data.get("timeline_days", [])),
        }), 200
    except Exception:
        logger.exception("Dashboard timeline failed for user %s", user_id)
        return jsonify({"success": False, "error": "Dashboard timeline failed."}), 500


@dashboard_bp.get("/<int:user_id>/study-activity")
def dashboard_study_activity(user_id: int):
    """Return daily/weekly/monthly study activity chart data."""
    try:
        data = get_dashboard_data(user_id)
        return jsonify({"success": True, "study_activity": _serialize(data.get("study_activity", {}))}), 200
    except Exception:
        logger.exception("Dashboard study activity failed for user %s", user_id)
        return jsonify({"success": False, "error": "Dashboard study activity failed."}), 500


@dashboard_bp.get("/<int:user_id>/difficulty-profile")
def dashboard_difficulty_profile(user_id: int):
    """Return the difficulty profile and learning progress analytics."""
    try:
        data = get_dashboard_data(user_id)
        return jsonify({
            "success": True,
            "difficulty_profile": _serialize(data.get("difficulty_profile", {})),
            "learning_progress_analytics": _serialize(data.get("learning_progress_analytics", {})),
        }), 200
    except Exception:
        logger.exception("Dashboard difficulty profile failed for user %s", user_id)
        return jsonify({"success": False, "error": "Dashboard difficulty profile failed."}), 500
