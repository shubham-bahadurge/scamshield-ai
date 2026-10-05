# ScamShield AI

ScamShield AI is an AI-powered scam detection and verification web application that helps users identify risk indicators in suspicious messages, screenshots, and URLs before interacting with them.

---

## Problem

Social engineering remains the primary entry point for modern cyber threats. Everyday users frequently encounter deceptive content across digital channels:
- **Phishing Messages:** Deceptive SMS and email alerts threatening imminent account suspension or KYC deadlines.
- **Authority Impersonation:** Spoofed notices imitating trusted banks, courier couriers, tax agencies, and tech support.
- **Malicious & Obfuscated Links:** Hyperlinks hiding behind raw IP hosts, deceptive subdomains, userinfo `@` characters, and high-abuse top-level domains.
- **Scam Screenshots:** Deceptive messages forwarded as screenshot images across WhatsApp, Telegram, and social platforms, bypassing traditional text-only spam filters.

When everyday users receive such alerts, they face a dangerous dilemma: there is no safe sandbox to verify whether a communication is genuine. Clicking or opening a suspicious link to "test" it exposes them to credential theft, session hijacking, or malicious payloads.

---

## Solution

ScamShield AI provides a zero-harm, explainable verification environment for consumer messages:
- **Analyze Pasted Messages:** Intercepts raw text from SMS, WhatsApp, and email messages to detect psychological manipulation and urgency cues.
- **Analyze Scam Screenshots via OCR:** Ingests screenshot images in-memory and extracts text using optical character recognition without writing files to disk.
- **Zero-Network Static URL Inspection:** Evaluates embedded URLs using lexical parsing without making external HTTP/HTTPS connections or DNS lookups.
- **Calibrated Risk Scoring:** Produces a deterministic 0–100 threat index with clear visual severity levels (**High Risk**, **Suspicious**, **Low Risk**).
- **Explainable Threat Indicators:** Enumerate exact warning signs (e.g., brand impersonation, urgent deadlines, high-abuse TLDs).
- **Actionable Safe Countermeasures:** Recommends concrete next steps on how to respond safely (e.g., verifying through official offline channels).
- **Offline Rule-Based Fallback:** Seamlessly shifts to a deterministic heuristic engine if cloud AI connectivity is unavailable or rate-limited.
- **Ephemeral Session History:** Saves scan dossiers in browser `sessionStorage` for convenient one-click restoration without cloud database persistence.

---

## Key Features

- **Gemini AI Analysis:** Contextual social engineering evaluation powered by Google Gemini 2.5 Flash.
- **Screenshot OCR:** In-memory optical character recognition via Gemini 2.5 Flash Vision (`Part.from_bytes`) with local Tesseract fallback.
- **Static URL Security Analysis:** Lexical parsing detecting high-abuse TLDs, raw IP hosts, URL shorteners, and deceptive subdomains.
- **Target URL Defanging:** Automatically renders detected URLs inert (`hxxp://` and `[.]`) within non-clickable code blocks.
- **Visual Risk Scoring:** Animated circular gauge displaying threat index ratings from 0 to 100.
- **Threat Indicator Extraction:** Transparent list of detected scam signatures, suspicious keywords, and lexical anomalies.
- **Prescriptive Recommendations:** Clear, actionable safety guidance tailored to the evaluated threat category.
- **Dual-Tier Offline Fallback:** Fault-tolerant fallback to `RuleBasedAnalyzer` if Gemini API connectivity drops.
- **Session-Based Scan History:** Client-side audit log retaining up to 20 scans per session with one-click inspection.
- **Responsive Cybersecurity UI:** Premium dark glassmorphic dashboard optimized for desktop, tablet, and mobile browsers.

---

## How It Works

```
                        User Input
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
         Message Text            Screenshot Upload
               │                         │
               │               Pillow Format Validation
               │                         │
               │               Gemini Vision OCR / Tesseract
               │                         │
               └────────────┬────────────┘
                            │
                            ▼
                ScamShield Analysis Engine
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
      Static URL Analysis        Threat Classifier
    (Zero-Network Parsing)    (Gemini AI / Heuristics)
               │                         │
               └────────────┬────────────┘
                            │
                            ▼
                     Risk Assessment
                            │
                            ▼
              Threat Indicators + Safe Actions
```

