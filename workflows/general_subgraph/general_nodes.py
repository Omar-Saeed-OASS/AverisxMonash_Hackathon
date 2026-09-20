import asyncio
import json
import os
import re
from collections.abc import Mapping
from typing import Any

from dotenv import load_dotenv

from .general_state import GeneralEmailState


load_dotenv()

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "general_email_rules.md")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
ACTION_PATTERN = re.compile(
    r"\b(?:please|kindly|can you|could you|would you|need you to|action required|follow up|follow-up|respond|reply|send|provide|confirm|review|complete|submit)\b",
    re.IGNORECASE,
)
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+|\r?\n+")


async def normalize_email(state: GeneralEmailState) -> dict[str, Any]:
    body = state.get("body") or ""
    return {
        "normalized_body": " ".join(body.split()),
        "subject": " ".join((state.get("subject") or "").split()),
        "category": "GENERAL",
        "word_count": len(body.split()),
    }


def _sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in SENTENCE_PATTERN.split(text) if sentence.strip()]


def _fallback_analysis(state: GeneralEmailState) -> dict[str, Any]:
    body = state.get("normalized_body", "")
    subject = state.get("subject", "")
    sentences = _sentences(body)
    action_items = [sentence for sentence in sentences if ACTION_PATTERN.search(sentence)]
    summary = " ".join(sentences[:2]) or (
        f"Email with subject '{subject}' has no body content." if subject else "Email has no body content."
    )
    return {
        "summary": summary[:280],
        "key_points": "; ".join(sentences[:5]) or (f"Subject: {subject}" if subject else "None identified"),
        "action_items": "; ".join(action_items) or "None identified",
        "requires_response": "Yes" if action_items else "No",
        "priority": "medium" if action_items else "low",
        "sentiment": "neutral",
        "language": "unknown",
        "entities": "None identified",
        "deadlines": "None identified",
        "risks": "None identified",
        "suggested_reply": "",
        "confidence": 0.35,
        "analysis_source": "local_fallback",
    }


def _load_rules() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as prompt_file:
        return prompt_file.read()


def _gemini_analysis(state: GeneralEmailState) -> dict[str, Any]:
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
    }
    schema = {
        "type": "object",
        "required": [
            "summary", "key_points", "action_items", "requires_response",
            "priority", "sentiment", "language", "entities", "deadlines",
            "risks", "suggested_reply", "confidence",
        ],
        "properties": {
            "summary": {"type": "string"},
            "key_points": {"type": "string"},
            "action_items": {"type": "string"},
            "requires_response": {"type": "string", "enum": ["Yes", "No"]},
            "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
            "sentiment": {"type": "string"},
            "language": {"type": "string"},
            "entities": {"type": "string"},
            "deadlines": {"type": "string"},
            "risks": {"type": "string"},
            "suggested_reply": {"type": "string"},
            "confidence": {"type": "number"},
        },
    }
    chat = client.chats.create(
        model=DEFAULT_MODEL,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    response = chat.send_message(
        f"{_load_rules()}\n\nEMAIL JSON:\n{json.dumps(email, ensure_ascii=False)}"
    )
    result = json.loads(response.text)
    result["analysis_source"] = f"gemini:{DEFAULT_MODEL}"
    return result


async def analyze_general_email(state: GeneralEmailState) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(_gemini_analysis, state)
    except Exception as exc:
        print(f"General email Gemini analysis unavailable; using fallback: {exc}", flush=True)
        return _fallback_analysis(state)


async def format_general_output(state: GeneralEmailState) -> dict[str, Any]:
    display_text = (
        f"Summary: {state.get('summary', 'No summary available.')} "
        f"Key points: {state.get('key_points', 'None identified')} "
        f"Action items: {state.get('action_items', 'None identified')} "
        f"Response required: {state.get('requires_response', 'No')}."
    )
    return {"display_text": display_text}


async def prepare_general_email(email: Mapping[str, Any]) -> GeneralEmailState:
    """Run the general-email graph using a router email record."""
    from .general_graph import general_graph

    return await general_graph.ainvoke(dict(email))
