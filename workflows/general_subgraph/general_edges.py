from langgraph.graph import END, START, StateGraph

from .general_nodes import analyze_general_email, format_general_output, normalize_email
from .general_state import GeneralEmailState


def build_general_graph():
    graph = StateGraph(GeneralEmailState)
    graph.add_node("normalize_email", normalize_email)
    graph.add_node("analyze_general_email", analyze_general_email)
    graph.add_node("format_general_output", format_general_output)
    graph.add_edge(START, "normalize_email")
    graph.add_edge("normalize_email", "analyze_general_email")
    graph.add_edge("analyze_general_email", "format_general_output")
    graph.add_edge("format_general_output", END)
    return graph.compile()
