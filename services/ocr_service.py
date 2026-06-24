# services/ocr_service.py
"""OCR service with image preprocessing and Gemini Vision fallback.

Supports:
- Printed text extraction (Tesseract)
- Scanned PDFs (preprocessing + Tesseract)
- Handwritten notes (attempts with preprocessing)
- Gemini Vision API fallback only when local OCR fails
"""

from __future__ import annotations

import base64
import io
import logging
import os
import string
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageOps
import pytesseract

from services.gemini_service import GeminiAPIError, GeminiConfigurationError

logger = logging.getLogger(__name__)
OCR_CONFIDENCE_THRESHOLD = 50.0


class OCRError(RuntimeError):
    """Base error for OCR service failures."""


class OCRPreprocessingError(OCRError):
    """Raised when image preprocessing fails."""


def extract_text_from_image(image_path: str) -> str:
    image_path = Path(image_path)

    if not image_path.exists():
        raise OCRError(f"Image file not found: {image_path}")

    best_local_text = ""

    # First try direct Tesseract
    try:
        text, confidence = _extract_with_tesseract(image_path)
        best_local_text = text
        if _is_valid_ocr_result(text):
            if confidence is None or confidence >= OCR_CONFIDENCE_THRESHOLD:
                logger.info("[OCR] Local OCR Success")
                return text
            logger.warning("[OCR] Local OCR confidence below threshold: %.1f", confidence)
        else:
            logger.warning("[OCR] OCR Validation Failed")
    except Exception as exc:
        logger.error("[OCR] Local OCR Failed: %s", exc)

    # Second try OCR with preprocessing
    try:
        text, confidence = _extract_with_preprocessing(image_path)
        best_local_text = text
        if _is_valid_ocr_result(text):
            if confidence is None or confidence >= OCR_CONFIDENCE_THRESHOLD:
                logger.info("[OCR] Local OCR Success")
                return text
            logger.warning("[OCR] Local OCR confidence below threshold: %.1f", confidence)
        else:
            logger.warning("[OCR] OCR Validation Failed")
    except Exception as exc:
        logger.error("[OCR] Local OCR Failed: %s", exc)

    logger.info("[OCR] Falling Back To Gemini Vision")
    try:
        text = _extract_with_gemini_vision(image_path)
        if text:
            return text
    except Exception as exc:
        logger.error("[OCR] Gemini Vision failed: %s", exc)

    if _is_valid_ocr_result(best_local_text):
        logger.info("[OCR] Returning best local OCR result after Gemini fallback failure")
        return best_local_text

    return ""


def extract_images_from_pdf(pdf_path: str | Path) -> list[str]:
    """Extract embedded PDF images into temporary files for STEM Diagram Explanation."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        return []

    image_paths: list[str] = []
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        logger.error("PDF image extraction requires pypdf: %s", exc)
        return []

    def _format_from_suffix(suffix: str | None) -> str:
        suffix = (suffix or "").lstrip(".").lower()
        if suffix in {"jpg", "jpeg"}:
            return "JPEG"
        if suffix in {"png", "gif", "webp"}:
            return suffix.upper()
        return "PNG"

    try:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            try:
                images = page.images
            except Exception:
                images = None

            if not images:
                continue

            if hasattr(images, "items"):
                image_iter = images.items()
            else:
                image_iter = enumerate(images)

            for _, image_obj in image_iter:
                if image_obj is None:
                    continue

                try:
                    image_name = getattr(image_obj, "name", None)
                    pil_image = getattr(image_obj, "image", None)
                    image_data = getattr(image_obj, "data", None)

                    if pil_image is not None:
                        suffix = image_path_suffix(image_name or getattr(pil_image, "format", None))
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                        temp_path = temp_file.name
                        temp_file.close()
                        pil_image.save(temp_path, format=_format_from_suffix(suffix))
                        image_paths.append(str(Path(temp_path).resolve()))
                        continue

                    if isinstance(image_data, (bytes, bytearray)):
                        suffix = image_path_suffix(image_name)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                            temp_file.write(image_data)
                            image_paths.append(str(Path(temp_file.name).resolve()))
                except Exception:
                    continue
    except Exception as exc:
        logger.error("Failed to extract PDF images: %s", exc)

    return image_paths


def extract_text_from_pdf_images(pdf_path: str | Path) -> str:
    """Render scanned PDF pages as images, then extract text with local OCR."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        return ""

    try:
        from pdf2image import convert_from_path
    except ImportError as exc:
        logger.error("Scanned PDF OCR requires pdf2image: %s", exc)
        return ""

    extracted_pages: list[str] = []
    try:
        page_images = convert_from_path(str(pdf_path), dpi=200, fmt="png")
    except Exception as exc:
        logger.error("Failed to render PDF pages as images: %s", exc)
        return ""

    for page_index, page_image in enumerate(page_images, start=1):
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                page_image.save(tmp, format="PNG")
                temp_path = tmp.name

            page_text = extract_text_from_image(temp_path)
            if page_text and page_text.strip():
                extracted_pages.append(page_text.strip())
        except Exception as exc:
            logger.error("OCR failed for PDF page %d: %s", page_index, exc)
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    return "\n\n".join(extracted_pages)


def image_path_suffix(image_name: str | None) -> str:
    if not image_name:
        return ".png"

    raw_name = str(image_name).strip()
    suffix = Path(raw_name).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return suffix

    format_name = raw_name.upper()
    if format_name in {"JPG", "JPEG"}:
        return ".jpg"
    if format_name == "PNG":
        return ".png"
    if format_name == "GIF":
        return ".gif"
    if format_name == "WEBP":
        return ".webp"

    return ".png"


