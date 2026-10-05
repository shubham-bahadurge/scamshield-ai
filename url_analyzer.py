"""
ScamShield AI - Suspicious URL Analyzer
========================================
Static lexical URL inspection module.
Performs 100% offline, zero-network analysis on URLs extracted from messages:
  - NO external HTTP/HTTPS requests
  - NO DNS lookups or socket connections
  - NO downloads or code execution
"""

import ipaddress
import re
from typing import Any, Dict, List
import urllib.parse

# Common URL Shorteners used to disguise final landing destinations
URL_SHORTENERS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "is.gd",
    "cutt.ly",
    "rb.gy",
    "shorturl.at",
    "ow.ly",
    "goo.gl",
    "buff.ly",
}

# High-abuse Top-Level Domains frequently utilized in automated phishing campaigns
SUSPICIOUS_TLDS = {
    "xyz",
    "top",
    "buzz",
    "cam",
    "work",
    "icu",
    "link",
    "click",
    "tk",
    "ml",
    "ga",
    "cf",
    "gq",
    "rest",
    "fit",
    "surf",
    "monster",
    "country",
}

# Recognized legitimate high-profile domains (protects against false positives)
TRUSTED_DOMAINS = {
    "google.com",
    "microsoft.com",
    "apple.com",
    "amazon.com",
    "github.com",
    "wikipedia.org",
    "youtube.com",
    "linkedin.com",
    "cloudflare.com",
    "stackoverflow.com",
    "python.org",
    "gov.in",
    "gov.uk",
    "usa.gov",
}

# Sensitive credential / transaction keywords in path or query
SENSITIVE_PATH_PATTERNS = [
    r"/login",
    r"/signin",
    r"/verify",
    r"/verification",
    r"/authenticate",
    r"/update-kyc",
    r"/kyc",
    r"/wallet-connect",
    r"/claim",
    r"/claim-reward",
    r"/claim-prize",
    r"/secure-auth",
    r"/otp",
    r"/account-recovery",
    r"/reset-password",
]

# Brand names commonly impersonated in phishing attacks
TARGETED_BRANDS = [
    "paypal",
    "apple",
    "microsoft",
    "netflix",
    "amazon",
    "chase",
    "bankofamerica",
    "wellsfargo",
    "citibank",
    "hsbc",
    "hdfc",
    "sbi",
    "icici",
    "paytm",
    "binance",
    "coinbase",
    "metamask",
]


