// ==========================================================================
// SCAMSHIELD AI - CLIENT THREAT INTERCEPTOR ENGINE
// ==========================================================================

const SESSION_STORAGE_KEY = "scamshield_session_history";
const MAX_HISTORY_ITEMS = 20;

// State management for in-memory screenshot ingestion
let selectedScreenshotFile = null;
let screenshotObjectUrl = null;

// Pre-configured test vectors for hackathon live demonstrations
const SAMPLES = {
    phishing: "URGENT NOTICE: Your bank account will be suspended within 24 hours due to unverified KYC. Click http://secure-bank-login.xyz to verify your account immediately and enter your OTP to avoid account closure.",
    lottery: "CONGRATULATIONS! You have been selected as the grand prize winner of $250,000 in our international lottery! Click here to claim your reward. Send money for processing fees to unlock your winnings.",
    crypto: "URGENT: Guaranteed 300% returns on crypto flash pool! Send 0.2 ETH now to verify your account and claim your prize. Click http://claim-crypto-eth.net/airdrop to connect your wallet.",
    safe: "Hi Shubham, our team standup is rescheduled to tomorrow at 10:30 AM in Conference Room B. Please remember to bring the slide deck."
};

// SVG Icon Helpers
const ICONS = {
    warning: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`,
    shield: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><path d="m9 12 2 2 4-4"></path></svg>`,
    safeCheck: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`
};

document.addEventListener("DOMContentLoaded", () => {
    // 1. Text input character counter
    const textarea = document.getElementById("message");
    const charCounter = document.getElementById("char-counter");

    if (textarea && charCounter) {
        textarea.addEventListener("input", () => {
            const len = textarea.value.length;
            charCounter.textContent = `${len} char${len === 1 ? '' : 's'}`;
        });
    }

    // 2. Drag & Drop event bindings on screenshot dropzone
    const dropzone = document.getElementById("screenshot-dropzone");
    if (dropzone) {
        ["dragenter", "dragover"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add("drag-active");
            });
        });

        ["dragleave", "dragend"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove("drag-active");
            });
        });

        dropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove("drag-active");

            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                const file = e.dataTransfer.files[0];
                setScreenshotFile(file);
            }
        });
    }

    // 3. Global Clipboard Image Paste (Cmd+V on Mac / Ctrl+V on Windows)
    window.addEventListener("paste", (e) => {
        const items = (e.clipboardData || window.clipboardData)?.items;
        if (!items) return;

        for (let i = 0; i < items.length; i++) {
            if (items[i].type && items[i].type.startsWith("image/")) {
                const file = items[i].getAsFile();
                if (file) {
                    e.preventDefault();
                    switchInputMode("screenshot");
                    setScreenshotFile(file);
                    break;
                }
            }
        }
    });

    // 4. Initialize session scan history from sessionStorage
    renderHistoryList();
});

// ==========================================================================
// INPUT MODE TOGGLE (Message Text vs Screenshot OCR)
// ==========================================================================
function switchInputMode(mode) {
    const tabText = document.getElementById("tab-text");
    const tabScreenshot = document.getElementById("tab-screenshot");
    const textSection = document.getElementById("text-input-section");
    const screenshotSection = document.getElementById("screenshot-input-section");

    if (mode === "screenshot") {
        if (tabScreenshot) tabScreenshot.classList.add("active");
        if (tabText) tabText.classList.remove("active");
        if (screenshotSection) screenshotSection.classList.remove("hidden");
        if (textSection) textSection.classList.add("hidden");
    } else {
        if (tabText) tabText.classList.add("active");
        if (tabScreenshot) tabScreenshot.classList.remove("active");
        if (textSection) textSection.classList.remove("hidden");
        if (screenshotSection) screenshotSection.classList.add("hidden");
    }
}

// ==========================================================================
// SCREENSHOT FILE HANDLING & PREVIEW
// ==========================================================================
function triggerFilePicker() {
    const fileInput = document.getElementById("screenshot-file-input");
    if (fileInput) fileInput.click();
}

function handleFileSelect(event) {
    const file = event.target && event.target.files && event.target.files[0];
    if (file) {
        setScreenshotFile(file);
    }
}

function setScreenshotFile(file) {
    if (!file.type || !file.type.startsWith("image/")) {
        alert("Please select a valid image file (PNG, JPEG, WEBP, or GIF).");
        return;
    }

    // Enforce 10 MB client-side limit
    if (file.size > 10 * 1024 * 1024) {
        alert("The selected screenshot exceeds the 10 MB size limit.");
        return;
    }

    selectedScreenshotFile = file;

    // Manage preview object URL in browser memory
    if (screenshotObjectUrl) {
        URL.revokeObjectURL(screenshotObjectUrl);
    }
    screenshotObjectUrl = URL.createObjectURL(file);

    const previewBox = document.getElementById("screenshot-preview-box");
    const dropzonePrompt = document.getElementById("dropzone-prompt");
    const previewImg = document.getElementById("screenshot-preview-img");
    const filenameEl = document.getElementById("preview-filename");
    const filesizeEl = document.getElementById("preview-filesize");

    if (previewImg) previewImg.src = screenshotObjectUrl;
    if (filenameEl) filenameEl.textContent = file.name || "screenshot.png";
    if (filesizeEl) filesizeEl.textContent = formatBytes(file.size);

    if (dropzonePrompt) dropzonePrompt.classList.add("hidden");
    if (previewBox) previewBox.classList.remove("hidden");
}

function removeSelectedScreenshot(event) {
    if (event) {
        event.stopPropagation();
    }
    clearScreenshot();
}

function clearScreenshot() {
    selectedScreenshotFile = null;
    if (screenshotObjectUrl) {
        URL.revokeObjectURL(screenshotObjectUrl);
        screenshotObjectUrl = null;
    }

    const fileInput = document.getElementById("screenshot-file-input");
    if (fileInput) fileInput.value = "";

    const previewBox = document.getElementById("screenshot-preview-box");
    const dropzonePrompt = document.getElementById("dropzone-prompt");
    const previewImg = document.getElementById("screenshot-preview-img");

    if (previewImg) previewImg.src = "";
    if (previewBox) previewBox.classList.add("hidden");
    if (dropzonePrompt) dropzonePrompt.classList.remove("hidden");

    const resultCard = document.getElementById("result");
    const urlSection = document.getElementById("url-analysis-section");
    const ocrSection = document.getElementById("ocr-extracted-section");
    if (resultCard) resultCard.classList.add("hidden");
    if (urlSection) urlSection.classList.add("hidden");
    if (ocrSection) ocrSection.classList.add("hidden");
}

function formatBytes(bytes) {
    if (!bytes || bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

// ==========================================================================
// TEST VECTOR HELPERS
// ==========================================================================
function loadSample(type) {
    const textarea = document.getElementById("message");
    const charCounter = document.getElementById("char-counter");

    if (textarea && SAMPLES[type]) {
        textarea.value = SAMPLES[type];
        if (charCounter) {
            charCounter.textContent = `${textarea.value.length} chars`;
        }
        textarea.focus();
    }
}

function clearInput() {
    const textarea = document.getElementById("message");
    const charCounter = document.getElementById("char-counter");
    const resultCard = document.getElementById("result");
    const urlSection = document.getElementById("url-analysis-section");
    const ocrSection = document.getElementById("ocr-extracted-section");

    if (textarea) textarea.value = "";
    if (charCounter) charCounter.textContent = "0 chars";
    if (resultCard) resultCard.classList.add("hidden");
    if (urlSection) urlSection.classList.add("hidden");
    if (ocrSection) ocrSection.classList.add("hidden");
}

// ==========================================================================
// RENDER COMPLETE ANALYSIS DOSSIER
// ==========================================================================
function renderAnalysisResult(data) {
    const resultCard = document.getElementById("result");
    if (!resultCard) return;

    // Unhide result card
    resultCard.classList.remove("hidden");

    const risk = data.risk || "Low Risk";
    const scoreVal = Number(data.score) || 0;

    // 1. Update Risk Pill & Severity Classes
    const riskEl = document.getElementById("risk");
    if (riskEl) {
        riskEl.textContent = risk;
        riskEl.className = "risk-pill " + getRiskClass(risk);
    }

    // 2. Animate Circular Visual Meter Gauge
    animateCircularGauge(scoreVal, risk);

    // 3. Update Fallback Linear Bar
    const scoreBar = document.getElementById("score-bar-fill");
    if (scoreBar) {
        scoreBar.style.width = Math.min(100, Math.max(0, scoreVal)) + "%";
        scoreBar.className = "score-bar-fill " + getRiskBarClass(risk);
    }

    // 4. Update Source Badge (AI vs Fallback + Vision OCR indication)
    const sourceBadge = document.getElementById("source-badge");
    if (sourceBadge) {
        if (data.is_screenshot) {
            const ocrName = data.ocr_source === "gemini_vision" ? "Gemini Vision" : "OCR";
            if (data.source === "ai") {
                sourceBadge.innerHTML = `🤖 ${ocrName} + AI Intelligence`;
                sourceBadge.className = "badge badge-ai";
            } else {
                sourceBadge.innerHTML = `📷 ${ocrName} + Rule Heuristic`;
                sourceBadge.className = "badge badge-fallback";
            }
        } else if (data.source === "ai") {
            sourceBadge.innerHTML = `🤖 AI-Powered Intelligence`;
            sourceBadge.className = "badge badge-ai";
        } else {
            sourceBadge.innerHTML = `⚡ Rule Heuristic (Offline)`;
            sourceBadge.className = "badge badge-fallback";
        }
    }

    // 5. Update Threat Category Pill
    const categoryEl = document.getElementById("category");
    if (categoryEl) {
        categoryEl.textContent = data.category || "Scam Assessment";
    }

    // 5b. Populate OCR Extracted Text Section (when screenshot analyzed)
    const ocrSection = document.getElementById("ocr-extracted-section");
    const ocrText = document.getElementById("ocr-extracted-text");
    const ocrBadge = document.getElementById("ocr-source-badge");

    if (data.is_screenshot && data.extracted_text) {
        if (ocrSection) ocrSection.classList.remove("hidden");
        if (ocrText) ocrText.textContent = data.extracted_text;
        if (ocrBadge) {
            ocrBadge.textContent = data.ocr_source === "gemini_vision" ? "Gemini 2.5 Flash Vision" : "Local Tesseract OCR";
        }
    } else {
        if (ocrSection) ocrSection.classList.add("hidden");
    }

    // 5c. Populate Suspicious URL Threat Inspection Section
    const urlSection = document.getElementById("url-analysis-section");
    const urlDetailsList = document.getElementById("url-details-list");
    const urlCountBadge = document.getElementById("url-count-badge");

    if (data.url_analysis && data.url_analysis.has_urls && Array.isArray(data.url_analysis.details) && data.url_analysis.details.length > 0) {
        if (urlSection) urlSection.classList.remove("hidden");
        if (urlCountBadge) {
            const count = data.url_analysis.urls_count || data.url_analysis.details.length;
            urlCountBadge.textContent = `${count} Target${count > 1 ? 's' : ''} Scanned`;
        }
        if (urlDetailsList) {
            urlDetailsList.innerHTML = "";
            data.url_analysis.details.forEach(item => {
                const card = document.createElement("div");
                card.className = "url-threat-card " + getUrlRiskBorderClass(item.risk_level);

                const flagsHtml = item.flags && item.flags.length > 0
                    ? item.flags.map(f => `<li class="url-flag-item"><span class="url-flag-icon">⚠️</span><span>${escapeHtml(f)}</span></li>`).join("")
                    : `<li class="url-flag-clean"><span>✅ No critical lexical anomalies detected</span></li>`;

                card.innerHTML = `
                    <div class="url-card-header">
                        <div class="url-defanged-box">
                            <span class="url-defanged-label">DEFANGED TARGET:</span>
                            <code class="defanged-url-code">${escapeHtml(item.defanged_url)}</code>
                        </div>
                        <span class="url-risk-tag ${getUrlRiskClass(item.risk_level)}">${escapeHtml(item.risk_level)}</span>
                    </div>
                    <div class="url-meta-row">
                        <span class="url-meta-pill">SCHEME: <strong>${escapeHtml((item.scheme || '').toUpperCase())}</strong></span>
                        <span class="url-meta-pill">HOST: <strong>${escapeHtml(item.hostname || '')}</strong></span>
                        <span class="url-meta-pill">THREAT SCORE: <strong>${item.score}/100</strong></span>
                    </div>
                    <div class="url-flags-container">
                        <span class="url-flags-title">INSPECTION FINDINGS:</span>
                        <ul class="url-flags-list">${flagsHtml}</ul>
                    </div>
                `;
                urlDetailsList.appendChild(card);
            });
        }
    } else {
        if (urlSection) urlSection.classList.add("hidden");
    }

    // 6. Update Why is this suspicious? (Explanation)
    const explanationEl = document.getElementById("explanation");
    if (explanationEl) {
        explanationEl.textContent = data.explanation || "Analysis completed successfully.";
    }

    // 7. Update Detected Warning Signs
    const detectedList = document.getElementById("detected");
    if (detectedList) {
        detectedList.innerHTML = "";
        const detectedItems = Array.isArray(data.detected) ? data.detected : [];

        if (detectedItems.length === 0) {
            const li = document.createElement("li");
            li.className = "indicator-safe-card";
            li.innerHTML = `
                <span class="indicator-safe-icon">${ICONS.safeCheck}</span>
                <span class="indicator-text">No active phishing signatures or standard scam keywords were detected.</span>
            `;
            detectedList.appendChild(li);
        } else {
            detectedItems.forEach(item => {
                const li = document.createElement("li");
                li.className = "threat-indicator-card";
                li.innerHTML = `
                    <span class="indicator-bullet">${ICONS.warning}</span>
                    <span class="indicator-text">Suspicious indicator: <strong>${escapeHtml(item)}</strong></span>
                `;
                detectedList.appendChild(li);
            });
        }
    }

    // 8. Update Recommended Actions
    const recommendationsList = document.getElementById("recommendations");
    if (recommendationsList) {
        recommendationsList.innerHTML = "";
        const recs = Array.isArray(data.recommendations) && data.recommendations.length > 0
            ? data.recommendations
            : [
                "Do not click unverified links or enter login credentials.",
                "Verify the sender's identity through official independent channels."
            ];

        recs.forEach(rec => {
            const li = document.createElement("li");
            li.className = "action-card";
            li.innerHTML = `
                <span class="action-shield">${ICONS.shield}</span>
                <span class="action-text">${escapeHtml(rec)}</span>
            `;
            recommendationsList.appendChild(li);
        });
    }
}

// ==========================================================================
// TEXT MESSAGE SCAN EXECUTION
// ==========================================================================
async function analyzeMessage() {
    const messageInput = document.getElementById("message");
    const analyzeBtn = document.getElementById("analyze-btn");
    const resultCard = document.getElementById("result");
    const textareaWrapper = document.getElementById("textarea-wrapper");

    const message = (messageInput ? messageInput.value : "").trim();

    if (!message) {
        alert("Please enter a message to analyze.");
        return;
    }

    // Set interactive loading state
    const originalBtnContent = analyzeBtn.innerHTML;
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = `
        <span class="btn-icon">
            <svg class="spin-animation" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
        </span>
        <span class="btn-text">Scanning Threat Vectors...</span>
    `;
    if (textareaWrapper) {
        textareaWrapper.classList.add("scanning");
    }

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();

        if (!response.ok || data.error) {
            alert(data.error || "An error occurred during threat analysis.");
            return;
        }

        // Render full analysis dossier
        renderAnalysisResult(data);

        // Save scan result to session history
        saveScanToHistory(message, data);

        // Smooth scroll to dossier report
        resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

    } catch (error) {
        console.error("Analysis network error:", error);
        alert("Failed to connect to ScamShield AI service. Please ensure the server is active.");
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = originalBtnContent;
        if (textareaWrapper) {
            textareaWrapper.classList.remove("scanning");
        }
    }
}

// ==========================================================================
// SCREENSHOT OCR SCAN EXECUTION
// ==========================================================================
async function analyzeScreenshot() {
    if (!selectedScreenshotFile) {
        alert("Please upload, drag & drop, or paste a screenshot image first.");
        return;
    }

    const analyzeScreenshotBtn = document.getElementById("analyze-screenshot-btn");
    const resultCard = document.getElementById("result");
    const originalBtnContent = analyzeScreenshotBtn.innerHTML;

    analyzeScreenshotBtn.disabled = true;
    analyzeScreenshotBtn.innerHTML = `
        <span class="btn-icon">
            <svg class="spin-animation" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
        </span>
        <span class="btn-text">Extracting Text & Scanning Threat...</span>
    `;

    try {
        const formData = new FormData();
        formData.append("screenshot", selectedScreenshotFile);

        const response = await fetch("/analyze-screenshot", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok || data.error) {
            alert(data.error || "An error occurred during screenshot threat analysis.");
            return;
        }

        // Populate textarea with extracted text for user reference
        const textarea = document.getElementById("message");
        const charCounter = document.getElementById("char-counter");
        if (textarea && data.extracted_text) {
            textarea.value = data.extracted_text;
            if (charCounter) {
                charCounter.textContent = `${data.extracted_text.length} chars`;
            }
        }

        // Render full analysis dossier
        renderAnalysisResult(data);

        // Save scan result to session history
        const summaryText = data.extracted_text || `Screenshot (${selectedScreenshotFile.name})`;
        saveScanToHistory(summaryText, data);

        // Smooth scroll to dossier report
        if (resultCard) {
            resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }

    } catch (error) {
        console.error("Screenshot analysis network error:", error);
        alert("Failed to connect to ScamShield AI service. Please ensure the server is active.");
    } finally {
        analyzeScreenshotBtn.disabled = false;
        analyzeScreenshotBtn.innerHTML = originalBtnContent;
    }
}

// ==========================================================================
// SESSION SCAN HISTORY ENGINE (sessionStorage)
// ==========================================================================
function getStoredHistory() {
    try {
        const raw = sessionStorage.getItem(SESSION_STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch (e) {
        console.warn("sessionStorage read error:", e);
        return [];
    }
}

function saveScanToHistory(originalMessage, analysisData) {
    try {
        let history = getStoredHistory();
        const record = {
            id: "scan_" + Date.now() + "_" + Math.random().toString(36).substr(2, 6),
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            risk: analysisData.risk || "Low Risk",
            score: Number(analysisData.score) || 0,
            category: analysisData.category || "General Assessment",
            messagePreview: originalMessage.length > 80 ? originalMessage.substring(0, 80) + "..." : originalMessage,
            originalMessage: originalMessage,
            hasUrls: Boolean(analysisData.url_analysis && analysisData.url_analysis.has_urls),
            urlsCount: analysisData.url_analysis ? (analysisData.url_analysis.urls_count || 0) : 0,
            isScreenshot: Boolean(analysisData.is_screenshot),
            ocrSource: analysisData.ocr_source || null,
            analysisData: analysisData
        };

        // Prepend and enforce maximum limit of 20 scans
        history.unshift(record);
        if (history.length > MAX_HISTORY_ITEMS) {
            history = history.slice(0, MAX_HISTORY_ITEMS);
        }

        sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(history));
        renderHistoryList();
    } catch (e) {
        console.warn("Failed to save scan to sessionStorage:", e);
    }
}

function restoreScan(scanId) {
    const history = getStoredHistory();
    const item = history.find(entry => entry.id === scanId);
    if (!item) return;

    const textarea = document.getElementById("message");
    const charCounter = document.getElementById("char-counter");
    if (textarea) {
        textarea.value = item.originalMessage;
        if (charCounter) {
            charCounter.textContent = `${item.originalMessage.length} chars`;
        }
    }

    renderAnalysisResult(item.analysisData);

    const resultCard = document.getElementById("result");
    if (resultCard) {
        resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
}

function clearScanHistory() {
    try {
        sessionStorage.removeItem(SESSION_STORAGE_KEY);
    } catch (e) {
        console.warn("Failed to clear sessionStorage:", e);
    }
    renderHistoryList();
}

function renderHistoryList() {
    const historyList = document.getElementById("history-list");
    const historyEmpty = document.getElementById("history-empty");
    const counterBadge = document.getElementById("history-counter-badge");
    const history = getStoredHistory();

    if (!counterBadge) return;

    if (!history || history.length === 0) {
        counterBadge.textContent = "0 Scans";
        if (historyEmpty) historyEmpty.classList.remove("hidden");
        if (historyList) {
            historyList.innerHTML = "";
            historyList.classList.add("hidden");
        }
        return;
    }

    counterBadge.textContent = `${history.length} Scan${history.length > 1 ? 's' : ''} Logged`;
    if (historyEmpty) historyEmpty.classList.add("hidden");
    if (historyList) {
        historyList.classList.remove("hidden");
        historyList.innerHTML = "";

        history.forEach(item => {
            const card = document.createElement("div");
            card.className = "history-card";
            card.setAttribute("role", "button");
            card.setAttribute("tabindex", "0");
            card.onclick = () => restoreScan(item.id);
            card.onkeydown = (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    restoreScan(item.id);
                }
            };

            const urlBadgeHtml = item.hasUrls
                ? `<span class="history-pill history-pill-url">🔗 ${item.urlsCount} URL${item.urlsCount > 1 ? 's' : ''}</span>`
                : '';

            const ocrBadgeHtml = item.isScreenshot
                ? `<span class="history-pill history-pill-ocr">📷 Screenshot</span>`
                : '';

            const detectedCount = item.analysisData && Array.isArray(item.analysisData.detected)
                ? item.analysisData.detected.length
                : 0;

            card.innerHTML = `
                <div class="history-card-top">
                    <div class="history-badges-left">
                        <span class="history-risk-pill ${getRiskClass(item.risk)}">${escapeHtml(item.risk)}</span>
                        <span class="history-score-pill">${item.score}/100</span>
                        ${ocrBadgeHtml}
                        ${urlBadgeHtml}
                    </div>
                    <span class="history-time">${escapeHtml(item.timestamp)}</span>
                </div>
                <div class="history-snippet">${escapeHtml(item.messagePreview)}</div>
                <div class="history-card-footer">
                    <span class="history-pill history-pill-cat">${escapeHtml(item.category)}</span>
                    <span class="history-indicators-count">${detectedCount} indicator${detectedCount === 1 ? '' : 's'}</span>
                    <span class="history-inspect-action">Re-inspect ↗</span>
                </div>
            `;
            historyList.appendChild(card);
        });
    }
}

// ==========================================================================
// VISUAL METERS & HELPERS
// ==========================================================================
function animateCircularGauge(targetScore, risk) {
    const meterCircle = document.getElementById("meter-circle");
    const scoreText = document.getElementById("score");

    const clampedScore = Math.min(100, Math.max(0, targetScore));
    const circumference = 2 * Math.PI * 50; // r = 50 => ~314.159
    const offset = circumference - (clampedScore / 100) * circumference;

    if (meterCircle) {
        meterCircle.style.strokeDashoffset = offset;
        meterCircle.className = "meter-fill " + getStrokeClass(risk);
    }

    if (scoreText) {
        animateScoreCounter(scoreText, clampedScore);
    }
}

function animateScoreCounter(element, target) {
    const start = 0;
    const duration = 500;
    const startTime = performance.now();

    function updateCounter(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeOutQuad = 1 - (1 - progress) * (1 - progress);
        const currentVal = Math.round(start + (target - start) * easeOutQuad);

        element.textContent = currentVal;

        if (progress < 1) {
            requestAnimationFrame(updateCounter);
        } else {
            element.textContent = target;
        }
    }

    requestAnimationFrame(updateCounter);
}

function getRiskClass(risk) {
    if (!risk) return "risk-low";
    const lower = risk.toLowerCase();
    if (lower.includes("high")) return "risk-high";
    if (lower.includes("suspicious")) return "risk-suspicious";
    return "risk-low";
}

function getRiskBarClass(risk) {
    if (!risk) return "bar-low";
    const lower = risk.toLowerCase();
    if (lower.includes("high")) return "bar-high";
    if (lower.includes("suspicious")) return "bar-suspicious";
    return "bar-low";
}

function getStrokeClass(risk) {
    if (!risk) return "stroke-low";
    const lower = risk.toLowerCase();
    if (lower.includes("high")) return "stroke-high";
    if (lower.includes("suspicious")) return "stroke-suspicious";
    return "stroke-low";
}

function getUrlRiskClass(risk) {
    if (!risk) return "tag-low";
    const lower = risk.toLowerCase();
    if (lower.includes("high")) return "tag-high";
    if (lower.includes("suspicious")) return "tag-suspicious";
    return "tag-low";
}

function getUrlRiskBorderClass(risk) {
    if (!risk) return "url-border-low";
    const lower = risk.toLowerCase();
    if (lower.includes("high")) return "url-border-high";
    if (lower.includes("suspicious")) return "url-border-suspicious";
    return "url-border-low";
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

// ==========================================================================
// PRIVACY-FIRST INCIDENT RESPONSE COPILOT
// ==========================================================================
async function buildIncidentResponsePlan() {
    const scenarioInput = document.getElementById("incident-scenario");
    const button = document.getElementById("response-plan-btn");
    const result = document.getElementById("incident-response-result");
    if (!scenarioInput || !button || !result) return;

    const originalButton = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="btn-text">Preparing safe next steps…</span>';

    try {
        const response = await fetch("/incident-response", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scenario: scenarioInput.value })
        });
        const data = await response.json();
        if (!response.ok || data.error) {
            throw new Error(data.error || "Could not prepare a response plan.");
        }

        document.getElementById("incident-response-title").textContent = data.title;
        document.getElementById("incident-response-priority").textContent = data.priority;
        document.getElementById("incident-response-report").textContent = data.report;
        document.getElementById("incident-response-privacy").textContent = data.privacy;

        const stepsList = document.getElementById("incident-response-steps");
        stepsList.replaceChildren();
        (Array.isArray(data.steps) ? data.steps : []).forEach((step) => {
            const item = document.createElement("li");
            item.textContent = step;
            stepsList.appendChild(item);
        });
        result.classList.remove("hidden");
        result.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (error) {
        console.error("Incident response plan error:", error);
        alert(error.message || "Unable to prepare a response plan. Please try again.");
    } finally {
        button.disabled = false;
        button.innerHTML = originalButton;
    }
}
