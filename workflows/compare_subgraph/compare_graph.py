from langgraph.graph import END, START, StateGraph

from . import compare_edges, compare_nodes
from .compare_state import CompareState

def build_compare_subgraph():
    """
    Assembles and compiles the document comparison state machine.
    """
    # Initialize the Graph with the TypedDict state
    workflow = StateGraph(CompareState)

    # Add all execution nodes
    workflow.add_node("preflight_node", compare_nodes.preflight_node)
    workflow.add_node("file_read_node", compare_nodes.file_read_node)
    workflow.add_node("extractor_node", compare_nodes.extractor_node)
    workflow.add_node("normalize_node", compare_nodes.normalize_node)
    workflow.add_node("compare_node", compare_nodes.compare_node)
    workflow.add_node("intelligence_node", compare_nodes.intelligence_node)

    # Define the Entry Point
    workflow.add_edge(START, "preflight_node")

    # Add Conditional Edges (The "Interrupts" to END)
    workflow.add_conditional_edges("preflight_node", compare_edges.route_preflight)
    workflow.add_conditional_edges("file_read_node", compare_edges.route_file_read)
    workflow.add_conditional_edges("extractor_node", compare_edges.route_extractor)

    # Add Linear Edges (The main execution path)
    workflow.add_edge("normalize_node", "compare_node")
    workflow.add_edge("compare_node", "intelligence_node")
    workflow.add_edge("intelligence_node", END)

    # Compile the executable graph
    # (Optional: Pass checkpointer=MemorySaver() here later for HITL pauses)
    return workflow.compile()

# Export the compiled subgraph so it can be invoked by your FastAPI router
compare_subgraph = build_compare_subgraph()