class URLAnalyzer:
    """
    Static analyzer for lexical detection of suspicious and malicious URLs.
    """

    # Bounded URL regex avoiding catastrophic backtracking (ReDoS safe)
    URL_PATTERN = re.compile(
        r"(?:https?://[^\s<>'\"`]+|www\.[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}(?:/[^\s<>'\"`]*)?)",
        re.IGNORECASE,
    )

    @classmethod
    def defang_url(cls, url: str) -> str:
        """
        Defangs a URL so that it cannot be mistakenly rendered as an active hyperlink.
        Example: http://evil.com/login -> hxxp://evil[.]com/login
        """
        if not url:
            return ""
        defanged = re.sub(r"^https://", "hxxps://", url, flags=re.IGNORECASE)
        defanged = re.sub(r"^http://", "hxxp://", defanged, flags=re.IGNORECASE)
        defanged = defanged.replace(".", "[.]")
        return defanged

    @classmethod
    def extract_urls(cls, text: str) -> List[str]:
        """
        Safely extracts all URLs from the input text, stripping trailing punctuation.
        """
        if not text:
            return []

        raw_matches = cls.URL_PATTERN.findall(text)
        cleaned_urls: List[str] = []

        for match in raw_matches:
            # Strip trailing punctuation often caught by regex in natural language
            cleaned = match.rstrip(".,;!?:)'\"]}>")
            if cleaned and cleaned not in cleaned_urls:
                cleaned_urls.append(cleaned)

        return cleaned_urls

    @classmethod
    def _is_ip_address(cls, hostname: str) -> bool:
        """Check if hostname is a raw IPv4 or IPv6 address."""
        clean_host = hostname.strip("[]")
        try:
            ipaddress.ip_address(clean_host)
            return True
        except ValueError:
            return False

    @classmethod
    def analyze_single_url(cls, raw_url: str) -> Dict[str, Any]:
        """
        Lexically inspect a single URL without any network requests.
        Returns score, risk level, defanged URL, and specific detected flags.
        """
        # Ensure scheme for urllib parsing
        parseable_url = raw_url
        if raw_url.lower().startswith("www."):
            parseable_url = "http://" + raw_url

        try:
            parsed = urllib.parse.urlsplit(parseable_url)
        except Exception:
            return {
                "original_url": raw_url,
                "defanged_url": cls.defang_url(raw_url),
                "scheme": "unknown",
                "hostname": "invalid",
                "score": 40,
                "risk_level": "Suspicious",
                "flags": ["Malformed URL structure detected."],
            }

        scheme = (parsed.scheme or "").lower()
        netloc = parsed.netloc or ""
        hostname = (parsed.hostname or "").lower()
        path = parsed.path or ""
        query = parsed.query or ""

        flags: List[str] = []
        critical_floor = 0
        moderate_score = 0

        # Check trusted whitelist base domains
        is_trusted = any(
            hostname == trusted or hostname.endswith("." + trusted)
            for trusted in TRUSTED_DOMAINS
        )

        # -------------------------------------------------------------
        # 1. CRITICAL INDICATORS (Trigger High-Risk Floor)
        # -------------------------------------------------------------

        # A. Raw IP Address Host
        if cls._is_ip_address(hostname):
            critical_floor = max(critical_floor, 85)
            flags.append("Critical: Raw IP-address host used instead of legitimate domain name.")

        # B. Userinfo '@' Spoofing
        if "@" in netloc or parsed.username:
            critical_floor = max(critical_floor, 90)
            flags.append("Critical: Userinfo '@' spoofing detected (designed to disguise destination domain).")

        # C. Brand Impersonation in Subdomains / Domain
        # Example: paypal.com.verify-auth.xyz or apple.com.account-update.net
        if not is_trusted:
            for brand in TARGETED_BRANDS:
                # Subdomain contains "brand.com" or "brand-" prefix
                if f"{brand}.com." in hostname or f"{brand}.org." in hostname:
                    critical_floor = max(critical_floor, 88)
                    flags.append(f"Critical: Misleading brand spoofing detected for '{brand}' in subdomain.")
                    break
                # Domain contains hyphenated brand impersonation like chase-bank-login
                elif re.search(rf"\b{brand}[-_](?:login|verify|secure|update|support|account)\b", hostname):
                    critical_floor = max(critical_floor, 85)
                    flags.append(f"Critical: Suspicious hyphenated brand pattern detected ('{brand}').")
                    break

        # -------------------------------------------------------------
        # 2. MODERATE INDICATORS (Cumulative Scoring)
        # -------------------------------------------------------------

        # A. Scheme Security (Plain HTTP)
        if scheme == "http":
            moderate_score += 15
            flags.append("Insecure HTTP protocol (lacks SSL/TLS encryption).")

        # B. High-Abuse TLDs
        tld = hostname.split(".")[-1] if "." in hostname else ""
        if tld in SUSPICIOUS_TLDS and not is_trusted:
            moderate_score += 25
            flags.append(f"High-abuse top-level domain frequently utilized in scams (.{tld}).")

        # C. URL Shorteners
        if hostname in URL_SHORTENERS:
            moderate_score += 20
            flags.append(f"URL shortener detected ({hostname}) — conceals final destination.")

        # D. Sensitive Path & Authentication Triggers
        full_path = f"{path}?{query}".lower()
        for pattern in SENSITIVE_PATH_PATTERNS:
            if re.search(pattern, full_path):
                moderate_score += 15
                flags.append("Sensitive credential or authentication path keyword detected in URL.")
                break

        # E. Excessive Subdomain Depth (e.g. login.secure.verify.user.account.net)
        subdomain_parts = hostname.split(".")
        if len(subdomain_parts) > 3 and not is_trusted and not cls._is_ip_address(hostname):
            moderate_score += 15
            flags.append("Excessive subdomain nesting (potential domain obfuscation).")

        # F. Non-standard Port
        if parsed.port and parsed.port not in (80, 443):
            moderate_score += 15
            flags.append(f"Non-standard web port (:{parsed.port}) used.")

        # G. Excessive Length
        if len(raw_url) > 100:
            moderate_score += 10
            flags.append(f"Abnormally long URL ({len(raw_url)} characters).")

        # H. Excessive Hex / Percent Encoding
        if raw_url.count("%") >= 3:
            moderate_score += 15
            flags.append("Excessive URL percent-encoding (potential evasion technique).")

        # -------------------------------------------------------------
        # 3. COMPUTE FINAL SCORE & SEVERITY
        # -------------------------------------------------------------

        # If trusted and no critical spoofing, cap score to prevent false positives
        if is_trusted and critical_floor == 0:
            final_score = min(moderate_score, 15)
        else:
            final_score = min(100, max(critical_floor, moderate_score))

        if final_score >= 70:
            risk_level = "High Risk"
        elif final_score >= 35:
            risk_level = "Suspicious"
        else:
            risk_level = "Low Risk"

        return {
            "original_url": raw_url,
            "defanged_url": cls.defang_url(raw_url),
            "scheme": scheme or "http",
            "hostname": hostname or "unknown",
            "score": final_score,
            "risk_level": risk_level,
            "flags": flags,
        }

    @classmethod
    def analyze_message_urls(cls, text: str) -> Dict[str, Any]:
        """
        Extracts and analyzes all URLs found in a text message.
        """
        urls = cls.extract_urls(text)

        if not urls:
            return {
                "has_urls": False,
                "urls_count": 0,
                "max_url_score": 0,
                "overall_url_risk": "Low Risk",
                "detected_flags": [],
                "details": [],
            }

        details = [cls.analyze_single_url(u) for u in urls]
        max_score = max((d["score"] for d in details), default=0)

        # Aggregate unique flags across all URLs
        combined_flags: List[str] = []
        for d in details:
            for flag in d["flags"]:
                if flag not in combined_flags:
                    combined_flags.append(flag)

        if max_score >= 70:
            overall_risk = "High Risk"
        elif max_score >= 35:
            overall_risk = "Suspicious"
        else:
            overall_risk = "Low Risk"

        return {
            "has_urls": True,
            "urls_count": len(urls),
            "max_url_score": max_score,
            "overall_url_risk": overall_risk,
            "detected_flags": combined_flags,
            "details": details,
        }
