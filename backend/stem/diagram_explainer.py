"""Image-based Diagram Explanation for STEM support.

This module is designed for image input only and keeps the public API
stable so future PDF extraction can pass extracted image paths directly
into explain_diagram().
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

from services.gemini_service import (
    GeminiAPIError,
    _extract_response_text,
    _get_client,
    _get_model_name,
)
from services.text_cleanup import remove_markdown_and_html

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def explain_diagram(image_path: str) -> dict[str, Any]:
    """Explain a diagram from a PNG or JPG image.

    The public API is intentionally simple so PDF image extraction can reuse
    the same call signature in the future.
    """
    image_file = Path(image_path or "")
    if not image_file.exists() or not image_file.is_file():
        return _unknown_diagram_response()

    if image_file.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        return _unknown_diagram_response()

    try:
        raw_output = _analyze_image_with_gemini(image_file)
        parsed = _parse_diagram_response(raw_output)
        if parsed:
            return parsed
    except Exception:
        pass

    return _unknown_diagram_response()


def _analyze_image_with_gemini(image_path: Path) -> str:
    """Use Gemini Vision to analyze the uploaded diagram image."""
    try:
        with open(image_path, "rb") as file:
            image_data = file.read()
    except Exception as exc:
        raise GeminiAPIError(f"Could not read image file: {exc}") from exc

    encoded_image = base64.b64encode(image_data).decode("utf-8")
    suffix = image_path.suffix.lower()
    media_type = "image/png" if suffix == ".png" else "image/jpeg"

    prompt = _diagram_prompt()

    try:
        from google.genai import types

        client = _get_client()
        response = client.models.generate_content(
            model=_get_model_name(),
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=prompt),
                        types.Part(
                            inline_data=types.Blob(
                                mime_type=media_type,
                                data=encoded_image,
                            )
                        ),
                    ],
                ),
            ],
        )
        return _extract_response_text(response)
    except Exception as exc:
        raise GeminiAPIError(f"Gemini Vision analysis failed: {exc}") from exc


def _diagram_prompt() -> str:
    """Build a dyslexia-friendly prompt for explaining diagrams."""
    return (
        "You are a dyslexia-friendly STEM tutor that explains diagrams.\n"
        "DO NOT only describe what is visible. Teach the concept the diagram shows.\n"
        "Use very simple English, short sentences, and avoid jargon.\n"
        "Return valid JSON only with these keys exactly:\n"
        "diagram_type, purpose, how_it_works, component_roles, key_concept, simplified_explanation, key_takeaway.\n"
        "Requirements for each key:\n"
        "- diagram_type: a short label (max 3 words).\n"
        "- purpose: 1-2 short sentences explaining why the diagram exists.\n"
        "- how_it_works: 3-5 short numbered steps describing the process.\n"
        "- component_roles: up to 5 items, each as {\"component\": \"name\", \"role\": \"short role\"}.\n"
        "- key_concept: 1-2 short sentences explaining the main STEM concept.\n"
        "- simplified_explanation: up to 3 very simple sentences, explain like a 12-year-old.\n"
        "- key_takeaway: one short sentence with the single most important idea.\n"
        "If you cannot identify a field, return \"Unknown\" (or an empty list for lists).\n"
        "Be concise. Keep each sentence short. Return JSON ONLY.\n"
        "Example output:\n"
        "{\n"
        "  \"diagram_type\": \"Circuit Diagram\",\n"
        "  \"purpose\": \"Used to study the relationship between voltage and current. It helps measure voltage and current.\",\n"
        "  \"how_it_works\": [\"The battery provides energy.\", \"Current flows through the resistor.\", \"The ammeter measures current.\", \"The voltmeter measures voltage.\"],\n"
        "  \"component_roles\": [{\"component\": \"Battery\", \"role\": \"Provides power\"}, {\"component\": \"Resistor\", \"role\": \"Controls current\"}],\n"
        "  \"key_concept\": \"Voltage and current are related.\",\n"
        "  \"simplified_explanation\": \"Electricity moves like water in a pipe. The battery pushes it and the meters check how much is flowing.\",\n"
        "  \"key_takeaway\": \"More voltage usually means more current.\"\n"
        "}"
    )


def _parse_diagram_response(response_text: str) -> dict[str, Any] | None:
    """Parse the model response and normalize the diagram explanation."""
    raw = response_text or ""
    stripped = _strip_code_block(raw).strip()

    data = None
    json_text = _extract_json_object(stripped)
    if json_text is not None:
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            data = None

    if data is None:
        cleaned = remove_markdown_and_html(stripped).strip()
        cleaned = _strip_code_block(cleaned)
        json_text = _extract_json_object(cleaned)
        if json_text is not None:
            try:
                data = json.loads(json_text)
            except json.JSONDecodeError:
                data = None

    if data is None:
        data = _parse_simple_key_values(stripped)

    sanitized = _sanitize_diagram_response(data)
    if sanitized:
        return sanitized
    return None


def _strip_code_block(text: str) -> str:
    if text.startswith("```") and text.endswith("```"):
        return text.strip("`\n ")
    return text


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start:end + 1]


def _parse_simple_key_values(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized = key.strip().lower().replace(" ", "_")
        if normalized in {
            "diagram_type",
            "purpose",
            "key_concept",
            "simplified_explanation",
            "key_takeaway",
        }:
            data[normalized] = value.strip()
        elif normalized == "how_it_works":
            # split into numbered or comma separated steps
            parts = [p.strip(" -\n\t.") for p in re.split(r"[\n,]+", value) if p.strip()]
            data[normalized] = parts
        elif normalized == "component_roles":
            # component roles may be provided as multiple lines like "Battery: Provides power"
            items: list[dict[str, str]] = []
            for part in re.split(r"[\n,]+", value):
                if not part.strip():
                    continue
                if "-" in part and ":" not in part:
                    # formats like "Battery - Provides power"
                    comp, role = [p.strip() for p in part.split("-", 1)]
                elif ":" in part:
                    comp, role = [p.strip() for p in part.split(":", 1)]
                else:
                    comp = part.strip()
                    role = ""
                items.append({"component": comp, "role": role})
            data[normalized] = items
    return data


def _sanitize_diagram_response(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    # Educational fields
    diagram_type = _take_first_words(_string_value(data.get("diagram_type")), 3)
    purpose = _take_first_sentences(_string_value(data.get("purpose")), 2)
    how_it_works = _list_of_strings(data.get("how_it_works"))[:5]
    # component_roles should be a list of {component, role}
    comp_roles_raw = data.get("component_roles")
    component_roles: list[dict[str, str]] = []
    if isinstance(comp_roles_raw, list):
        for item in comp_roles_raw[:5]:
            if isinstance(item, dict):
                component_roles.append({
                    "component": _string_value(item.get("component")),
                    "role": _string_value(item.get("role")),
                })
            elif isinstance(item, str) and ":" in item:
                comp, role = [p.strip() for p in item.split(":", 1)]
                component_roles.append({"component": comp, "role": role})
    elif isinstance(comp_roles_raw, dict):
        # single dict mapping
        for k, v in list(comp_roles_raw.items())[:5]:
            component_roles.append({"component": _string_value(k), "role": _string_value(v)})

    key_concept = _take_first_sentences(_string_value(data.get("key_concept")), 2)
    simplified_explanation = _take_first_sentences(_string_value(data.get("simplified_explanation")), 3)
    key_takeaway = _take_first_sentence(_string_value(data.get("key_takeaway")))

    if not diagram_type:
        diagram_type = "Unknown"
    if not purpose:
        purpose = "Unable to determine diagram purpose."
    if not how_it_works:
        how_it_works = []
    if not component_roles:
        component_roles = []
    if not key_concept:
        key_concept = ""
    if not simplified_explanation:
        simplified_explanation = "The diagram could not be analyzed."
    if not key_takeaway:
        key_takeaway = "Try another image."

    return {
        "diagram_type": diagram_type,
        "purpose": purpose,
        "how_it_works": how_it_works,
        "component_roles": component_roles,
        "key_concept": key_concept,
        "simplified_explanation": simplified_explanation,
        "key_takeaway": key_takeaway,
    }


def _unknown_diagram_response() -> dict[str, Any]:
    return {
        "diagram_type": "Unknown",
        "purpose": "Unable to determine diagram purpose.",
        "how_it_works": [],
        "component_roles": [],
        "key_concept": "",
        "simplified_explanation": "The diagram could not be analyzed.",
        "key_takeaway": "Try another image.",
    }


def _string_value(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _list_of_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        parts = [item.strip() for item in re.split(r"[,;\n]+", value) if item.strip()]
        return parts
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _take_first_sentence(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return sentences[0].strip() if sentences else ""


def _take_first_sentences(text: str, count: int) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    return " ".join(sentences[:count]).strip()


def _take_first_words(text: str, count: int) -> str:
    words = [w for w in text.split() if w]
    return " ".join(words[:count]).strip()
