from .spam_edges import build_spam_graph


spam_graph = build_spam_graph()

__all__ = ["build_spam_graph", "spam_graph"]
