from langgraph.graph import END, START, StateGraph

from .spam_nodes import analyze_spam_email, apply_spam_policy, normalize_spam_email
from .spam_state import SpamEmailState


def build_spam_graph():
    graph = StateGraph(SpamEmailState)
    graph.add_node("normalize_spam_email", normalize_spam_email)
    graph.add_node("analyze_spam_email", analyze_spam_email)
    graph.add_node("apply_spam_policy", apply_spam_policy)
    graph.add_edge(START, "normalize_spam_email")
    graph.add_edge("normalize_spam_email", "analyze_spam_email")
    graph.add_edge("analyze_spam_email", "apply_spam_policy")
    graph.add_edge("apply_spam_policy", END)
    return graph.compile()
