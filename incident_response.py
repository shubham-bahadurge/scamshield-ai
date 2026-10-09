"""Privacy-first incident response playbooks for common scam exposure scenarios.

These deterministic playbooks complement AI scam detection with practical next steps.
No incident details are persisted or sent to a third-party service by this module.
"""
from typing import Dict

PLAYBOOKS: Dict[str, Dict[str, object]] = {
    "received": {
        "title": "You received a suspicious message",
        "priority": "Prevent further interaction",
        "steps": [
            "Do not reply, click links, open attachments, scan QR codes, or call numbers in the message.",
            "Verify the claim independently using the organisation's official app, a website you type yourself, or a number from your card or statement.",
            "Block and report the sender in the messaging or email app.",
            "Keep a screenshot or copy if you may need to report it; avoid forwarding it to other people."
        ],
        "report": "If money or sensitive information was involved, switch to the matching response option and act promptly."
    },
    "clicked": {
        "title": "You clicked a link",
        "priority": "Stop interaction and check for exposure",
        "steps": [
            "Close the page. Do not download files, install profiles/apps, allow notifications, or enter any information.",
            "If you typed a password, OTP, card detail, or UPI PIN, treat it as exposed and use the matching response option below.",
            "Check your device's downloads and recently installed apps; run its built-in security scan and update the browser and operating system.",
            "Watch for unexpected sign-in alerts and transactions. Use the service's official app or website—not the message link—to review your account."
        ],
        "report": "A click alone does not prove your device or account was compromised. Act on any information you entered or software you installed."
    },
    "shared_credentials": {
        "title": "You shared a password, OTP, PIN, or banking detail",
        "priority": "Urgent — secure the affected account",
        "steps": [
            "From a trusted device, open the service's official app or type its official website yourself. Change any exposed password immediately.",
            "Sign out other sessions where available, revoke unknown devices or app access, and enable multi-factor authentication.",
            "If a bank, card, wallet, UPI PIN, banking password, or OTP was exposed, contact your bank/payment provider immediately using its official number and ask them to secure the account.",
            "Review recent account activity and transactions. Never share another OTP/PIN with someone claiming to help you recover the account."
        ],
        "report": "If money may have been lost in India, call 1930 promptly and submit a report at cybercrime.gov.in."
    },
    "sent_money": {
        "title": "You sent money or noticed an unauthorised transaction",
        "priority": "Urgent — contact your financial provider now",
        "steps": [
            "Call your bank, card issuer, or payment app using its official app or the number on your card/statement. Report the transaction and request an immediate hold or recall where possible.",
            "In India, call the cyber-fraud helpline 1930 as soon as possible and submit the complaint at https://cybercrime.gov.in/.",
            "Save the transaction/reference ID, amount, time, recipient details, messages, and screenshots for the bank and authorities.",
            "Change exposed credentials from a trusted device and ask the provider to block or secure affected cards, accounts, or UPI access.",
            "Do not pay anyone who promises guaranteed recovery of your money."
        ],
        "report": "Speed matters, but recovery is not guaranteed. Use official bank and government reporting channels only."
    },
    "installed_app": {
        "title": "You installed an unfamiliar app or file",
        "priority": "Contain possible device access",
        "steps": [
            "If you suspect remote access or the app is controlling the device, disconnect it from Wi-Fi/mobile data and do not use it for banking.",
            "From a different trusted device, contact your bank/payment provider if financial apps or accounts may be exposed; change passwords and revoke active sessions.",
            "Review recently installed apps and unusual accessibility, device-admin, VPN, or screen-sharing permissions. Remove the suspicious app if you can do so safely.",
            "Update the operating system and run a reputable built-in security scan. If suspicious control persists, seek trusted technical support before using the device for sensitive tasks."
        ],
        "report": "If money was transferred or banking credentials were exposed, also use the urgent financial-fraud steps."
    },
    "shared_screen": {
        "title": "You shared your screen or allowed remote access",
        "priority": "End access and protect accounts",
        "steps": [
            "End the call/session and disconnect remote access. Disable screen-sharing or remote-control permissions for the unfamiliar app.",
            "From a separate trusted device, contact your bank/payment provider if you opened banking/payment apps during the session.",
            "Change exposed passwords, sign out other sessions, revoke unknown devices, and review recent transactions.",
            "Uninstall unfamiliar remote-access apps and check accessibility/device-admin permissions. Get trusted technical help if you cannot confirm access has ended."
        ],
        "report": "If funds were taken or a transfer was induced, contact your provider immediately and report it through the official cybercrime channels."
    }
}


def build_response_plan(scenario: str) -> Dict[str, object]:
    """Return a fresh, non-persistent playbook for a validated scenario."""
    if scenario not in PLAYBOOKS:
        raise ValueError("Choose one of the listed incident scenarios.")
    playbook = PLAYBOOKS[scenario]
    return {
        "scenario": scenario,
        "title": str(playbook["title"]),
        "priority": str(playbook["priority"]),
        "steps": list(playbook["steps"]),
        "report": str(playbook["report"]),
        "privacy": "This response plan is generated locally from the selected scenario and is not saved by the server."
    }
