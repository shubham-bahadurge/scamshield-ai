"""
ScamShield AI - Detection Engine
================================
This module provides scam detection capabilities using:
1. URLAnalyzer: Static, zero-network lexical URL threat scanner.
2. RuleBasedAnalyzer: Local keyword matching and heuristics engine (original logic + URL telemetry).
3. AIScamAnalyzer: Advanced analysis powered by Google Gemini API.
4. ScamDetector: Unified orchestrator that attempts AI analysis and gracefully
   falls back to the rule-based engine whenever the API key is missing or fails.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from url_analyzer import URLAnalyzer

logger = logging.getLogger(__name__)


# Standard scam keywords preserved from the original application
DEFAULT_SCAM_WORDS: List[str] = [
    "otp",
    "urgent",
    "click",
    "winner",
    "prize",
    "lottery",
    "password",
    "verify your account",
    "send money",
    "bank account",
]


class RuleBasedAnalyzer:
    """
    Local heuristic analyzer that inspects messages for known scam keywords
    and static URL threats.
    Preserves 100% of the original scoring logic as a reliable offline fallback.
    """

    def __init__(
        self,
        scam_words: Optional[List[str]] = None,
        url_analyzer: Optional[URLAnalyzer] = None,
    ) -> None:
        self.scam_words = scam_words or list(DEFAULT_SCAM_WORDS)
        self.url_analyzer = url_analyzer or URLAnalyzer()

    def analyze(
        self,
        message: str,
        url_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a message using rule-based keyword detection and static URL analysis.
        Original scoring:
          - >= 3 keywords -> High Risk (score: 90)
          - >= 1 keywords -> Suspicious (score: 60)
          - 0 keywords    -> Low Risk    (score: 15)
        Integrated URL findings adjust score floor for high-risk URLs.
        """
        message_lower = (message or "").lower()

        detected = [word for word in self.scam_words if word in message_lower]

        if len(detected) >= 3:
            risk = "High Risk"
            score = 90
            category = "High Risk Phishing / Fraud Indicator"
            explanation = (
                f"Multiple high-risk scam triggers were detected ({', '.join(detected)}). "
                "This message exhibits strong characteristics of social engineering or financial fraud."
            )
            recommendations = [
                "Do not click any links, open attachments, or call phone numbers in the message.",
                "Never share OTPs, passwords, UPI PINs, or banking details under any circumstance.",
                "Block the sender and report the message as scam/phishing to your service provider.",
            ]
        elif len(detected) >= 1:
            risk = "Suspicious"
            score = 60
            category = "Suspicious Communication"
            explanation = (
                f"Suspicious keyword(s) detected: {', '.join(detected)}. "
                "Exercise caution and independently verify the sender before taking action."
            )
            recommendations = [
                "Verify the sender's identity through official independent channels (not numbers in the message).",
                "Do not share personal or confidential information.",
                "Avoid clicking unverified short links or downloading attachments.",
            ]
        else:
            risk = "Low Risk"
            score = 15
            category = "General / Low Risk"
            explanation = (
                "No standard scam keywords were detected in this message. "
                "The text appears generally safe based on offline heuristic rules."
            )
            recommendations = [
                "Always remain vigilant even when messages appear safe.",
                "Legitimate institutions will never ask for your password or OTP via text or email.",
            ]

        # -------------------------------------------------------------
        # Integrate Static URL Analysis (Zero-Network)
        # -------------------------------------------------------------
        if url_results is None:
            url_results = self.url_analyzer.analyze_message_urls(message)

        if url_results.get("has_urls"):
            max_url_score = url_results.get("max_url_score", 0)

            # Raise score if URL score exceeds text keyword score
            if max_url_score > score:
                score = max_url_score
                if score >= 70:
                    risk = "High Risk"
                elif score >= 35:
                    risk = "Suspicious"
                else:
                    risk = "Low Risk"

            # Merge detected URL flags into warning signs list
            for flag in url_results.get("detected_flags", []):
                if flag not in detected:
                    detected.append(flag)

            # Adjust category & explanation based on URL threat severity
            if url_results.get("overall_url_risk") == "High Risk":
                category = "High Risk Phishing / Malicious URL Target"
                explanation += (
                    f" Suspicious destination link detected ({url_results['details'][0]['defanged_url']})."
                )
                if "Do not click any links, open attachments, or call phone numbers in the message." not in recommendations:
                    recommendations.insert(0, "Do not click any links, open attachments, or call phone numbers in the message.")
            elif url_results.get("overall_url_risk") == "Suspicious" and risk == "Low Risk":
                risk = "Suspicious"
                category = "Suspicious Link / Unverified Target"
                if "Avoid clicking unverified short links or downloading attachments." not in recommendations:
                    recommendations.insert(0, "Avoid clicking unverified short links or downloading attachments.")

        return {
            "risk": risk,
            "score": score,
            "detected": detected,
            "category": category,
            "explanation": explanation,
            "recommendations": recommendations,
            "source": "rule_based",
            "message": "Analysis completed successfully.",
            "url_analysis": url_results,
        }


