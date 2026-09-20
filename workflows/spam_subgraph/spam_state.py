from typing import Any, TypedDict


class SpamEmailState(TypedDict, total=False):
    email_id: str
    from_name: str
    from_email: str
    received_at: str
    subject: str
    body: str
    attachments: list[dict[str, Any]]

    normalized_body: str
    spam_score: float
    is_spam: bool
    spam_reasons: str
    risk_signals: str
    recommended_action: str
    spam_reason: str
    confidence: float
    analysis_source: str
    blacklist_threshold: int
    spam_count: int
    is_blacklisted: bool
    blacklist_reason: str
    blacklist_status: str
    display_text: str
