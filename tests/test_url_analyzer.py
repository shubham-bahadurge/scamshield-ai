"""
Tests for URLAnalyzer (Static, Zero-Network URL Inspection)
"""

import pytest
from url_analyzer import URLAnalyzer


def test_extract_urls():
    text = "Visit https://example.com and check http://test.org/page. Also see www.mybank.net/login."
    urls = URLAnalyzer.extract_urls(text)
    assert len(urls) == 3
    assert "https://example.com" in urls
    assert "http://test.org/page" in urls
    assert "www.mybank.net/login" in urls


def test_extract_urls_strips_trailing_punctuation():
    text = "Go to https://bank.com/login, or read https://help.org/faq. Is this safe (https://secure.net)?"
    urls = URLAnalyzer.extract_urls(text)
    assert "https://bank.com/login" in urls
    assert "https://help.org/faq" in urls
    assert "https://secure.net" in urls


def test_extract_no_urls():
    text = "Hello Shubham, let's meet at 5 PM for dinner."
    urls = URLAnalyzer.extract_urls(text)
    assert urls == []


def test_defang_url():
    assert URLAnalyzer.defang_url("http://evil.com/phish") == "hxxp://evil[.]com/phish"
    assert URLAnalyzer.defang_url("https://bank.xyz/login") == "hxxps://bank[.]xyz/login"
    assert URLAnalyzer.defang_url("") == ""


def test_critical_ip_address_host():
    result = URLAnalyzer.analyze_single_url("http://192.168.1.1/login")
    assert result["risk_level"] == "High Risk"
    assert result["score"] >= 85
    assert any("Raw IP-address" in f for f in result["flags"])


def test_critical_userinfo_spoofing():
    result = URLAnalyzer.analyze_single_url("https://paypal.com@attacker-site.com/auth")
    assert result["risk_level"] == "High Risk"
    assert result["score"] >= 90
    assert any("Userinfo '@' spoofing" in f for f in result["flags"])


def test_critical_subdomain_brand_impersonation():
    result = URLAnalyzer.analyze_single_url("https://paypal.com.account-update.xyz/verify")
    assert result["risk_level"] == "High Risk"
    assert result["score"] >= 85
    assert any("brand spoofing" in f.lower() for f in result["flags"])


def test_moderate_single_indicator_remains_low_risk():
    # Only HTTP on a standard domain
    res_http = URLAnalyzer.analyze_single_url("http://example.org/about")
    assert res_http["risk_level"] == "Low Risk"
    assert res_http["score"] <= 30

    # Only .xyz TLD with https and normal path
    res_xyz = URLAnalyzer.analyze_single_url("https://myportfolio.xyz/gallery")
    assert res_xyz["risk_level"] == "Low Risk"
    assert res_xyz["score"] <= 30

    # Only shortener
    res_short = URLAnalyzer.analyze_single_url("https://bit.ly/resource123")
    assert res_short["risk_level"] == "Low Risk"
    assert res_short["score"] <= 30


def test_multiple_moderate_combine_to_higher_risk():
    # HTTP + .xyz TLD + sensitive /login path
    result = URLAnalyzer.analyze_single_url("http://myportal.xyz/login")
    assert result["score"] >= 40
    assert result["risk_level"] in ("Suspicious", "High Risk")


def test_trusted_domains_remain_low_risk():
    google_res = URLAnalyzer.analyze_single_url("https://www.google.com/search?q=cybersecurity")
    assert google_res["risk_level"] == "Low Risk"
    assert google_res["score"] <= 15

    apple_res = URLAnalyzer.analyze_single_url("https://apple.com/iphone")
    assert apple_res["risk_level"] == "Low Risk"
    assert apple_res["score"] <= 15

    ms_res = URLAnalyzer.analyze_single_url("https://microsoft.com/en-us/security")
    assert ms_res["risk_level"] == "Low Risk"
    assert ms_res["score"] <= 15


def test_analyze_message_urls_summary():
    text = "Check this out http://192.168.1.1/login and https://www.google.com"
    summary = URLAnalyzer.analyze_message_urls(text)
    assert summary["has_urls"] is True
    assert summary["urls_count"] == 2
    assert summary["max_url_score"] >= 85
    assert summary["overall_url_risk"] == "High Risk"
    assert len(summary["details"]) == 2
