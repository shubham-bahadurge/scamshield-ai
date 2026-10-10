import os
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from analyzer import ScamDetector
from ocr_analyzer import OCRScanner
from incident_response import build_response_plan

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Leave room for multipart form overhead while enforcing the OCR module's 10 MB image cap.
app.config["MAX_CONTENT_LENGTH"] = 11 * 1024 * 1024

# Initialize the scam detector (AI-powered with automatic rule-based fallback)
detector = ScamDetector()

# Initialize the in-memory screenshot OCR scanner
ocr_scanner = OCRScanner(detector=detector)


@app.route("/health", methods=["GET"])
def health():
    """Minimal deployment health check; never exposes secrets or their values."""
    ai_configured = detector.ai_analyzer.is_available()
    return jsonify({
        "status": "ok",
        "message_analysis": "available",
        "url_analysis": "available",
        "incident_response": "available",
        "gemini_configured": ai_configured,
        "screenshot_ocr": "gemini_or_local_fallback" if ai_configured else "requires_gemini_key_or_local_tesseract",
    }), 200


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "error": "Invalid request. JSON payload expected."
        }), 400

    message = data.get("message", "").strip()

    if not message:
        return jsonify({
            "error": "Please enter a message to analyze."
        }), 400

    try:
        result = detector.analyze(message)
        return jsonify(result), 200
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except Exception as err:
        app.logger.exception(f"Unexpected error during analysis: {err}")
        return jsonify({
            "error": "An internal error occurred while analyzing the message."
        }), 500


@app.route("/analyze-screenshot", methods=["POST"])
def analyze_screenshot():
    if "screenshot" not in request.files and "image" not in request.files:
        return jsonify({
            "error": "No screenshot uploaded. Please select, drop, or paste an image file."
        }), 400

    file = request.files.get("screenshot") or request.files.get("image")
    if not file or not file.filename:
        return jsonify({
            "error": "No file selected. Please choose a screenshot image."
        }), 400

    try:
        image_bytes = file.read()
        result = ocr_scanner.process_screenshot(image_bytes, filename=file.filename)
        return jsonify(result), 200
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except RuntimeError as rt_err:
        return jsonify({"error": str(rt_err)}), 400
    except Exception as err:
        app.logger.exception(f"Unexpected error during screenshot OCR analysis: {err}")
        return jsonify({
            "error": "An internal error occurred while processing the screenshot."
        }), 500


@app.route("/incident-response", methods=["POST"])
def incident_response():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request. JSON payload expected."}), 400

    scenario = data.get("scenario")
    if not isinstance(scenario, str):
        return jsonify({"error": "Choose what happened so we can prepare a response plan."}), 400

    try:
        return jsonify(build_response_plan(scenario)), 200
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    except Exception:
        app.logger.exception("Unexpected error while building incident response plan")
        return jsonify({"error": "Unable to build the response plan right now."}), 500


if __name__ == "__main__":
    # Debug mode is opt-in; never enable Flask's debugger by default.
    debug_mode = os.getenv("FLASK_DEBUG", "False").strip().lower() in ("true", "1", "t")
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=debug_mode, port=port)