class AIScamAnalyzer:
    """
    AI-powered scam analyzer using Google Gemini.
    Provides semantic understanding, threat categorization, reasoning,
    and tailored safety recommendations.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        self._explicit_key = api_key is not None
        # Backward compatibility: an earlier Vercel setup stored the key under
        # the variable name "shubham12". Prefer the documented name first.
        self.api_key = api_key.strip() if api_key is not None else (
            os.getenv("GEMINI_API_KEY") or os.getenv("shubham12") or ""
        ).strip()
        self.model_name = (
            model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        ).strip()
        self.timeout_seconds = timeout_seconds
        self._client = None

    def is_available(self) -> bool:
        """Check if an API key is present."""
        if not self._explicit_key and not self.api_key:
            self.api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("shubham12") or "").strip()
        return bool(self.api_key and self.api_key != "your_gemini_api_key_here")

    def _get_client(self):
        """Lazy-initialize the Google GenAI client."""
        if not self.api_key:
            self.api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("shubham12") or "").strip()
        if self._client is None and self.is_available():
            try:
                from google import genai
                from google.genai import types

                self._client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(timeout=self.timeout_seconds),
                )
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI Client: {e}")
                self._client = None
        return self._client

    def build_prompt(
        self,
        message: str,
        url_results: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Construct the prompt instructing Gemini to return structured JSON."""
        url_context = ""
        if url_results and url_results.get("has_urls"):
            url_lines = [
                f"- Defanged URL: {d['defanged_url']} | Risk: {d['risk_level']} | Signals: {', '.join(d['flags']) if d['flags'] else 'None'}"
                for d in url_results.get("details", [])
            ]
            url_context = (
                "\nExtracted URLs (defanged for security):\n"
                + "\n".join(url_lines)
                + "\nEvaluate whether these URLs match credential harvesting, impersonation, or deceptive targets.\n"
            )

        return (
            "You are ScamShield AI, an expert cybersecurity and anti-fraud analyst.\n"
            "Analyze the following suspicious message to determine if it is a scam, phishing, "
            "financial fraud, impersonation, or benign communication.\n\n"
            f'Message:\n"""\n{message}\n"""\n'
            f"{url_context}\n"
            "Respond ONLY with a valid JSON object matching this exact format:\n"
            "{\n"
            '  "risk": "Low Risk" | "Suspicious" | "High Risk",\n'
            '  "score": <integer 0 to 100>,\n'
            '  "category": "<short scam classification e.g. Phishing / Banking Fraud / Legitimate>",\n'
            '  "detected": ["<warning sign or indicator 1>", "<warning sign 2>"],\n'
            '  "explanation": "<1-2 sentences explaining why this message is safe or dangerous>",\n'
            '  "recommendations": ["<actionable safety step 1>", "<actionable safety step 2>"]\n'
            "}\n"
        )

    def parse_ai_response(
        self,
        text: str,
        url_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Clean, parse, and validate the JSON payload returned by the AI.
        Ensures all expected fields exist and match allowable values.
        """
        cleaned = text.strip()
        # Remove Markdown code blocks if present (```json ... ```)
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        data = json.loads(cleaned)

        if not isinstance(data, dict):
            raise ValueError("AI output is not a JSON object")

        # Validate & normalize 'score'
        try:
            score = int(data.get("score", 50))
            score = max(0, min(100, score))
        except (ValueError, TypeError):
            score = 50

        # Validate & normalize 'risk'
        risk = str(data.get("risk", "")).strip()
        valid_risks = {"Low Risk", "Suspicious", "High Risk"}
        if risk not in valid_risks:
            if score >= 70:
                risk = "High Risk"
            elif score >= 40:
                risk = "Suspicious"
            else:
                risk = "Low Risk"

        # Validate 'detected' list
        detected = data.get("detected")
        if not isinstance(detected, list):
            detected = [str(detected)] if detected else []
        else:
            detected = [str(item) for item in detected if item]

        # Merge URL flags if not already present
        if url_results and url_results.get("has_urls"):
            for flag in url_results.get("detected_flags", []):
                if flag not in detected:
                    detected.append(flag)

        # Validate 'recommendations' list
        recommendations = data.get("recommendations")
        if not isinstance(recommendations, list):
            recommendations = [str(recommendations)] if recommendations else []
        else:
            recommendations = [str(item) for item in recommendations if item]

        # Validate category and explanation
        category = str(data.get("category") or "General Assessment").strip()
        explanation = str(
            data.get("explanation")
            or "Analysis completed by ScamShield AI detection model."
        ).strip()

        return {
            "risk": risk,
            "score": score,
            "detected": detected,
            "category": category,
            "explanation": explanation,
            "recommendations": recommendations,
            "source": "ai",
            "message": "Analysis completed successfully.",
            "url_analysis": url_results or {"has_urls": False, "urls_count": 0, "details": []},
        }

    def analyze(
        self,
        message: str,
        url_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call the Gemini API and return validated analysis."""
        client = self._get_client()
        if not client:
            raise RuntimeError("Gemini AI client is not available or API key is missing.")

        # Sanitize and limit input length to protect against prompt bloat
        truncated_message = message[:4000].strip()
        prompt = self.build_prompt(truncated_message, url_results=url_results)

        from google.genai import types

        response = client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        response_text = getattr(response, "text", "")
        if not response_text:
            raise ValueError("Empty response received from AI model.")

        return self.parse_ai_response(response_text, url_results=url_results)


class ScamDetector:
    """
    Unified Orchestrator:
    - Pre-scans message for URLs via zero-network static inspection.
    - Attempts AI-powered analysis first when an API key is available.
    - Automatically falls back to RuleBasedAnalyzer on missing key / error.
    - Attaches comprehensive URL intelligence to every response.
    """

    def __init__(
        self,
        ai_analyzer: Optional[AIScamAnalyzer] = None,
        rule_analyzer: Optional[RuleBasedAnalyzer] = None,
        url_analyzer: Optional[URLAnalyzer] = None,
    ) -> None:
        self.url_analyzer = url_analyzer or URLAnalyzer()
        self.ai_analyzer = ai_analyzer or AIScamAnalyzer()
        self.rule_analyzer = rule_analyzer or RuleBasedAnalyzer(url_analyzer=self.url_analyzer)

    def analyze(self, message: str) -> Dict[str, Any]:
        """
        Analyze the given message with AI if available, falling back to rule engine.
        Includes zero-network static URL inspection.
        """
        clean_message = (message or "").strip()
        if not clean_message:
            raise ValueError("Please enter a message to analyze.")

        # 1. Zero-Network Static URL Extraction & Lexical Scan
        url_results = self.url_analyzer.analyze_message_urls(clean_message)

        # 2. Attempt AI analysis if configured
        if self.ai_analyzer.is_available():
            try:
                result = self.ai_analyzer.analyze(clean_message, url_results=url_results)
                result["fallback_triggered"] = False
                result["url_analysis"] = url_results
                return result
            except Exception as e:
                logger.warning(
                    f"AI analysis failed ({type(e).__name__}: {e}). "
                    "Engaging rule-based fallback analyzer."
                )
                # Fall through to rule-based fallback
                fallback_result = self.rule_analyzer.analyze(clean_message, url_results=url_results)
                fallback_result["fallback_triggered"] = True
                fallback_result["fallback_reason"] = (
                    f"AI unavailable ({type(e).__name__}). Used rule-based fallback."
                )
                fallback_result["url_analysis"] = url_results
                return fallback_result

        # 3. API key is not configured -> Use rule-based analyzer directly
        fallback_result = self.rule_analyzer.analyze(clean_message, url_results=url_results)
        fallback_result["fallback_triggered"] = False
        fallback_result["url_analysis"] = url_results
        return fallback_result
