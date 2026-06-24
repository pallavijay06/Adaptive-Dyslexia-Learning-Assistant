"""Image-based Diagram Explanation for STEM support.

This module is designed for image input only and keeps the public API
stable so future PDF extraction can pass extracted image paths directly
into explain_diagram().
"""

from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any

from services.cache_service import (
    DIAGRAM_CACHE_TTL_DAYS,
    get_cache_value,
    make_diagram_cache_key,
    set_cache_value,
)
from services.gemini_service import (
    GeminiAPIError,
    _extract_response_text,
    _get_client,
    _get_model_name,
)
from services.text_cleanup import remove_markdown_and_html

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def explain_diagram(image_path: str) -> dict[str, Any]:
    """Explain a diagram from a PNG or JPG image.

    The public API is intentionally simple so PDF image extraction can reuse
    the same call signature in the future.
    """
    print("[DIAGRAM DEBUG] Entering explain_diagram()")
    image_file = Path(image_path or "")
    print("[DIAGRAM DEBUG] Image Path:", str(image_file))
    print("[DIAGRAM DEBUG] Exists:", image_file.exists())
    print("[DIAGRAM DEBUG] Is file:", image_file.is_file())
    print("[DIAGRAM DEBUG] Extension:", image_file.suffix.lower())

    if image_file.exists() and image_file.is_file():
        try:
            size = image_file.stat().st_size
        except Exception as exc:
            size = f"error reading size: {exc}"
        print("[DIAGRAM DEBUG] Size:", size)

    if not image_file.exists() or not image_file.is_file():
        print("[DIAGRAM DEBUG] Invalid image: file does not exist or is not a file")
        return _unknown_diagram_response()

    if image_file.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        print("[DIAGRAM DEBUG] Invalid image: unsupported extension")
        return _unknown_diagram_response()

    try:
        image_bytes = _read_image_bytes(image_file)
        cache_key = make_diagram_cache_key(image_bytes)
        cached = get_cache_value(cache_key)
        if cached is not None:
            logger.info("[CACHE HIT] Diagram")
            print("[DIAGRAM DEBUG] Cache hit - returning cached diagram explanation")
            return cached
        logger.info("[CACHE MISS] Diagram")
        print("[DIAGRAM DEBUG] Cache miss - proceeding to Gemini")
    except Exception as exc:
        print("[DIAGRAM DEBUG] Cache preparation failed:", repr(exc))
        # If cache key generation fails, continue to Gemini analysis.
        image_bytes = None
        cache_key = None

    try:
        raw_output = _analyze_image_with_gemini(image_file)
        parsed = _parse_diagram_response(raw_output)
        if parsed:
            print("[DIAGRAM DEBUG] Parsed diagram response successfully")
            if cache_key is not None:
                set_cache_value(cache_key, parsed, ttl_hours=DIAGRAM_CACHE_TTL_DAYS * 24)
                logger.info("[CACHE STORE] Diagram")
            return parsed
        print("[DIAGRAM DEBUG] Parsed diagram response was None")
    except Exception as exc:
        print("[DIAGRAM DEBUG] Gemini error:", repr(exc))
        print("=================================================")
        print("DIAGRAM FALLBACK TRIGGERED")
        print("Reason: Gemini error")
        print("=================================================")
        return _unknown_diagram_response()

    print("=================================================")
    print("DIAGRAM FALLBACK TRIGGERED")
    print("Reason: Parse or sanitization failure")
    print("=================================================")
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
        print("[DIAGRAM DEBUG] Entering _analyze_image_with_gemini()")
        print("[DIAGRAM DEBUG] Sending image to Gemini")
        print("[DIAGRAM DEBUG] Selected model:", _get_model_name())
        print("[DIAGRAM DEBUG] Image byte size:", len(image_data))
        print("[DIAGRAM DEBUG] Mime type:", media_type)

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
        raw_text = _extract_response_text(response)
        print("=================================================")
        print("RAW GEMINI RESPONSE")
        print("=================================================")
        print(raw_text)
        print("=================================================")
        return raw_text
    except Exception as exc:
        print("[DIAGRAM DEBUG] Gemini request failed:", repr(exc))
        raise GeminiAPIError(f"Gemini Vision analysis failed: {exc}") from exc

def _read_image_bytes(image_path: Path) -> bytes:
    try:
        with open(image_path, "rb") as file:
            return file.read()
    except Exception as exc:
        raise GeminiAPIError(f"Could not read image file for hashing: {exc}") from exc


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
    print("[DIAGRAM DEBUG] Entering _parse_diagram_response()")
    raw = response_text or ""
    print("[DIAGRAM DEBUG] Original response text:")
    print(raw)
    stripped = _strip_code_block(raw).strip()

    data = None
    json_text = _extract_json_object(stripped)
    if json_text is not None:
        print("[DIAGRAM DEBUG] JSON extracted from stripped response")
        print(json_text)
        try:
            data = json.loads(json_text)
            print("[DIAGRAM DEBUG] JSON parsing succeeded")
            print("[DIAGRAM DEBUG] Parsed keys:", list(data.keys()) if isinstance(data, dict) else type(data))
        except json.JSONDecodeError as exc:
            print("[DIAGRAM DEBUG] JSON parsing failed:", repr(exc))
            data = None

    if data is None:
        cleaned = remove_markdown_and_html(stripped).strip()
        cleaned = _strip_code_block(cleaned)
        json_text = _extract_json_object(cleaned)
        if json_text is not None:
            print("[DIAGRAM DEBUG] JSON extracted from cleaned response")
            print(json_text)
            try:
                data = json.loads(json_text)
                print("[DIAGRAM DEBUG] JSON parsing succeeded after cleanup")
                print("[DIAGRAM DEBUG] Parsed keys:", list(data.keys()) if isinstance(data, dict) else type(data))
            except json.JSONDecodeError as exc:
                print("[DIAGRAM DEBUG] JSON parsing failed after cleanup:", repr(exc))
                data = None

    if data is None:
        print("[DIAGRAM DEBUG] Falling back to simple key/value parsing")
        data = _parse_simple_key_values(stripped)
        print("[DIAGRAM DEBUG] Parsed simple key/value data:", data)

    sanitized = _sanitize_diagram_response(data)
    print("[DIAGRAM DEBUG] Sanitized diagram response:", sanitized)
    if sanitized:
        return sanitized
    print("[DIAGRAM DEBUG] Sanitization returned None or empty result")
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
    print("[DIAGRAM DEBUG] Entering _unknown_diagram_response()")
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
