from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from nodes import (
	classify_routing_email,
	keep_unhandled_email,
	run_general_subgraph,
	run_spam_subgraph,
)


EmailCategory = Literal[
	"BL_COMPARISON",
	"SI_REQUEST",
	"INVOICE_QUERY",
	"GENERAL",
	"SPAM",
]


class RoutingState(TypedDict, total=False):
	email: dict[str, Any]
	spam_context: dict[str, Any]
	classification_supplied: bool
	category: EmailCategory
	confidence: float
	routing_reasoning: str
	classification_source: str
	result: dict[str, Any]


def route_category(state: RoutingState) -> str:
	category = state.get("category")
	if category == "SPAM":
		return "spam"
	if category in {"GENERAL", "SI_REQUEST", "INVOICE_QUERY"}:
		return "general"
	return "unhandled"


def build_routing_graph():
	graph = StateGraph(RoutingState)
	graph.add_node("classify_email", classify_routing_email)
	graph.add_node("run_spam_subgraph", run_spam_subgraph)
	graph.add_node("run_general_subgraph", run_general_subgraph)
	graph.add_node("keep_unhandled_email", keep_unhandled_email)
	graph.add_edge(START, "classify_email")
	graph.add_conditional_edges(
		"classify_email",
		route_category,
		{
			"spam": "run_spam_subgraph",
			"general": "run_general_subgraph",
			"unhandled": "keep_unhandled_email",
		},
	)
	graph.add_edge("run_spam_subgraph", END)
	graph.add_edge("run_general_subgraph", END)
	graph.add_edge("keep_unhandled_email", END)
	return graph.compile()


routing_graph = build_routing_graph()


async def route_email(
	email: dict[str, Any],
	spam_context: dict[str, Any] | None = None,
	classification: dict[str, Any] | None = None,
) -> dict[str, Any]:
	initial_state: RoutingState = {
		"email": dict(email),
		"spam_context": dict(spam_context or {}),
	}
	if classification:
		initial_state.update(classification)
		initial_state["classification_supplied"] = True
	result = await routing_graph.ainvoke(initial_state)
	return {**email, **result, **result.get("result", {})}
