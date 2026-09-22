from typing import Any, Literal, TypedDict


EmailCategory = Literal[
    "BL_COMPARISON",
    "SI_REQUEST",
    "INVOICE_QUERY",
    "GENERAL",
    "SPAM",
]


class RouterState(TypedDict, total=False):
    email: dict[str, Any]
    spam_context: dict[str, Any]
    classification_supplied: bool
    category: EmailCategory
    confidence: float
    routing_reasoning: str
    classification_source: str
    result: dict[str, Any]