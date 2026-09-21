from typing import Any

from workflows.classify_and_route_llm import classify_email


def classify_email_node(state: dict[str, Any]) -> dict[str, Any]:
    result = classify_email(
        subject=state.get("subject", ""),
        body=state.get("email_content", state.get("body", "")),
    )

    return {
        "category": result.category,
        "reasoning": result.reasoning,
    }