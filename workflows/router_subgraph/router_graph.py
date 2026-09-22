from langgraph.graph import END, START, StateGraph

from .router_edges import route_category
from .router_nodes import (
    classify_routing_email,
    keep_unhandled_email,
    run_compare_subgraph,
    run_general_subgraph,
    run_spam_subgraph,
)
from .router_state import RouterState


def build_router_graph():
    graph = StateGraph(RouterState)
    graph.add_node("classify_email", classify_routing_email)
    graph.add_node("run_spam_subgraph", run_spam_subgraph)
    graph.add_node("run_general_subgraph", run_general_subgraph)
    graph.add_node("run_compare_subgraph", run_compare_subgraph)
    graph.add_node("keep_unhandled_email", keep_unhandled_email)
    graph.add_edge(START, "classify_email")
    graph.add_conditional_edges(
        "classify_email",
        route_category,
        {
            "spam": "run_spam_subgraph",
            "general": "run_general_subgraph",
            "compare": "run_compare_subgraph",
            "unhandled": "keep_unhandled_email",
        },
    )
    graph.add_edge("run_spam_subgraph", END)
    graph.add_edge("run_general_subgraph", END)
    graph.add_edge("run_compare_subgraph", END)
    graph.add_edge("keep_unhandled_email", END)
    return graph.compile()


router_graph = build_router_graph()