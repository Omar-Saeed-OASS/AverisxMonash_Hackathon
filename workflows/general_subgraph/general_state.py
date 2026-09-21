from typing import Any, TypedDict


class GeneralEmailState(TypedDict, total=False):
    email_id: str
    from_name: str
    from_email: str
    received_at: str
    subject: str
    body: str

    normalized_body: str
    summary: str
    key_points: str
    action_items: str
    requires_response: str
    word_count: int
    category: str
    attachments: list[dict[str, Any]]
    priority: str
    sentiment: str
    language: str
    entities: str
    deadlines: str
    risks: str
    suggested_reply: str
    confidence: float
    analysis_source: str
    display_text: str
