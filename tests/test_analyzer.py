"""
Test Suite for ScamShield AI
============================
Covers:
1. Rule-based heuristic analyzer (original logic preservation).
2. AI prompt generation and response parsing.
3. Fallback behavior when AI fails, API key is absent, or output is invalid.
4. Flask /analyze route integration and error handling.
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from analyzer import AIScamAnalyzer, RuleBasedAnalyzer, ScamDetector, DEFAULT_SCAM_WORDS
from app import app


# ============================================================================
# 1. Tests for RuleBasedAnalyzer
# ============================================================================

def test_rule_based_low_risk_no_keywords():
    analyzer = RuleBasedAnalyzer()
    result = analyzer.analyze("Hey, are we still meeting for lunch tomorrow?")
    assert result["risk"] == "Low Risk"
    assert result["score"] == 15
    assert result["detected"] == []
    assert result["source"] == "rule_based"
    assert len(result["recommendations"]) > 0
    assert "explanation" in result


def test_rule_based_suspicious_single_keyword():
    analyzer = RuleBasedAnalyzer()
    result = analyzer.analyze("This is urgent, please call me back.")
    assert result["risk"] == "Suspicious"
    assert result["score"] == 60
    assert "urgent" in result["detected"]
    assert result["source"] == "rule_based"


def test_rule_based_suspicious_two_keywords():
    analyzer = RuleBasedAnalyzer()
    result = analyzer.analyze("Please click the link to claim your prize.")
    assert result["risk"] == "Suspicious"
    assert result["score"] == 60
    assert "click" in result["detected"]
    assert "prize" in result["detected"]


def test_rule_based_high_risk_three_or_more_keywords():
    analyzer = RuleBasedAnalyzer()
    result = analyzer.analyze(
        "Urgent! You are a lottery winner! Click here to share your otp to verify your account."
    )
    assert result["risk"] == "High Risk"
    assert result["score"] == 90
    assert len(result["detected"]) >= 3
    assert result["source"] == "rule_based"
    assert "otp" in result["detected"]
    assert "urgent" in result["detected"]


def test_rule_based_case_insensitive():
    analyzer = RuleBasedAnalyzer()
    result = analyzer.analyze("ENTER YOUR OTP NOW TO ACCESS YOUR BANK ACCOUNT")
    assert result["risk"] == "Suspicious"
    assert "otp" in result["detected"]
    assert "bank account" in result["detected"]


def test_rule_based_all_keywords_recognized():
    analyzer = RuleBasedAnalyzer()
    for word in DEFAULT_SCAM_WORDS:
        res = analyzer.analyze(f"Test message with {word} included")
        assert word in res["detected"], f"Keyword '{word}' was not detected"


# ============================================================================
# 2. Tests for AIScamAnalyzer Prompt & Parsing
# ============================================================================

def test_ai_build_prompt_contains_message():
    analyzer = AIScamAnalyzer(api_key="dummy_key")
    prompt = analyzer.build_prompt("Verify your account immediately")
    assert "Verify your account immediately" in prompt
    assert "ScamShield AI" in prompt
    assert "JSON" in prompt


def test_ai_parse_valid_json():
    analyzer = AIScamAnalyzer(api_key="test_key")
    sample_json = json.dumps({
        "risk": "High Risk",
        "score": 95,
        "category": "Banking Phishing",
        "detected": ["Fake bank URL", "Urgent deadline threat", "Requests debit PIN"],
        "explanation": "This message impersonates a bank to steal your card credentials.",
        "recommendations": [
            "Do not click the link.",
            "Contact your bank directly."
        ]
    })

    result = analyzer.parse_ai_response(sample_json)
    assert result["risk"] == "High Risk"
    assert result["score"] == 95
    assert result["category"] == "Banking Phishing"
    assert len(result["detected"]) == 3
    assert len(result["recommendations"]) == 2
    assert result["source"] == "ai"
    assert result["message"] == "Analysis completed successfully."


def test_ai_parse_markdown_wrapped_json():
    analyzer = AIScamAnalyzer(api_key="test_key")
    markdown_json = """```json
    {
        "risk": "Low Risk",
        "score": 10,
        "category": "Legitimate",
        "detected": [],
        "explanation": "Normal conversation.",
        "recommendations": ["No action required."]
    }
    ```"""

    result = analyzer.parse_ai_response(markdown_json)
    assert result["risk"] == "Low Risk"
    assert result["score"] == 10
    assert result["source"] == "ai"


def test_ai_parse_clamps_invalid_scores():
    analyzer = AIScamAnalyzer(api_key="test_key")
    data = json.dumps({
        "risk": "High Risk",
        "score": 150,
        "category": "Scam",
        "detected": ["Suspicious link"],
        "explanation": "Danger.",
        "recommendations": ["Avoid."]
    })
    result = analyzer.parse_ai_response(data)
    assert result["score"] == 100

    data_neg = json.dumps({
        "risk": "Low Risk",
        "score": -20,
        "category": "Safe",
        "detected": [],
        "explanation": "Safe.",
        "recommendations": []
    })
    result_neg = analyzer.parse_ai_response(data_neg)
    assert result_neg["score"] == 0


def test_ai_parse_infers_risk_if_unrecognized():
    analyzer = AIScamAnalyzer(api_key="test_key")
    data = json.dumps({
        "risk": "UNKNOWN_RISK",
        "score": 85,
        "category": "Threat",
        "detected": ["Phishing link"],
        "explanation": "High threat detected.",
        "recommendations": ["Block sender."]
    })
    result = analyzer.parse_ai_response(data)
    assert result["risk"] == "High Risk"


def test_ai_parse_malformed_json_raises_error():
    analyzer = AIScamAnalyzer(api_key="test_key")
    with pytest.raises(Exception):
        analyzer.parse_ai_response("This is definitely not JSON.")


# ============================================================================
# 3. Tests for ScamDetector Fallback Behavior
# ============================================================================

def test_detector_fallback_when_api_key_missing():
    ai = AIScamAnalyzer(api_key="")
    detector = ScamDetector(ai_analyzer=ai)

    result = detector.analyze("Your bank account needs verification, urgent!")
    assert result["source"] == "rule_based"
    assert result["fallback_triggered"] is False
    assert result["risk"] == "Suspicious"


def test_detector_fallback_when_ai_raises_exception():
    mock_ai = MagicMock(spec=AIScamAnalyzer)
    mock_ai.is_available.return_value = True
    mock_ai.analyze.side_effect = RuntimeError("Network connection timed out")

    detector = ScamDetector(ai_analyzer=mock_ai)
    result = detector.analyze("Urgent click winner prize!")

    assert result["source"] == "rule_based"
    assert result["fallback_triggered"] is True
    assert "AI unavailable" in result["fallback_reason"]
    assert result["risk"] == "High Risk"
    assert result["score"] == 90


def test_detector_fallback_when_ai_returns_invalid_json():
    mock_ai = MagicMock(spec=AIScamAnalyzer)
    mock_ai.is_available.return_value = True
    mock_ai.analyze.side_effect = ValueError("AI output is not a JSON object")

    detector = ScamDetector(ai_analyzer=mock_ai)
    result = detector.analyze("Urgent action required on your account")

    assert result["source"] == "rule_based"
    assert result["fallback_triggered"] is True
    assert result["risk"] == "Suspicious"


def test_detector_uses_ai_when_available_and_healthy():
    mock_ai = MagicMock(spec=AIScamAnalyzer)
    mock_ai.is_available.return_value = True
    mock_ai.analyze.return_value = {
        "risk": "High Risk",
        "score": 88,
        "category": "Crypto Scam",
        "detected": ["Guaranteed returns promise"],
        "explanation": "Crypto scheme with unrealistic yield.",
        "recommendations": ["Never send crypto to unknown wallets."],
        "source": "ai",
        "message": "Analysis completed successfully."
    }

    detector = ScamDetector(ai_analyzer=mock_ai)
    result = detector.analyze("Send 1 ETH to double your money immediately!")

    assert result["source"] == "ai"
    assert result["score"] == 88
    assert result["fallback_triggered"] is False
    mock_ai.analyze.assert_called_once()


def test_detector_empty_message_raises_value_error():
    detector = ScamDetector()
    with pytest.raises(ValueError):
        detector.analyze("")
    with pytest.raises(ValueError):
        detector.analyze("    ")


# ============================================================================
# 4. Tests for Flask Application Routes
# ============================================================================

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_home_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ScamShield AI" in response.data
    assert b"Check a suspicious message" in response.data


def test_analyze_route_empty_body(client):
    response = client.post("/analyze", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_analyze_route_blank_message(client):
    response = client.post("/analyze", json={"message": "   "})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_analyze_route_non_json_payload(client):
    response = client.post("/analyze", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_analyze_route_valid_message_preserves_contract(client):
    response = client.post(
        "/analyze",
        json={"message": "Your lottery prize is waiting. Click to get your otp."}
    )
    assert response.status_code == 200
    data = response.get_json()

    # Preserves existing expected keys
    assert "risk" in data
    assert "score" in data
    assert "detected" in data
    assert "message" in data

    # Enhanced keys
    assert "recommendations" in data
    assert "explanation" in data
    assert "category" in data
    assert "source" in data

    # Data types
    assert isinstance(data["risk"], str)
    assert isinstance(data["score"], int)
    assert isinstance(data["detected"], list)
    assert isinstance(data["recommendations"], list)


def test_analyze_route_handles_unexpected_exception(client):
    with patch("app.detector.analyze", side_effect=Exception("Database crash")):
        response = client.post("/analyze", json={"message": "Hello"})
        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data


# ============================================================================
# 5. Tests for URL Integration into Risk Assessment
# ============================================================================

def test_critical_url_elevates_risk_without_scam_words():
    # Message text contains zero scam keywords, but points to raw IP host
    detector = ScamDetector()
    result = detector.analyze("Please review document at http://192.168.1.100/login")
    assert result["risk"] == "High Risk"
    assert result["score"] >= 85
    assert result["url_analysis"]["has_urls"] is True
    assert any("Raw IP-address" in flag for flag in result["detected"])


def test_benign_url_keeps_low_risk():
    # Message with legitimate trusted link remains low risk
    detector = ScamDetector()
    result = detector.analyze("Here is the documentation: https://www.google.com")
    assert result["risk"] == "Low Risk"
    assert result["score"] <= 20
    assert result["url_analysis"]["has_urls"] is True
    assert result["url_analysis"]["overall_url_risk"] == "Low Risk"


def test_message_without_url_preserves_has_urls_false():
    detector = ScamDetector()
    result = detector.analyze("Good morning team, let us start our standup.")
    assert result["url_analysis"]["has_urls"] is False
    assert result["url_analysis"]["urls_count"] == 0
    assert result["risk"] == "Low Risk"


# ============================================================================
# 6. Tests for Scan History Data Contract & Secret Non-Leakage
# ============================================================================

def test_home_page_contains_history_elements(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"history-section" in response.data
    assert b"history-list" in response.data
    assert b"clear-history-btn" in response.data
    assert b"history-empty" in response.data


def test_analyze_payload_contains_all_history_fields_and_no_secrets(client):
    response = client.post(
        "/analyze",
        json={"message": "URGENT: your bank account is locked, click http://192.168.1.1/login to enter OTP"}
    )
    assert response.status_code == 200
    data = response.get_json()

    # All fields required by saveScanToHistory must be present
    required_history_fields = [
        "risk", "score", "category", "detected", "explanation",
        "recommendations", "source", "url_analysis"
    ]
    for field in required_history_fields:
        assert field in data, f"Missing required history field: {field}"

    # Confirm secrets are never attached to response payload
    payload_str = json.dumps(data).lower()
    assert "api_key" not in payload_str
    assert "gemini_api_key" not in payload_str
    assert "secret" not in payload_str



# ============================================================================
# 7. Privacy-First Incident Response Copilot
# ============================================================================
def test_incident_response_received_scenario(client):
    response = client.post("/incident-response", json={"scenario": "received"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["scenario"] == "received"
    assert len(data["steps"]) >= 3
    assert "not saved" in data["privacy"]


def test_incident_response_money_loss_includes_official_india_channels(client):
    response = client.post("/incident-response", json={"scenario": "sent_money"})
    assert response.status_code == 200
    data = response.get_json()
    joined = " ".join(data["steps"]) + " " + data["report"]
    assert "1930" in joined
    assert "cybercrime.gov.in" in joined


def test_incident_response_rejects_unknown_scenario(client):
    response = client.post("/incident-response", json={"scenario": "give-me-admin-access"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_incident_response_rejects_non_json(client):
    response = client.post("/incident-response", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_home_page_contains_incident_response_copilot(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"SCAMSHIELD RESPONSE COPILOT" in response.data
    assert b"incident-scenario" in response.data
