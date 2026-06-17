"""Text-to-Speech service for audio learning mode."""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from gtts import gTTS


class TTSError(RuntimeError):
    """Raised when audio generation fails."""


AUDIO_FOLDER = "generated_audio"

# Create audio folder if it doesn't exist
Path(AUDIO_FOLDER).mkdir(parents=True, exist_ok=True)


def clean_text_for_speech(text: str) -> str:
    """Clean text for natural-sounding text-to-speech generation.
    
    Removes or normalizes elements that sound unnatural when read aloud:
    - Markdown formatting
    - Bullet points and list markers
    - Excessive punctuation
    - Special symbols
    - Multiple spaces
    
    Args:
        text: Raw text that may contain formatting artifacts
        
    Returns:
        Cleaned text suitable for TTS
    """
    if not text or not text.strip():
        return ""

    text = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)

    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)

    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*(?:[-*+•‣◦]|\d+[\.)])\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*_]{3,}\s*$", " ", text, flags=re.MULTILINE)

    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"(\*|_|~~)(.*?)\1", r"\2", text)

    replacements = {
        "&": " and ",
        "@": " at ",
        "%": " percent ",
        "+": " plus ",
        "=": " equals ",
        "→": " leads to ",
        "->": " leads to ",
        "=>": " leads to ",
        "/": " or ",
    }
    for symbol, spoken in replacements.items():
        text = text.replace(symbol, spoken)

    text = re.sub(r"[#*_~^|\\<>{}\[\]()`]", " ", text)
    text = re.sub(r"([!?.]){2,}", r"\1", text)
    text = re.sub(r"[,;:]{2,}", ",", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"([,.!?;:])([A-Za-z])", r"\1 \2", text)

    text = re.sub(r"\n\s*\n+", ". ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text

def generate_audio(text: str, lang: str = "en", slow: bool = False) -> str:
    """Generate MP3 audio from text using Google Text-to-Speech.
    
    Automatically cleans text for natural speech before generation.
    
    Args:
        text: Text to convert to speech
        lang: Language code (default: "en" for English)
        slow: Whether to speak slowly (default: False)
        
    Returns:
        Path to generated MP3 file
        
    Raises:
        TTSError: If audio generation fails
    """
    if not text or not text.strip():
        raise TTSError("Text cannot be empty.")
    
    text = text.strip()
    
    # Clean text for natural speech
    text = clean_text_for_speech(text)
    
    if not text:
        raise TTSError("Text is empty after cleaning.")
    
    # Limit text length for performance (gTTS works best with reasonable text chunks)
    if len(text) > 5000:
        raise TTSError("Text is too long (max 5000 characters). Please split into smaller chunks.")
    
    try:
        # Generate unique filename
        filename = f"{uuid.uuid4()}.mp3"
        filepath = os.path.join(AUDIO_FOLDER, filename)
        
        # Create gTTS object. Playback speed is controlled in the browser,
        # so we always generate a single MP3 file at normal speed.
        tts = gTTS(
            text=text,
            lang=lang,
            slow=False,
            tld="co.uk"  # TLD for stability
        )
        
        # Save to file
        tts.save(filepath)
        
        # Verify file was created and has content
        if not os.path.exists(filepath):
            raise TTSError(f"Audio file was not created: {filepath}")
        
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            raise TTSError("Generated audio file is empty.")
        
        return filepath
    
    except TTSError:
        raise
    except Exception as exc:
        raise TTSError(f"Audio generation failed: {exc}") from exc


def cleanup_audio_file(filepath: str) -> bool:
    """Safely delete an audio file.
    
    Args:
        filepath: Path to audio file to delete
        
    Returns:
        True if deleted, False if file doesn't exist
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    except Exception as exc:
        print(f"Warning: Could not delete audio file {filepath}: {exc}")
        return False


def cleanup_old_audio_files(keep_count: int = 50) -> None:
    """Clean up old audio files, keeping only the most recent.
    
    Useful for preventing disk space issues from accumulated audio files.
    
    Args:
        keep_count: Number of recent files to keep
    """
    try:
        audio_folder = Path(AUDIO_FOLDER)
        if not audio_folder.exists():
            return
        
        mp3_files = sorted(
            audio_folder.glob("*.mp3"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if len(mp3_files) > keep_count:
            for old_file in mp3_files[keep_count:]:
                try:
                    old_file.unlink()
                except Exception as exc:
                    print(f"Warning: Could not delete {old_file}: {exc}")
    except Exception as exc:
        print(f"Warning: Cleanup failed: {exc}")
