"""
Tests for Screenshot OCR Analysis Engine
"""

import io
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

from app import app
from ocr_analyzer import OCRScanner


def create_synthetic_image(format_name: str = "PNG", size=(200, 100), color="white") -> bytes:
    """Helper to generate an in-memory image buffer without disk persistence."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


def test_validate_image_valid_png():
    scanner = OCRScanner()
    png_bytes = create_synthetic_image("PNG")
    mime, w, h = scanner.validate_image(png_bytes)
    assert mime == "image/png"
    assert w == 200
    assert h == 100


def test_validate_image_valid_jpeg():
    scanner = OCRScanner()
    jpeg_bytes = create_synthetic_image("JPEG")
    mime, w, h = scanner.validate_image(jpeg_bytes)
    assert mime == "image/jpeg"
    assert w == 200
    assert h == 100


def test_validate_image_empty_bytes():
    scanner = OCRScanner()
    with pytest.raises(ValueError, match="No image data provided"):
        scanner.validate_image(b"")


def test_validate_image_non_image_corrupted():
    scanner = OCRScanner()
    with pytest.raises(ValueError, match="not a valid image"):
        scanner.validate_image(b"This is a text file posing as an image.")


def test_validate_image_dimensions_too_small():
    scanner = OCRScanner()
    tiny_bytes = create_synthetic_image("PNG", size=(4, 4))
    with pytest.raises(ValueError, match="dimensions are too small"):
        scanner.validate_image(tiny_bytes)


def test_validate_image_exceeds_max_size():
    scanner = OCRScanner()
    huge_bytes = b"0" * (11 * 1024 * 1024)
    with pytest.raises(ValueError, match="exceeds the 10 MB size limit"):
        scanner.validate_image(huge_bytes)


def test_process_screenshot_routes_to_pipeline():
    scanner = OCRScanner()
    png_bytes = create_synthetic_image("PNG")

    scam_text = "URGENT: Your bank account is locked! Click to enter your otp now."

    with patch.object(scanner, "extract_text", return_value=(scam_text, "gemini_vision")):
        result = scanner.process_screenshot(png_bytes, filename="chat_screenshot.png")

        assert result["is_screenshot"] is True
        assert result["extracted_text"] == scam_text
        assert result["ocr_source"] == "gemini_vision"
        assert result["filename"] == "chat_screenshot.png"
        assert result["risk"] == "High Risk"
        assert result["score"] == 90
        assert "otp" in result["detected"]


def test_process_screenshot_with_suspicious_url_defangs_target():
    scanner = OCRScanner()
    png_bytes = create_synthetic_image("PNG")

    message_with_url = "Verify your account at http://192.168.1.1/login immediately."

    with patch.object(scanner, "extract_text", return_value=(message_with_url, "gemini_vision")):
        result = scanner.process_screenshot(png_bytes, filename="sms.png")

        assert result["risk"] == "High Risk"
        assert result["url_analysis"]["has_urls"] is True
        details = result["url_analysis"]["details"]
        assert len(details) == 1
        assert details[0]["defanged_url"] == "hxxp://192[.]168[.]1[.]1/login"
        assert "http://" not in details[0]["defanged_url"]


def test_process_screenshot_empty_text_raises_error():
    scanner = OCRScanner()
    png_bytes = create_synthetic_image("PNG")

    with patch.object(scanner, "extract_text", return_value=("   ", "gemini_vision")):
        with pytest.raises(ValueError, match="No readable text could be detected"):
            scanner.process_screenshot(png_bytes)


# ============================================================================
# Flask Endpoint Tests: POST /analyze-screenshot
# ============================================================================

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_analyze_screenshot_endpoint_no_file(client):
    response = client.post("/analyze-screenshot", data={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_analyze_screenshot_endpoint_non_image_file(client):
    data = {
        "screenshot": (io.BytesIO(b"random plain text"), "test.txt")
    }
    response = client.post("/analyze-screenshot", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    data = response.get_json()
    assert "not a valid image" in data["error"]


def test_analyze_screenshot_endpoint_success(client):
    img_bytes = create_synthetic_image("PNG")
    mock_scam = "Winner! You won a prize lottery. Send money now."

    with patch("app.ocr_scanner.extract_text", return_value=(mock_scam, "gemini_vision")):
        data = {
            "screenshot": (io.BytesIO(img_bytes), "screenshot.png")
        }
        response = client.post("/analyze-screenshot", data=data, content_type="multipart/form-data")
        assert response.status_code == 200
        res = response.get_json()
        assert res["is_screenshot"] is True
        assert res["extracted_text"] == mock_scam
        assert res["risk"] == "High Risk"
        assert res["score"] == 90
        assert "prize" in res["detected"]
