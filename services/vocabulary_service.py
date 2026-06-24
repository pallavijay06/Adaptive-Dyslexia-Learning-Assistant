"""Vocabulary extraction service using AI for dyslexia support."""

from __future__ import annotations

import json
import logging
import re
from collections import Counter

from services.llm_router import generate_content
from services.ollama_service import clean_ollama_response

logger = logging.getLogger(__name__)

DEFAULT_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "as", "at", "be", "because", "been", "before",
    "being", "below", "between", "both", "but", "by", "could", "did", "do",
    "does", "doing", "down", "during", "each", "few", "for", "from", "further",
    "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it",
    "its", "itself", "just", "me", "more", "most", "my", "myself", "no",
    "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other",
    "our", "ours", "ourselves", "out", "over", "own", "same", "she",
    "should", "so", "some", "such", "than", "that", "the", "their", "theirs",
    "them", "themselves", "then", "there", "these", "they", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "with", "you", "your", "yours", "yourself", "yourselves"
}

GENERIC_VOCABULARY_BLOCKWORDS = {
    "basic",
    "learn",
    "learns",
    "learned",
    "learning",
    "understand",
    "understanding",
    "understood",
    "together",
    "rule",
    "rules",
    "important",
    "topic",
    "use",
    "using",
    "makes",
    "make",
    "need",
    "needs",
    "help",
    "helps",
    "helping",
}

MAX_VOCABULARY_PHRASE_WORDS = 2


class VocabularyError(RuntimeError):
    """Raised when vocabulary extraction fails."""


def generate_vocabulary(text: str, word_count: int = 10) -> list[dict[str, str]]:
    """Extract difficult vocabulary from text with AI-driven definitions.

    Retries once when model output is malformed and falls back to local NLP.
    """
    text = text[:3000]

    if not text or not text.strip():
        raise VocabularyError("Text cannot be empty.")

    word_count = max(1, min(50, int(word_count)))

    prompt = (
        "Extract difficult vocabulary from this text.\n\n"
        "Return ONLY a JSON array. Example format:\n"
        '[\n'
        '  {"word": "photosynthesis", "meaning": "Process where plants make food from sunlight"},\n'
        '  {"word": "mitochondria", "meaning": "Part of cell that makes energy"}\n'
        ']\n\n'
        "Rules:\n"
        f"- Identify exactly {word_count} difficult words\n"
        "- Create SIMPLE definitions (max 10 words)\n"
        "- Use child-friendly language\n"
        "- Return ONLY valid JSON\n"
        "- No explanation\n"
        "- No thinking\n"
        "- No markdown\n"
        "- No code blocks\n\n"
        f"Text:\n{text.strip()}"
    )

    last_exc: Exception | None = None
    for attempt in range(1, 3):
        try:
            # Vocabulary extraction limited to 500 tokens
            response = generate_content(prompt, max_tokens=500)
            return _parse_vocabulary_json(response)
        except VocabularyError as exc:
            logger.warning("Vocabulary parse failed on attempt %s: %s", attempt, exc)
            last_exc = exc
            if attempt == 1:
                continue
            break
        except Exception as exc:
            logger.warning("Vocabulary generation failed on attempt %s: %s", attempt, exc)
            last_exc = exc
            if attempt == 1:
                continue
            break

    logger.exception("Vocabulary extraction failed twice. Falling back to local extraction.")
    vocabulary = _fallback_vocabulary_from_text(text, word_count)
    if vocabulary:
        return vocabulary

    raise VocabularyError(
        "Vocabulary extraction encountered a formatting issue and could not extract key terms."
    ) from last_exc


def _parse_vocabulary_json(response: str) -> list[dict[str, str]]:
    if not response or not response.strip():
        raise VocabularyError("Empty response from vocabulary extractor.")

    cleaned = _sanitize_response_text(response)
    json_str = _extract_json_array(cleaned)

    if not json_str:
        raise VocabularyError("Could not locate vocabulary JSON in the model response.")

    json_str = _sanitize_json_string(json_str)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as first_exc:
        repaired = _repair_json_string(json_str)
        try:
            data = json.loads(repaired)
        except json.JSONDecodeError as second_exc:
            logger.warning("Vocabulary JSON repair failed: %s", second_exc)
            vocabulary = _regex_vocabulary_fallback(cleaned)
            if vocabulary:
                return vocabulary
            raise VocabularyError("Vocabulary extraction encountered a formatting issue. Retrying...") from second_exc

    if not isinstance(data, list):
        raise VocabularyError("Expected JSON array in vocabulary response.")

    vocabulary = []
    for item in data:
        if not isinstance(item, dict):
            continue

        word = str(item.get("word", "")).strip()
        meaning = str(item.get("meaning", "")).strip()

        if word and meaning and _is_valid_vocabulary_term(word):
            vocabulary.append({"word": word, "meaning": meaning})

    if vocabulary:
        return vocabulary

    vocabulary = _regex_vocabulary_fallback(cleaned)
    if vocabulary:
        return vocabulary

    raise VocabularyError("Vocabulary extraction encountered a formatting issue. Retrying...")