> **Security Guarantee:**
> "Suspicious URLs are analyzed without visiting them using zero-network static lexical inspection."

---

## AI Implementation

ScamShield utilizes **Google Gemini 2.5 Flash** through the official `google-genai` SDK with structured cybersecurity prompts and response validation.

- **System Prompting:** The AI is instructed as a specialized cybersecurity analyst focused on social engineering tactics, authority impersonation, financial panic triggers, and fraudulent promises.
- **Schema Validation:** Model responses are strictly parsed into structured JSON containing threat classification, numerical risk scoring, detected indicators, root-cause explanations, and recommended safe actions.
- **Transparency:** ScamShield does not use a proprietary or custom-trained model, custom machine-learning training pipelines, or arbitrary accuracy percentages. It pairs a leading foundational multimodal model with deterministic validation rules and deterministic fallback logic.

---

## URL Security

Submitted URLs are analyzed **entirely without outbound network requests**. The backend never pings, resolves DNS for, connects to, downloads from, or crawls target URLs.

Implemented static lexical checks include:
- **Protocol Analysis:** Distinguishing unencrypted `http://` from encrypted `https://`.
- **Raw IP Hosts:** Detecting IPv4/IPv6 addresses used in host headers to bypass domain reputation filters (e.g., `http://192.168.1.1/login`).
- **High-Abuse TLDs:** Identifying top-level domains frequently abused in automated phishing campaigns (`.xyz`, `.top`, `.buzz`, `.cam`, `.work`, `.icu`, `.tk`, etc.).
- **Deceptive Brand & Subdomain Spoofing:** Detecting targeted brands embedded in subdomains (e.g., `paypal.com.verify-account.xyz`).
- **Credential Path Patterns:** Spotting common harvesting paths (`/login`, `/signin`, `/verify`, `/secure`, `/banking`, `/wallet`).
- **URL Shortener Detection:** Identifying link disguises (`bit.ly`, `tinyurl.com`, `t.co`, `is.gd`, `cutt.ly`, etc.).
- **Userinfo Authentication Spoofing:** Identifying the `@` trick used to deceive users regarding the actual destination host.
- **Punycode & Hex Encoding:** Flagging excessive URL percent-encoding and homograph indicators.
- **Lexical Anomalies:** Excessive URL length and suspicious hyphenation/subdomain depth.

---

## OCR (Optical Character Recognition)

- **In-Memory Image Ingestion:** Uploaded screenshots are streamed in RAM (`io.BytesIO`) and validated via `Pillow`.
- **Multimodal Gemini Vision:** When the Gemini API is configured, `types.Part.from_bytes` sends raw image bytes directly to Gemini 2.5 Flash Vision for transcription.
- **Offline OCR Fallback:** If `pytesseract` and a local Tesseract binary are present on the system, ScamShield falls back to local OCR.
- **Zero Permanent Storage:** Uploaded screenshots are processed in memory and discarded immediately after transcription. No images are saved to local disks or databases.
- **Real-World Note:** OCR extraction fidelity depends on image clarity, font legibility, and image resolution.

---

## Privacy

- **Server-Side API Keys:** The `GEMINI_API_KEY` is loaded exclusively on the backend from environment variables and is never transmitted to or accessible from the frontend client.
- **Repository Secrets Protection:** `.env` and `*.env.local` are explicitly excluded from Git version control.
- **Ephemeral Session Storage:** Threat scan records reside exclusively in the client browser's `sessionStorage` and are wiped when the browser tab is closed.
- **Zero Cloud Databases:** ScamShield does not maintain an external database, user registration system, or persistent message repository.
- **Zero URL Detonation:** Links extracted from messages or screenshots are never contacted by ScamShield servers.

---

## Fallback Architecture

ScamShield implements a resilient dual-tier fallback architecture:

