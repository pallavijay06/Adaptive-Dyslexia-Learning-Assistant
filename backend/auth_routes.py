"""Authentication API routes — exposes existing auth_service and db functions."""

from __future__ import annotations

import logging
from datetime import datetime

from flask import Blueprint, jsonify, request, session

from database.db import (
    create_login_session,
    close_login_session,
    get_user,
    get_user_by_id,
    save_user,
    update_user_last_login,
    update_user_logout,
)
from services.auth_service import (
    hash_password,
    normalize_email,
    validate_email,
    validate_password,
    validate_registration_fields,
    verify_password,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = logging.getLogger(__name__)

_SESSION_USER_KEY = "user_id"
_SESSION_LOGIN_TIME_KEY = "login_time"
_SESSION_SESSION_ID_KEY = "db_session_id"


def _user_to_dict(user) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "grade": user.grade,
        "institution": user.institution,
        "field_of_study": user.field_of_study,
        "preferred_language": user.preferred_language,
        "learning_goal": user.learning_goal,
        "dyslexia_status": user.dyslexia_status,
        "registration_date": user.registration_date.isoformat() if user.registration_date else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "total_sessions": user.total_sessions,
        "total_learning_minutes": user.total_learning_minutes,
    }


def _current_user_id() -> int | None:
    return session.get(_SESSION_USER_KEY)


@auth_bp.post("/register")
def register():
    """Register a new learner account."""
    print("[REGISTER] raw body  :", request.get_data(as_text=True))
    print("[REGISTER] content-type:", request.content_type)
    data = request.get_json(silent=True) or {}
    print("[REGISTER] parsed JSON:", data)
    full_name = (data.get("full_name") or data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""
    age = str(data.get("age") or "")
    grade = (data.get("grade") or "").strip()
    institution = (data.get("institution") or "").strip()
    field_of_study = (data.get("field_of_study") or "").strip()
    preferred_language = (data.get("preferred_language") or "").strip() or None
    learning_goal = (data.get("learning_goal") or "").strip() or None
    dyslexia_status = (data.get("dyslexia_status") or "Prefer not to say").strip()

    valid, message = validate_registration_fields(
        full_name, email, password, confirm_password, age, grade, institution, field_of_study
    )
    if not valid:
        print("[REGISTER 400] validation failed:", message, "| payload:", request.get_json())
        return jsonify({"success": False, "error": message}), 400

    try:
        user = save_user(
            name=full_name,
            email=normalize_email(email),
            password_hash=hash_password(password),
            age=int(age) if age else 0,
            grade=grade,
            institution=institution,
            field_of_study=field_of_study,
            preferred_language=preferred_language,
            learning_goal=learning_goal,
            dyslexia_status=dyslexia_status,
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 409
    except Exception:
        logger.exception("Registration failed")
        return jsonify({"success": False, "error": "Registration failed."}), 500

    now = datetime.utcnow()
    update_user_last_login(user.id, now)
    db_session = create_login_session(user.id)
    session[_SESSION_USER_KEY] = user.id
    session[_SESSION_LOGIN_TIME_KEY] = now.isoformat()
    session[_SESSION_SESSION_ID_KEY] = db_session.id
    session.permanent = True

    return jsonify({"success": True, "user": _user_to_dict(user), "session_id": db_session.id}), 201


@auth_bp.post("/login")
def login():
    """Authenticate a learner and start a session."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    email_valid, email_msg = validate_email(email)
    if not email_valid:
        return jsonify({"success": False, "error": email_msg}), 400
    if not password:
        return jsonify({"success": False, "error": "Password is required."}), 400

    user = get_user(normalize_email(email))
    if user is None:
        return jsonify({"success": False, "error": "No account found."}), 404
    if not verify_password(password, user.password_hash):
        return jsonify({"success": False, "error": "Invalid email or password."}), 401

    now = datetime.utcnow()
    update_user_last_login(user.id, now)
    db_session = create_login_session(user.id)

    session[_SESSION_USER_KEY] = user.id
    session[_SESSION_LOGIN_TIME_KEY] = now.isoformat()
    session[_SESSION_SESSION_ID_KEY] = db_session.id
    session.permanent = True

    return jsonify({"success": True, "user": _user_to_dict(user), "session_id": db_session.id}), 200


@auth_bp.post("/logout")
def logout():
    """End the current learner session."""
    user_id = _current_user_id()
    db_session_id = session.get(_SESSION_SESSION_ID_KEY)
    login_time_str = session.get(_SESSION_LOGIN_TIME_KEY)

    if user_id and db_session_id and login_time_str:
        try:
            login_time = datetime.fromisoformat(login_time_str)
            logout_time = datetime.utcnow()
            close_login_session(db_session_id, user_id, login_time, logout_time)
            update_user_logout(user_id, logout_time)
        except Exception:
            logger.exception("Failed to close login session on logout")

    session.clear()
    return jsonify({"success": True}), 200


@auth_bp.get("/profile")
def get_profile():
    """Return the authenticated learner's profile."""
    user_id = _current_user_id()
    if user_id is None:
        return jsonify({"success": False, "error": "Not authenticated."}), 401

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return jsonify({"success": False, "error": "User not found."}), 404

    return jsonify({"success": True, "user": _user_to_dict(user)}), 200


@auth_bp.put("/profile")
def update_profile():
    """Update mutable profile fields for the authenticated learner."""
    user_id = _current_user_id()
    if user_id is None:
        return jsonify({"success": False, "error": "Not authenticated."}), 401

    user = get_user_by_id(user_id)
    if user is None:
        return jsonify({"success": False, "error": "User not found."}), 404

    data = request.get_json(silent=True) or {}
    allowed = {
        "preferred_language", "learning_goal", "dyslexia_status",
        "grade", "institution", "field_of_study",
    }
    updates = {k: v for k, v in data.items() if k in allowed and v is not None}

    if not updates:
        return jsonify({"success": False, "error": "No updatable fields provided."}), 400

    from database.db import _get_connection
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]
    try:
        with _get_connection() as conn:
            conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    except Exception:
        logger.exception("Profile update failed")
        return jsonify({"success": False, "error": "Profile update failed."}), 500

    updated_user = get_user_by_id(user_id)
    return jsonify({"success": True, "user": _user_to_dict(updated_user)}), 200


@auth_bp.get("/session")
def check_session():
    """Return current session status and user info if authenticated."""
    user_id = _current_user_id()
    if user_id is None:
        return jsonify({"authenticated": False}), 200

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return jsonify({"authenticated": False}), 200

    return jsonify({
        "authenticated": True,
        "user": _user_to_dict(user),
        "session_id": session.get(_SESSION_SESSION_ID_KEY),
    }), 200
