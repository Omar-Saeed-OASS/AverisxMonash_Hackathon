from typing import Any

from workflows.router_subgraph.router_graph import router_graph


async def run_router_subgraph(state: dict[str, Any]) -> dict[str, Any]:
	router_state = {
		"email": state["email"],
		"spam_context": state.get("spam_context", {}),
	}
	if state.get("classification"):
		router_state.update(state["classification"])
		router_state["classification_supplied"] = True

	result = await router_graph.ainvoke(router_state)
	return {"result": {**result, **result.get("result", {})}}
