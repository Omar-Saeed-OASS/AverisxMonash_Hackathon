from langgraph.graph import StateGraph, END
from .compare_state import CompareState
from . import compare_nodes
from . import compare_edges

def build_compare_subgraph():
    workflow = StateGraph(CompareState)

    # Add all execution nodes + the new persistent node
    workflow.add_node("preflight_node", compare_nodes.preflight_node)
    workflow.add_node("file_read_node", compare_nodes.file_read_node)
    workflow.add_node("extractor_node", compare_nodes.extractor_node)
    workflow.add_node("normalize_node", compare_nodes.normalize_node)
    workflow.add_node("compare_node", compare_nodes.compare_node)
    workflow.add_node("intelligence_node", compare_nodes.intelligence_node)
    workflow.add_node("db_save_node", compare_nodes.db_save_node)

    # Define the Entry Point
    workflow.set_entry_point("preflight_node")

    # Add Conditional Edges (Now routing errors to db_save_node)
    workflow.add_conditional_edges("preflight_node", compare_edges.route_preflight)
    workflow.add_conditional_edges("file_read_node", compare_edges.route_file_read)
    workflow.add_conditional_edges("extractor_node", compare_edges.route_extractor)

    # Add Linear Edges
    workflow.add_edge("normalize_node", "compare_node")
    workflow.add_edge("compare_node", "intelligence_node")

    # The Funnel: Success path goes to DB save, DB save goes to END
    workflow.add_edge("intelligence_node", "db_save_node")
    workflow.add_edge("db_save_node", END)

    return workflow.compile()


compare_subgraph = build_compare_subgraph()