def _is_valid_vocabulary_term(text: str) -> bool:
    if not text or not text.strip():
        return False

    cleaned = text.strip()
    if re.search(r"[^A-Za-z \-']", cleaned):
        return False

    tokens = [token.strip("-'").lower() for token in cleaned.split() if token.strip()]
    if not tokens or len(tokens) > MAX_VOCABULARY_PHRASE_WORDS:
        return False

    if any(token in DEFAULT_STOPWORDS or token in GENERIC_VOCABULARY_BLOCKWORDS for token in tokens):
        return False

    if len(tokens) == 1:
        return len(tokens[0]) >= 3

    return all(len(token) >= 4 for token in tokens) and any(len(token) >= 6 for token in tokens)

def _sanitize_response_text(text: str) -> str:
    text = clean_ollama_response(text)
    text = re.sub(r'```(?:json)?\s*([\s\S]*?)```', r'\1', text)
    text = re.sub(r'(?im)^\s*(Reasoning|Thoughts|Analysis)\s*:.*$', "", text)
    text = re.sub(r'(?m)^>.*$', "", text)
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', " ", text)
    return text.strip()


def _extract_json_array(text: str) -> str | None:
    start = text.find("[")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    candidate = text[start:index + 1]
                    if re.search(r'"?word"?\s*:', candidate, re.IGNORECASE):
                        return candidate
                    break
        start = text.find("[", start + 1)
    return None


def _sanitize_json_string(json_str: str) -> str:
    json_str = json_str.strip()
    json_str = json_str.replace("\r", " ")
    json_str = json_str.replace("\t", " ")
    json_str = json_str.replace("\n", " ")
    json_str = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', " ", json_str)
    return re.sub(r'\s+', " ", json_str).strip()


def _repair_json_string(json_str: str) -> str:
    repaired = json_str
    repaired = repaired.replace("“", '"').replace("”", '"').replace("’", "'")
    repaired = re.sub(r'([{,]\s*)(word|meaning|explanation|example)(\s*:)', r'\1"\2"\3', repaired)
    repaired = re.sub(r":\s*'([^']*)'", lambda m: ': "' + m.group(1).replace('"', '\\"') + '"', repaired)
    repaired = re.sub(r',\s*}', '}', repaired)
    repaired = re.sub(r',\s*\]', ']', repaired)
    repaired = re.sub(r',\s*,', ',', repaired)
    repaired = re.sub(r'\s+', ' ', repaired).strip()
    return repaired


def _regex_vocabulary_fallback(text: str) -> list[dict[str, str]]:
    words = re.findall(r'"word"\s*:\s*"([^"\n\r]+)"', text)
    meanings = re.findall(r'"meaning"\s*:\s*"([^"\n\r]+)"', text)
    vocabulary = []
    for word, meaning in zip(words, meanings):
        cleaned_word = word.strip()
        cleaned_meaning = meaning.strip()
        if cleaned_word and cleaned_meaning and _is_valid_vocabulary_term(cleaned_word):
            vocabulary.append({"word": cleaned_word, "meaning": cleaned_meaning})

    if vocabulary:
        return vocabulary

    pairs = re.findall(r'([A-Za-z\-\']{3,})\s*[:\-]\s*([^\n\r]+)', text)
    for word, meaning in pairs:
        if len(vocabulary) >= 10:
            break
        cleaned_word = word.strip().strip('"\'')
        cleaned_meaning = meaning.strip().strip('"\'')
        if cleaned_word and cleaned_meaning and _is_valid_vocabulary_term(cleaned_word):
            vocabulary.append({"word": cleaned_word, "meaning": cleaned_meaning})
    return vocabulary


def _fallback_vocabulary_from_text(text: str, word_count: int) -> list[dict[str, str]]:
    """Extract likely vocabulary locally when model JSON is unusable."""
    candidates = re.findall(r"\b[A-Za-z][A-Za-z\-']{5,}\b", text)
    counts = Counter(
        word.lower().strip("-'")
        for word in candidates
        if word.lower().strip("-'") not in DEFAULT_STOPWORDS
    )

    vocabulary = []
    for word, _ in counts.most_common(word_count):
        display_word = word.capitalize()
        if not _is_valid_vocabulary_term(display_word):
            continue
        vocabulary.append(
            {
                "word": display_word,
                "meaning": "Definition unavailable.",
            }
        )
    return vocabulary


