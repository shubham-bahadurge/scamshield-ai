"""Production readiness regression tests."""
import pytest
from analyzer import AIScamAnalyzer
from app import app


def test_legacy_gemini_environment_variable_is_supported(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("shubham12", "test-secret-not-a-real-key")
    analyzer = AIScamAnalyzer()
    assert analyzer.api_key == "test-secret-not-a-real-key"
    assert analyzer.is_available() is True


def test_documented_gemini_environment_variable_takes_precedence(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "documented-key")
    monkeypatch.setenv("shubham12", "legacy-key")
    analyzer = AIScamAnalyzer()
    assert analyzer.api_key == "documented-key"


def test_health_endpoint_does_not_expose_secret(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "do-not-leak-this")
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["gemini_configured"] is True
    assert "do-not-leak-this" not in response.get_data(as_text=True)


def test_health_endpoint_works_without_gemini_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("shubham12", raising=False)
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["gemini_configured"] is False
