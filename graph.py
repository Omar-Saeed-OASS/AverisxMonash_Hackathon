from typing import Any, TypedDict

from langgraph.graph import StateGraph, START, END

from nodes import classify_email_node


class EmailState(TypedDict, total=False):
    email_id: str
    sender_email: str
    subject: str
    body: str
    attachments: list

    category: str
    reasoning: str


def route_email(state: EmailState) -> str:
    """
    Decide which workflow should run after classification.
    """

    category = state.get("category")

    if category == "BL_COMPARISON":
        return "bl_comparison"

    if category == "SI_REQUEST":
        return "si_request"

    if category == "INVOICE_QUERY":
        return "invoice_query"

    if category == "SPAM":
        return "spam"

    return "general"


def build_graph():

    builder = StateGraph(EmailState)

    # 1. Classification node
    builder.add_node("classify", classify_email_node)

    # 2. Future workflow nodes
    builder.add_node("bl_comparison", lambda state: state)
    builder.add_node("si_request", lambda state: state)
    builder.add_node("invoice_query", lambda state: state)
    builder.add_node("spam", lambda state: state)
    builder.add_node("general", lambda state: state)

    # START → classifier
    builder.add_edge(START, "classify")

    # classifier → conditional routing
    builder.add_conditional_edges(
        "classify",
        route_email,
        {
            "bl_comparison": "bl_comparison",
            "si_request": "si_request",
            "invoice_query": "invoice_query",
            "spam": "spam",
            "general": "general",
        },
    )

    # Temporary endpoints
    builder.add_edge("bl_comparison", END)
    builder.add_edge("si_request", END)
    builder.add_edge("invoice_query", END)
    builder.add_edge("spam", END)
    builder.add_edge("general", END)

    return builder.compile()


graph = build_graph()