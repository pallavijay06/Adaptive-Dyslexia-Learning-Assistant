# services/ocr_service.py
"""OCR service with image preprocessing and Gemini Vision fallback.

Supports:
- Printed text extraction (Tesseract)
- Scanned PDFs (preprocessing + Tesseract)
- Handwritten notes (attempts with preprocessing)
- Gemini Vision API fallback when OCR quality is poor
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from urllib import response

import cv2
import numpy as np
from PIL import Image, ImageOps
import pytesseract

from services.gemini_service import GeminiAPIError, GeminiConfigurationError


class OCRError(RuntimeError):
    """Base error for OCR service failures."""


class OCRPreprocessingError(OCRError):
    """Raised when image preprocessing fails."""


def extract_text_from_image(image_path: str) -> str:
    image_path = Path(image_path)

    if not image_path.exists():
        raise OCRError(f"Image file not found: {image_path}")

    try:
        # Try Gemini Vision first
        text = _extract_with_gemini_vision(image_path)

        if text and len(text.strip()) > 10:
            return text

    except Exception as e:
        print(f"Gemini OCR failed: {e}")

    # Fallback to traditional OCR
    try:
        text = _extract_with_preprocessing(image_path)

        if text:
            return text

    except Exception:
        pass

    return ""


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
    

def _extract_with_tesseract(image_path: Path) -> str:
    try:
        image = Image.open(image_path)

        # Use a robust default configuration suitable for printed educational text
        custom_config = r'--oem 3 --psm 6'

        text = pytesseract.image_to_string(image, config=custom_config, lang="eng")

        # Try to obtain an average confidence where possible
        try:
            data = pytesseract.image_to_data(image, config=custom_config, lang="eng", output_type=pytesseract.Output.DICT)
            confs = [int(v) for v in data.get('conf', []) if v and v != '-1']
            avg_conf = sum(confs) / len(confs) if confs else None
            if avg_conf is not None:
                print(f"Tesseract avg confidence: {avg_conf:.1f}")
        except Exception:
            pass

        return text or ""

    except Exception as exc:
        raise OCRError(f"Tesseract extraction failed: {exc}") from exc

def _extract_with_preprocessing(image_path: Path) -> str:
    """Extract text from preprocessed image (denoised, thresholded, etc)."""
    try:
        # Load image
        img = cv2.imread(str(image_path))
        if img is None:
            raise OCRPreprocessingError(f"Could not load image: {image_path}")
        # Log original size
        orig_h, orig_w = img.shape[:2]
        print(f"OCR original image size: {orig_w}x{orig_h}")

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
            # dark background -> likely light text; invert to get dark text
            enhanced = cv2.bitwise_not(enhanced)

        # Adaptive thresholding with block size scaled to image size
        block_size = 15 if max(orig_w, orig_h) > 1000 else 11
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            2
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
        print(f"OCR processed image size: {proc_w}x{proc_h}")

        # Save preprocessed image temporarily
        temp_preprocessed = str(image_path.parent / f"_preprocessed_{image_path.name}")
        cv2.imwrite(temp_preprocessed, cleaned)

        try:
            # Extract text from preprocessed image using Tesseract and gather confidences
            pil_image = Image.open(temp_preprocessed)
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(pil_image, config=custom_config, lang="eng")

            try:
                data = pytesseract.image_to_data(pil_image, config=custom_config, lang="eng", output_type=pytesseract.Output.DICT)
                confs = [int(v) for v in data.get('conf', []) if v and v != '-1']
                avg_conf = sum(confs) / len(confs) if confs else None
                if avg_conf is not None:
                    print(f"Preprocessed OCR avg confidence: {avg_conf:.1f}")
            except Exception:
                pass

            return text or ""
        finally:
            # Clean up temp file
            try:
                os.remove(temp_preprocessed)
            except:
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