def _is_handwritten(image_path: Path) -> bool:
    """
    Rough handwriting detector.

    Handwritten notes generally contain:
    - more irregular edges
    - varying stroke widths
    - less alignment than printed text
    """

    try:
        img = cv2.imread(str(image_path))

        if img is None:
            return False

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        edges = cv2.Canny(gray, 50, 150)

        edge_density = np.sum(edges > 0) / edges.size

        return edge_density > 0.12

    except Exception:
        return False
    

def _is_valid_ocr_result(text: str) -> bool:
    if not text or not text.strip():
        return False

    normalized = " ".join(text.split()).strip()
    if len(normalized) <= 1:
        return False

    alpha_numeric_chars = [c for c in normalized if c.isalnum()]
    if len(alpha_numeric_chars) < 2:
        return False

    if normalized.lower() in {"?", "??", "???", "#####", "!!!", "..."}:
        return False

    if all(c in string.punctuation + string.whitespace for c in normalized):
        return False

    return True


def _extract_with_tesseract(image_path: Path) -> tuple[str, float | None]:
    try:
        image = Image.open(image_path)

        # Use a robust default configuration suitable for printed educational text
        custom_config = r'--oem 3 --psm 6'

        text = pytesseract.image_to_string(image, config=custom_config, lang="eng")
        avg_conf = None

        try:
            data = pytesseract.image_to_data(
                image,
                config=custom_config,
                lang="eng",
                output_type=pytesseract.Output.DICT,
            )
            confs = [int(v) for v in data.get("conf", []) if v and v != "-1"]
            avg_conf = sum(confs) / len(confs) if confs else None
            if avg_conf is not None:
                logger.debug("Tesseract avg confidence: %.1f", avg_conf)
        except Exception:
            pass

        return text or "", avg_conf

    except Exception as exc:
        raise OCRError(f"Tesseract extraction failed: {exc}") from exc

def _extract_with_preprocessing(image_path: Path) -> tuple[str, float | None]:
    """Extract text from preprocessed image (denoised, thresholded, etc)."""
    try:
        # Load image
        img = cv2.imread(str(image_path))
        if img is None:
            raise OCRPreprocessingError(f"Could not load image: {image_path}")
        # Log original size
        orig_h, orig_w = img.shape[:2]
        logger.debug("OCR original image size: %dx%d", orig_w, orig_h)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Denoise using a combination of median blur and fastNlMeans
        denoised = cv2.medianBlur(gray, 3)
        denoised = cv2.fastNlMeansDenoising(denoised, h=8)

        # Increase contrast with CLAHE
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Detect if text is light on dark and invert if necessary
        mean_intensity = int(np.mean(enhanced))
        if mean_intensity < 127:
            enhanced = cv2.bitwise_not(enhanced)

        # Adaptive thresholding with block size scaled to image size
        block_size = 15 if max(orig_w, orig_h) > 1000 else 11
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            2,
        )

        # Morphological cleaning
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)

        # Resize small images to improve OCR on small text
        target_width = 1600
        if orig_w < target_width:
            scale = target_width / orig_w
            cleaned = cv2.resize(cleaned, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        proc_h, proc_w = cleaned.shape[:2]
        logger.debug("OCR processed image size: %dx%d", proc_w, proc_h)

        # Save preprocessed image temporarily
        temp_preprocessed = str(image_path.parent / f"_preprocessed_{image_path.name}")
        cv2.imwrite(temp_preprocessed, cleaned)

        try:
            pil_image = Image.open(temp_preprocessed)
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(pil_image, config=custom_config, lang="eng")
            avg_conf = None

            try:
                data = pytesseract.image_to_data(
                    pil_image,
                    config=custom_config,
                    lang="eng",
                    output_type=pytesseract.Output.DICT,
                )
                confs = [int(v) for v in data.get("conf", []) if v and v != "-1"]
                avg_conf = sum(confs) / len(confs) if confs else None
                if avg_conf is not None:
                    logger.debug("Preprocessed OCR avg confidence: %.1f", avg_conf)
            except Exception:
                pass

            return text or "", avg_conf
        finally:
            try:
                os.remove(temp_preprocessed)
            except Exception:
                pass

    except OCRPreprocessingError:
        raise
    except Exception as exc:
        raise OCRPreprocessingError(f"Preprocessing failed: {exc}") from exc


def _extract_with_gemini_vision(image_path: Path) -> str:
    """Extract text from image using Gemini Vision API as fallback."""
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
    except Exception as exc:
        raise GeminiAPIError(f"Could not read image file: {exc}") from exc
    
    import base64
    encoded_image = base64.b64encode(image_data).decode("utf-8")
    
    # Determine image type
    suffix = image_path.suffix.lower()
    if suffix in [".jpg", ".jpeg"]:
        media_type = "image/jpeg"
    elif suffix == ".png":
        media_type = "image/png"
    elif suffix == ".gif":
        media_type = "image/gif"
    elif suffix == ".webp":
        media_type = "image/webp"
    else:
        media_type = "image/jpeg"  # Default
    
    prompt = """
You are an OCR engine specialized in handwritten student notes.

Extract every visible word from the image.

Requirements:
- Preserve headings.
- Preserve bullet points.
- Preserve numbered lists.
- Preserve equations and formulas.
- Preserve line breaks.
- Do not summarize.
- Do not explain.
- Do not correct grammar.
- Return only the extracted text.


Even if handwriting is messy, make the most likely interpretation.
"""

    try:
        from google.genai import types
        from services.gemini_service import _get_client, _get_model_name, _extract_response_text
        
        client = _get_client()
        
        # Use Vision API with inline image
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
        print("GEMINI OCR OUTPUT:")
        print(_extract_response_text(response))
        return _extract_response_text(response)
    except Exception as exc:
        raise GeminiAPIError(f"Gemini Vision extraction failed: {exc}") from exc
