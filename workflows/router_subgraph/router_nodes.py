from typing import Any

from workflows.classify_and_route_llm import classify_email

from .router_state import RouterState


async def classify_routing_email(state: RouterState) -> dict[str, Any]:
    if state.get("classification_supplied"):
        return {}
    return await classify_email(state["email"])


async def run_spam_subgraph(state: RouterState) -> dict[str, Any]:
    from workflows.spam_subgraph.spam_nodes import prepare_spam_email

    result = await prepare_spam_email({
        **state["email"],
        **state.get("spam_context", {}),
        **state,
    })
    return {"result": result}


async def run_general_subgraph(state: RouterState) -> dict[str, Any]:
    from workflows.general_subgraph.general_nodes import prepare_general_email

    result = await prepare_general_email({**state["email"], **state})
    return {"result": result}


async def run_compare_subgraph(state: RouterState) -> dict[str, Any]:
    try:
        from workflows.compare_subgraph.compare_graph import compare_subgraph

        attachments = []
        for attachment in state["email"].get("attachments", []):
            if isinstance(attachment, str):
                attachments.append(attachment)
            elif isinstance(attachment, dict):
                path = attachment.get("storage_path")
                if path:
                    attachments.append(path)
        compare_input = {
            "email_id": state["email"].get("email_id", ""),
            "attachments": [path for path in attachments if path],
        }
        result = await compare_subgraph.ainvoke(compare_input)
    except Exception as exc:
        result = {
            "status": "NEEDS_REVIEW",
            "review_reason": "unreadable",
            "has_defect": False,
            "defect_fields": [],
            "comparison_error": str(exc),
        }
    return {"result": result}


async def keep_unhandled_email(state: RouterState) -> dict[str, Any]:
    return {"result": dict(state["email"])}