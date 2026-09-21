from collections.abc import Mapping
from typing import Any

from workflows.classify_and_route_llm import classify_email


async def classify_routing_email(state: dict[str, Any]) -> dict[str, Any]:
	if state.get("classification_supplied"):
		return {}
	classification = await classify_email(state["email"])
	return classification


async def run_spam_subgraph(state: dict[str, Any]) -> dict[str, Any]:
	from workflows.spam_subgraph.spam_nodes import prepare_spam_email

	result = await prepare_spam_email({
		**state["email"],
		**state.get("spam_context", {}),
		**state,
	})
	return {"result": result}


async def run_general_subgraph(state: dict[str, Any]) -> dict[str, Any]:
	from workflows.general_subgraph.general_nodes import prepare_general_email

	result = await prepare_general_email({**state["email"], **state})
	return {"result": result}


async def keep_unhandled_email(state: dict[str, Any]) -> dict[str, Any]:
	return {"result": dict(state["email"])}