```
[ Ingestion ]
      │
      ▼
Is Gemini API Available?
 ├── YES ──▶ AI-Powered Intelligence (Gemini 2.5 Flash)
 └── NO  ──▶ Deterministic Rule-Based Analysis (RuleBasedAnalyzer)

Is Gemini Vision Available for Screenshots?
 ├── YES ──▶ Gemini 2.5 Flash Vision OCR
 └── NO  ──▶ Local Tesseract OCR (if installed) / Informative Error Guidance
```

If an API outage, quota exhaustion, or network interruption occurs during an AI call, the exception is caught automatically, and `RuleBasedAnalyzer` produces a complete threat dossier marked with an offline heuristic badge.

---

## Tech Stack

- **Language:** Python 3.13+
- **Backend Web Framework:** Flask 3.1+
- **Generative AI Model:** Google Gemini 2.5 Flash (`gemini-2.5-flash`)
- **Official AI SDK:** `google-genai` (v2.28+)
- **Image Processing & Validation:** Pillow (v12.3+)
- **Offline OCR Fallback:** `pytesseract` (optional local fallback)
- **Frontend:** Vanilla HTML5, Modern CSS3 (Glassmorphism), JavaScript (ES6+)
- **Testing & Quality Assurance:** `pytest` (v9.1+)

---

## Project Structure

```
scamshield-ai/
├── .env.example                     # Environment configuration template
├── .gitignore                       # Git exclusion rules for secrets and caches
├── README.md                        # Project documentation and specifications
├── requirements.txt                 # Python dependencies
├── analyzer.py                      # ScamDetector, AIScamAnalyzer, RuleBasedAnalyzer
├── app.py                           # Flask application entry point and routes
├── create_presentation.py           # Presentation deck generator script
├── ocr_analyzer.py                  # In-memory OCR scanner (Gemini Vision + Pillow)
├── url_analyzer.py                  # Zero-network static lexical URL inspection
├── ScamShield_AI_Presentation.pptx  # 16:9 widescreen presentation deck
├── static/
│   ├── script.js                    # Client-side UI logic, drag & drop, paste, history
│   └── style.css                    # Dark cybersecurity glassmorphism styling
├── templates/
│   └── index.html                   # Application single-page dashboard
└── tests/
    ├── __init__.py                  # Test package initialization
    ├── test_analyzer.py             # Unit and integration tests for analyzer & routes
    ├── test_ocr.py                  # Unit and integration tests for OCR scanner
    └── test_url_analyzer.py         # Unit tests for static lexical URL inspection
```

---

## Installation

