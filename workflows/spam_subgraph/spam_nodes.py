import asyncio
import json
import os
import re
from collections.abc import Mapping
from typing import Any

from dotenv import load_dotenv

from .spam_state import SpamEmailState


load_dotenv()
PROMPT_PATH = os.path.join(os.path.dirname(__file__), "spam_email_rules.md")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
BLACKLIST_THRESHOLD = int(os.getenv("SPAM_BLACKLIST_THRESHOLD", "3"))
URL_PATTERN = re.compile(r"https?://|www\.|bit\.ly|tinyurl", re.IGNORECASE)
SUSPICIOUS_PATTERN = re.compile(
    r"password|verify your account|urgent payment|gift card|wire transfer|crypto|click here|winner|claim now|act immediately",
    re.IGNORECASE,
)


async def normalize_spam_email(state: SpamEmailState) -> dict[str, Any]:
    body = state.get("body") or ""
    return {
        "normalized_body": " ".join(body.split()),
        "blacklist_threshold": state.get("blacklist_threshold", BLACKLIST_THRESHOLD),
    }


def _load_rules() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as prompt_file:
        return prompt_file.read()


def _fallback_analysis(state: SpamEmailState) -> dict[str, Any]:
    text = f"{state.get('subject', '')} {state.get('normalized_body', '')}"
    signals: list[str] = []
    if URL_PATTERN.search(text):
        signals.append("contains_link_or_url")
    suspicious_matches = SUSPICIOUS_PATTERN.findall(text)
    if suspicious_matches:
        signals.append("contains_common_spam_or_phishing_language")
    if len(suspicious_matches) >= 2:
        signals.append("multiple_high_risk_phrases")
    if text.count("!") >= 3:
        signals.append("excessive_exclamation_marks")
    score = min(0.95, 0.25 + 0.25 * len(signals))
    is_spam = score >= 0.65
    action = "reject" if is_spam else ("review" if signals else "allow")
    reasons = [
        "The message contains signals commonly associated with unsolicited or phishing email."
        for _ in [1]
    ] if signals else []
    return {
        "spam_score": score,
        "is_spam": is_spam,
        "spam_reasons": "; ".join(reasons) or "None identified",
        "risk_signals": "; ".join(signals) or "None identified",
        "recommended_action": action,
        "spam_reason": reasons[0] if reasons else "No strong spam indicators detected.",
        "confidence": 0.35,
        "analysis_source": "local_fallback",
    }


def _gemini_analysis(state: SpamEmailState) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=api_key)
    email = {
        "email_id": state.get("email_id", ""),
        "from_name": state.get("from_name", ""),
        "from_email": state.get("from_email", ""),
        "received_at": state.get("received_at", ""),
        "subject": state.get("subject", ""),
        "body": state.get("normalized_body", ""),
        "attachments": [
            {"filename": item.get("filename"), "content_type": item.get("content_type")}
            for item in state.get("attachments", [])
        ],
    }
    schema = {
        "type": "object",
        "required": [
            "spam_score", "is_spam", "spam_reasons", "risk_signals",
            "recommended_action", "spam_reason", "confidence",
        ],
        "properties": {
            "spam_score": {"type": "number"},
            "is_spam": {"type": "boolean"},
            "spam_reasons": {"type": "string"},
            "risk_signals": {"type": "string"},
            "recommended_action": {"type": "string", "enum": ["allow", "review", "reject"]},
            "spam_reason": {"type": "string"},
            "confidence": {"type": "number"},
        },
    }
    chat = client.chats.create(
        model=DEFAULT_MODEL,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    response = chat.send_message(
        f"{_load_rules()}\n\nEMAIL JSON:\n{json.dumps(email, ensure_ascii=False)}"
    )
    result = json.loads(response.text)
    result["spam_score"] = max(0.0, min(1.0, float(result["spam_score"])))
    result["analysis_source"] = f"gemini:{DEFAULT_MODEL}"
    return result


async def analyze_spam_email(state: SpamEmailState) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(_gemini_analysis, state)
    except Exception as exc:
        print(f"Spam Gemini analysis unavailable; using fallback: {exc}", flush=True)
        return _fallback_analysis(state)


async def apply_spam_policy(state: SpamEmailState) -> dict[str, Any]:
    previous_spam_count = int(state.get("spam_count") or 0)
    threshold = int(state.get("blacklist_threshold") or BLACKLIST_THRESHOLD)
    spam_count = previous_spam_count + (1 if state.get("is_spam", False) else 0)
    is_blacklisted = bool(state.get("is_blacklisted")) or (
        state.get("is_spam", False) and spam_count >= threshold
    )
    remaining = max(threshold - spam_count, 0)
    if is_blacklisted:
        blacklist_status = f"Sender blacklisted after reaching {spam_count}/{threshold} spam messages."
    elif state.get("is_spam", False):
        blacklist_status = (
            f"Sender is not blacklisted yet ({spam_count}/{threshold} spam messages). "
            f"{remaining} more spam message(s) will trigger the blacklist."
        )
    else:
        blacklist_status = f"Sender has {spam_count}/{threshold} spam messages and remains allowed."
    action = state.get("recommended_action", "review")
    display_text = (
        f"Spam score: {float(state.get('spam_score', 0)):.2f}. "
        f"Decision: {action}. "
        f"Reason: {state.get('spam_reason', 'No reason provided.')} "
        f"{blacklist_status}"
    )
    return {
        "spam_count": spam_count,
        "is_blacklisted": is_blacklisted,
        "blacklist_status": blacklist_status,
        "display_text": display_text,
        "blacklist_reason": (
            f"Sender reached the spam threshold of {threshold} messages"
            if is_blacklisted else ""
        ),
    }


async def prepare_spam_email(email: Mapping[str, Any]) -> SpamEmailState:
    """Run spam triage for an email record produced by the Gmail listener."""
    from .spam_graph import spam_graph

    return await spam_graph.ainvoke(dict(email))
