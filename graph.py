from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from nodes import run_router_subgraph


class MainGraphState(TypedDict, total=False):
	email: dict[str, Any]
	spam_context: dict[str, Any]
	classification: dict[str, Any]
	result: dict[str, Any]


def build_main_graph():
	graph = StateGraph(MainGraphState)
	graph.add_node("route_email", run_router_subgraph)
	graph.add_edge(START, "route_email")
	graph.add_edge("route_email", END)
	return graph.compile()


main_graph = build_main_graph()


async def route_email(
	email: dict[str, Any],
	spam_context: dict[str, Any] | None = None,
	classification: dict[str, Any] | None = None,
) -> dict[str, Any]:
	state: MainGraphState = {
		"email": dict(email),
		"spam_context": dict(spam_context or {}),
	}
	if classification:
		state["classification"] = dict(classification)
	result = await main_graph.ainvoke(state)
	return {
		**email,
		**result,
		**result.get("result", {}),
		"attachments": email.get("attachments", []),
	}
