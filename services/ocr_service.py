# services/ocr_service.py
"""OCR service with image preprocessing and Gemini Vision fallback.

Supports:
- Printed text extraction (Tesseract)
- Scanned PDFs (preprocessing + Tesseract)
- Handwritten notes (attempts with preprocessing)
- Gemini Vision API fallback when OCR quality is poor
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from services.gemini_service import GeminiAPIError, GeminiConfigurationError


class OCRError(RuntimeError):
    """Base error for OCR service failures."""


class OCRPreprocessingError(OCRError):
    """Raised when image preprocessing fails."""


def extract_text_from_image(image_path: str) -> str:
    """Extract text from an image using OCR with preprocessing and AI fallback.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Extracted text
        
    Raises:
        OCRError: If extraction fails
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise OCRError(f"Image file not found: {image_path}")
    
    try:
        # Try direct OCR first
        text = _extract_with_tesseract(image_path)
        
        # Check if text extraction was successful (more than just whitespace)
        if text and text.strip():
            # Quality check - if text seems very short relative to image, try with preprocessing
            if len(text.strip()) < 50:
                try:
                    preprocessed_text = _extract_with_preprocessing(image_path)
                    if len(preprocessed_text.strip()) > len(text.strip()):
                        text = preprocessed_text
                except OCRPreprocessingError:
                    pass  # Fall back to original text
        
        # If OCR quality is poor, try Gemini Vision API
        if not text or len(text.strip()) < 20:
            try:
                text = _extract_with_gemini_vision(image_path)
            except (GeminiAPIError, GeminiConfigurationError) as exc:
                # If Gemini also fails and we have some text, return it
                if text and text.strip():
                    return text
                raise OCRError(f"Both Tesseract and Gemini Vision failed: {exc}") from exc
        
        return text or ""
    
    except OCRError:
        raise
    except Exception as exc:
        raise OCRError(f"Unexpected error during OCR: {exc}") from exc


def extract_text_from_pdf_images(pdf_path: str) -> str:
    """Extract text from scanned PDF by converting pages to images and running OCR.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Concatenated text from all pages
        
    Raises:
        OCRError: If PDF processing fails
    """
    try:
        import pdf2image
    except ImportError:
        raise OCRError(
            "pdf2image is not installed. Run: pip install pdf2image"
        )
    
    try:
        images = pdf2image.convert_from_path(pdf_path)
        all_text = []
        
        for page_num, image in enumerate(images, 1):
            try:
                temp_image_path = f"/tmp/pdf_page_{page_num}.png"
                image.save(temp_image_path)
                page_text = extract_text_from_image(temp_image_path)
                if page_text:
                    all_text.append(page_text)
                # Clean up temp file
                try:
                    os.remove(temp_image_path)
                except:
                    pass
            except Exception as exc:
                raise OCRError(f"Failed to process page {page_num}: {exc}") from exc
        
        return "\n\n---PAGE BREAK---\n\n".join(all_text)
    
    except OCRError:
        raise
    except Exception as exc:
        raise OCRError(f"PDF to image conversion failed: {exc}") from exc


def _extract_with_tesseract(image_path: Path) -> str:
    """Extract text directly using Tesseract OCR."""
    try:
        import pytesseract
    except ImportError:
        raise OCRError("pytesseract is not installed. Run: pip install pytesseract")
    
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
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
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) for better contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        
        # Apply adaptive thresholding (better for varying lighting conditions)
        binary = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
        
        # Morph operations to clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Save preprocessed image temporarily
        temp_preprocessed = str(image_path.parent / f"_preprocessed_{image_path.name}")
        cv2.imwrite(temp_preprocessed, cleaned)
        
        try:
            # Extract text from preprocessed image
            import pytesseract
            pil_image = Image.open(temp_preprocessed)
            text = pytesseract.image_to_string(pil_image)
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
    
    prompt = (
        "Extract ALL text from this image. "
        "Return only the extracted text, nothing else. "
        "Preserve formatting and structure as much as possible."
    )
    
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
        
        return _extract_response_text(response)
    except Exception as exc:
        raise GeminiAPIError(f"Gemini Vision extraction failed: {exc}") from exc
