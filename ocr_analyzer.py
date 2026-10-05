"""
ScamShield AI - Screenshot OCR Threat Analysis Engine
======================================================
Processes uploaded screenshots of suspicious SMS, WhatsApp, email,
and social media messages in-memory:
  - In-memory image validation (zero permanent disk storage)
  - Multimodal text extraction via Gemini 2.5 Flash Vision
  - Offline Tesseract fallback (if binary available)
  - Seamless ingestion into existing ScamDetector pipeline
  - Full URL detection, defanging, and risk scoring reuse
"""

import io
import logging
from typing import Any, Dict, Optional, Tuple
from PIL import Image

from analyzer import ScamDetector

logger = logging.getLogger(__name__)

# Maximum allowable image upload size (10 MB)
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024

# Allowed image formats and their MIME types
SUPPORTED_FORMATS: Dict[str, str] = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
    "GIF": "image/gif",
    "BMP": "image/bmp",
}


class OCRScanner:
    """
    In-memory image ingestion and OCR extraction engine.
    Extracts text from screenshots and routes directly into ScamDetector.
    """

    def __init__(self, detector: Optional[ScamDetector] = None) -> None:
        self.detector = detector or ScamDetector()

    def validate_image(self, image_bytes: bytes) -> Tuple[str, int, int]:
        """
        Validates image bytes in memory without writing to disk.
        Returns: (mime_type, width, height)
        Raises: ValueError if invalid, corrupted, or exceeds size limits.
        """
        if not image_bytes:
            raise ValueError("No image data provided. Please upload a valid screenshot.")

        if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
            raise ValueError("Image file exceeds the 10 MB size limit.")

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img_format = (img.format or "").upper()
                if img_format not in SUPPORTED_FORMATS:
                    raise ValueError(
                        f"Unsupported image format: {img_format or 'unknown'}. "
                        "Please upload a PNG, JPEG, or WEBP screenshot."
                    )

                width, height = img.size
                if width < 10 or height < 10:
                    raise ValueError("Image dimensions are too small to contain readable text.")

                mime_type = SUPPORTED_FORMATS[img_format]
                return mime_type, width, height

        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError("The uploaded file is corrupted or not a valid image.")

    def extract_text_with_gemini(self, image_bytes: bytes, mime_type: str) -> str:
        """
        Transcribe screenshot text using Gemini 2.5 Flash Vision.
        """
        ai = self.detector.ai_analyzer
        client = ai._get_client()
        if not client:
            raise RuntimeError("Gemini AI client is not available.")

        from google.genai import types

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        prompt = (
            "You are ScamShield AI, an expert cybersecurity OCR transcription engine.\n"
            "Extract all text, SMS messages, chat conversations, sender names, links, notifications, "
            "and phone numbers visible in this screenshot exactly as they appear.\n"
            "If the image contains NO readable text or is blank, respond ONLY with: NO_TEXT_FOUND\n"
            "Do not add conversational commentary, introductory text, or markdown quotes. "
            "Return only the raw extracted text."
        )

        response = client.models.generate_content(
            model=ai.model_name,
            contents=[prompt, image_part],
            config=types.GenerateContentConfig(
                temperature=0.0,
            ),
        )

        text = (getattr(response, "text", "") or "").strip()
        if not text or text == "NO_TEXT_FOUND":
            raise ValueError("No readable text could be detected in this screenshot.")

        return text

    def extract_text_with_tesseract(self, image_bytes: bytes) -> str:
        """
        Fallback local OCR using pytesseract if installed and binary present.
        """
        try:
            import pytesseract
            with Image.open(io.BytesIO(image_bytes)) as img:
                text = pytesseract.image_to_string(img).strip()
                if not text:
                    raise ValueError("No readable text could be detected in this screenshot.")
                return text
        except ImportError:
            raise RuntimeError("Local pytesseract module not installed.")
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise RuntimeError(f"Local Tesseract execution failed: {e}")

    def extract_text(self, image_bytes: bytes, mime_type: str) -> Tuple[str, str]:
        """
        Extract text using Gemini Vision if configured, falling back to local Tesseract.
        Returns: (extracted_text, engine_name)
        """
        # 1. Attempt Gemini Vision if key configured
        if self.detector.ai_analyzer.is_available():
            try:
                text = self.extract_text_with_gemini(image_bytes, mime_type)
                return text, "gemini_vision"
            except Exception as e:
                logger.warning(f"Gemini Vision extraction failed ({e}). Checking local OCR fallback.")

        # 2. Attempt local Tesseract fallback
        try:
            text = self.extract_text_with_tesseract(image_bytes)
            return text, "local_tesseract"
        except Exception:
            pass

        # 3. Neither engine succeeded
        raise RuntimeError(
            "Screenshot analysis requires either a configured GEMINI_API_KEY in .env "
            "or local Tesseract OCR installed. Please configure GEMINI_API_KEY or paste "
            "the message text directly into the text analyzer."
        )

    def process_screenshot(
        self,
        image_bytes: bytes,
        filename: str = "screenshot.png",
    ) -> Dict[str, Any]:
        """
        Full in-memory pipeline:
        1. Validates image bytes.
        2. Performs OCR text extraction.
        3. Routes extracted text into ScamDetector.analyze().
        4. Reuses full URL analysis, scoring, and recommendation matrix.
        """
        mime_type, width, height = self.validate_image(image_bytes)

        extracted_text, engine = self.extract_text(image_bytes, mime_type)
        if not extracted_text or not extracted_text.strip():
            raise ValueError("No readable text could be detected in this screenshot.")

        # Pass extracted text through the existing ScamShield pipeline
        analysis_result = self.detector.analyze(extracted_text)

        # Attach OCR telemetry
        analysis_result["extracted_text"] = extracted_text
        analysis_result["ocr_source"] = engine
        analysis_result["filename"] = filename
        analysis_result["image_dimensions"] = f"{width}x{height}"
        analysis_result["is_screenshot"] = True

        return analysis_result
