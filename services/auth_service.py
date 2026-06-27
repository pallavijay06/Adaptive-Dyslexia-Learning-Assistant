"""Authentication helpers for user registration and login."""

from __future__ import annotations

import re
from typing import Tuple

from werkzeug.security import check_password_hash, generate_password_hash

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LENGTH = 8


def normalize_email(email: str) -> str:
    """Normalize email addresses for consistent lookup."""
    return email.strip().lower()


def hash_password(password: str) -> str:
    """Hash a plaintext password for secure storage."""
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    return check_password_hash(password_hash, password)


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate an email address format."""
    if not email or not email.strip():
        return False, "Email address is required."

    normalized = normalize_email(email)
    if not EMAIL_REGEX.match(normalized):
        return False, "Please provide a valid email address."

    return True, ""


def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength for registration."""
    if not password:
        return False, "Password is required."
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."
    if password.islower() or password.isupper():
        return False, "Password should include both uppercase and lowercase characters."
    if not any(char.isdigit() for char in password):
        return False, "Password should include at least one digit."
    if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/`~" for char in password):
        return False, "Password should include at least one symbol."
    return True, ""


def validate_registration_fields(
    full_name: str,
    email: str,
    password: str,
    confirm_password: str,
    age: str,
    grade: str,
    institution: str,
    field_of_study: str,
) -> Tuple[bool, str]:
    """Validate the fields for user registration."""
    if not full_name or not full_name.strip():
        return False, "Full name is required."

    email_valid, email_message = validate_email(email)
    if not email_valid:
        return False, email_message

    password_valid, password_message = validate_password(password)
    if not password_valid:
        return False, password_message

    if password != confirm_password:
        return False, "Password and confirmation do not match."

    if age:
        try:
            numeric_age = int(age)
            if numeric_age < 5 or numeric_age > 120:
                return False, "Please enter a realistic age between 5 and 120."
        except ValueError:
            return False, "Age must be a valid number."

    if not grade or not grade.strip():
        return False, "Please provide your grade, class, or year of study."
    if not institution or not institution.strip():
        return False, "Please provide your school or institution name."
    if not field_of_study or not field_of_study.strip():
        return False, "Please provide your field of study or stream."

    return True, ""