def explain_word(word: str) -> dict[str, str]:
    """Get a detailed explanation of any word.
    
    Works for words that may not be in the uploaded document.
    Provides meaning, simple explanation, and example sentence.
    
    Args:
        word: Word to explain
        
    Returns:
        Dict with 'word', 'meaning', 'explanation', and 'example' keys
        
    Raises:
        VocabularyError: If explanation fails
    """
    if not word or not word.strip():
        raise VocabularyError("Word cannot be empty.")
    
    word = word.strip()
    
    prompt = (
        f"Explain this word: '{word}'\n\n"
        "Return ONLY valid JSON (no markdown, no code blocks).\n\n"
        "Format:\n"
        "{\n"
        '  "word": "the word",\n'
        '  "meaning": "Simple definition in max 10 words",\n'
        '  "explanation": "Slightly longer child-friendly explanation (1-2 sentences)",\n'
        '  "example": "An example sentence using the word"\n'
        "}\n\n"
        "Rules:\n"
        "- meaning: VERY simple (max 10 words)\n"
        "- explanation: Child-friendly and easy to understand\n"
        "- example: Clear sentence showing how to use the word\n"
        "- Return ONLY the JSON object\n"
        "- No markdown, no code blocks"
    )
    
    try:
        logger.info("[VOCAB] Explaining word: %s", word)
        logger.info("[VOCAB] Using max_tokens=%s", 300)
        response = generate_content(prompt, max_tokens=300)
        return _parse_word_explanation_json(response, fallback_word=word)
    except Exception as exc:
        error_text = str(exc).lower()
        if "402" in error_text or "quota exceeded" in error_text or "credits exhausted" in error_text:
            logger.error("[VOCAB] OpenRouter quota exceeded while explaining word: %s", word)
        logger.exception("Word explanation failed. Using local fallback for '%s'.", word)
        return _fallback_word_explanation(word)


def _parse_word_explanation_json(response: str, fallback_word: str = "Unknown") -> dict[str, str]:
    """Safely parse word explanation JSON from AI response.
    
    Args:
        response: Raw response from AI
        
    Returns:
        Word explanation dict
        
    Raises:
        VocabularyError: If JSON cannot be parsed
    """
    if not response or not response.strip():
        raise VocabularyError("Empty response from word explainer.")
    
    cleaned = _sanitize_response_text(response)
    
    # Try to find JSON object
    if "{" not in cleaned:
        raise VocabularyError("Response does not contain a JSON object.")
    
    # Extract JSON from response (in case there's extra text)
    import re

    matches = re.findall(
        r'\[\s*\{.*?\}\s*\]',
        cleaned,
        re.DOTALL
    )

    json_str = None

    for candidate in matches:
        if '"word"' in candidate and '"meaning"' in candidate:
            json_str = candidate
            break

    if json_str is None:
        # Try to find a JSON object instead of array
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            raise VocabularyError("Could not find valid JSON object in response.")
        
        json_str = cleaned[start_idx:end_idx + 1]
    
    json_str = _sanitize_json_string(json_str)
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        try:
            data = json.loads(_repair_json_string(json_str))
        except json.JSONDecodeError as exc:
            logger.warning("Word explanation JSON repair failed: %s", exc)
            data = _regex_word_explanation_fallback(cleaned, fallback_word)
    
    if isinstance(data, list) and data and isinstance(data[0], dict):
        data = data[0]
    if not isinstance(data, dict):
        return _fallback_word_explanation(fallback_word)
    
    # Extract and validate fields
    word = (data.get("word") or fallback_word or "Unknown").strip()
    meaning = (data.get("meaning") or "").strip()
    explanation = (data.get("explanation") or "").strip()
    example = (data.get("example") or "").strip()
    
    if not meaning:
        return _fallback_word_explanation(word)
    
    return {
        "word": word,
        "meaning": meaning,
        "explanation": explanation,
        "example": example
    }


def _regex_word_explanation_fallback(text: str, word: str) -> dict[str, str]:
    fields = {}
    for field in ("word", "meaning", "explanation", "example"):
        match = re.search(
            rf'"?{field}"?\s*:\s*"?([^"\n\r,}}]+)"?',
            text,
            flags=re.IGNORECASE,
        )
        if match:
            fields[field] = match.group(1).strip()

    if not fields.get("meaning"):
        return _fallback_word_explanation(word)

    return {
        "word": fields.get("word") or word,
        "meaning": fields["meaning"],
        "explanation": fields.get("explanation") or f"{word} is an important word to understand.",
        "example": fields.get("example") or f"I learned the word {word} today.",
    }


def _fallback_word_explanation(word: str) -> dict[str, str]:
    clean_word = re.sub(r"[^A-Za-z0-9 \-']", "", word).strip() or "this word"
    return {
        "word": clean_word,
        "meaning": "Definition unavailable.",
        "explanation": "No explanation is available at this time.",
        "example": "",
    }