### Prerequisites
- macOS or Linux
- Python 3.10+ (tested on Python 3.13)
- Google Gemini API key (optional for offline mode; free tier available via [Google AI Studio](https://aistudio.google.com/))

### Setup Commands

```bash
# 1. Clone the repository and enter directory
cd scamshield-ai

# 2. Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install required dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
```

Open `.env` in a text editor and add your Gemini API key:

```env
GEMINI_API_KEY=your_actual_key_here
GEMINI_MODEL=gemini-2.5-flash
FLASK_DEBUG=True
PORT=5001
```

> **Security Warning:** Never commit your real API key to Git. The `.gitignore` file is configured to exclude `.env` automatically.

---

## Running the Application

Ensure the virtual environment is activated, then launch the Flask server:

```bash
python app.py
```

The application will start on:

**`http://127.0.0.1:5001`**

*(Port `5001` is configured by default to avoid port conflicts with the macOS AirPlay receiver on port 5000).*

---

## Testing

The test suite validates input sanitization, AI schema parsing, rule-based fallback, zero-network URL inspection, URL defanging, and in-memory OCR.

Run the complete test suite:

```bash
pytest -v
```

### Verified Test Results
- **Total Tests Collected:** **51**
- **Tests Passed:** **51**
- **Tests Failed:** **0**
- **Execution Time:** ~0.42 seconds

```
============================== test session starts ==============================
collected 51 items

tests/test_analyzer.py (28 tests) ............................            [ 54%]
tests/test_ocr.py (12 tests) ............                                 [ 78%]
tests/test_url_analyzer.py (11 tests) ...........                         [100%]

============================== 51 passed in 0.42s ==============================
```

---

## Security Notes

- **API Key Confidentiality:** The Gemini API key remains strictly server-side and is never exposed in client HTML or JavaScript bundles.
- **Git Hygiene:** Secret files (`.env`, `*.env.local`) are excluded via `.gitignore`.
- **Zero-Network URL Isolation:** Submitted URLs are analyzed purely through lexical tokenization; the server never initiates outbound connections to target links.
- **URL Defanging:** Displayed URLs are transformed into inert text strings (`hxxp://` and `[.]`) and rendered inside non-clickable HTML `<code>` blocks to prevent accidental user clicks.
- **No Scan Database:** Scans are maintained in ephemeral client-side storage, protecting sensitive user messages from centralized persistence.

---

## Limitations

- **API Connectivity Requirement:** Live neural reasoning requires an active connection to Google Gemini. When offline, ScamShield relies on its heuristic rule engine.
- **OCR Quality Dependency:** Text extraction accuracy is bounded by image resolution, blur, lighting, and visual legibility.
- **Static URL Limitations:** Lexical analysis detects patterns and known risk signals (raw IPs, abuse TLDs, shorteners), but cannot detect legitimate domains hosting compromised sub-resources without active scanning.
- **No Active Crawling or Sandboxing:** By deliberate security design, ScamShield does not crawl live web targets, execute JavaScript, or run virtual browser sandboxes.
- **No External Threat Feeds:** The current MVP does not integrate external threat intelligence APIs (e.g., VirusTotal, Shodan, AlienVault OTX).
- **No Custom Model Training:** The application utilizes foundational Gemini 2.5 Flash capabilities rather than a proprietary trained model.

---

## Future Improvements

*The following features are planned for future development:*
- **External Threat Intelligence Feeds:** Optional integration with reputation services for verified malware and domain scoring.
- **Multilingual Scam Templates:** Extended detection matrices for multilingual phishing campaigns and region-specific scam idioms.
- **Enhanced OCR Preprocessing:** Image contrast enhancement, adaptive thresholding, and skew correction for degraded screenshots.
- **Browser & Mobile Extensions:** One-click right-click inspection within email clients and web messaging platforms.
- **Enterprise SOC Reporting:** Exportable standardized threat intelligence reports (STIX/TAXII format) for IT security triage.
- **Expanded Category Coverage:** Dedicated heuristic modules for executive impersonation (whaling), QR code phishing (quishing), and invoice fraud.

---

## Hackathon

- **Event:** ForgeHacks 2026
- **Track:** AI + Cybersecurity
- **Project Purpose:** Built to provide everyday users with an accessible, explainable, and zero-harm tool to recognize and respond safely to social engineering threats.

---

## Demo Flow

For live judging or evaluations, follow this 11-step demonstration:

1. **Paste a Suspicious Message:** Load the pre-configured *Bank Phishing* test vector or paste a suspicious SMS.
2. **Execute Analysis:** Click **Analyze Threat**.
3. **Inspect the Risk Score:** Observe the animated circular threat gauge display **High Risk** ($90/100$).
4. **Review Explanations:** Examine the plain-language explanation breaking down urgency triggers and KYC panic tactics.
5. **Review Safe Actions:** Note the prescriptive countermeasures (e.g., contacting the bank through independent channels).
6. **Inspect Detected URLs:** Scroll to the *Suspicious URL Threat Inspection* section.
7. **Observe URL Defanging:** Confirm the target link is safely rendered as `hxxp://secure-bank-login[.]xyz` with `.xyz` TLD flags.
8. **Upload a Scam Screenshot:** Switch to the **Screenshot OCR** tab and upload or paste (`Cmd+V`) a screenshot image.
9. **Demonstrate OCR Extraction:** Click **Scan Screenshot**; observe in-memory text transcription without disk writes.
10. **Examine Final Dossier:** Confirm that extracted text and detected URLs flow through the unified assessment engine.
11. **Review Session History:** Scroll to the *Session Audit Log* below; demonstrate instant one-click restoration of previous scans from `sessionStorage`.

---

## Honest AI Disclosure

AI coding assistants were used during development to accelerate code generation, test authoring, and documentation formatting where applicable. The architecture, security design, deterministic validation safeguards, and final repository documentation accurately reflect the implemented application.
