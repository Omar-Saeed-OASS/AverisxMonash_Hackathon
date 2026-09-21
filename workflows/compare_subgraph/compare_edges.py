from typing import Literal
from langgraph.graph import END
from .compare_state import CompareState

def route_preflight(state: CompareState) -> Literal["file_read_node", "__end__"]:
    """
    Checks if the preflight node flagged a missing attachment error.
    If so, terminates the graph early. Otherwise, proceeds to read the files.
    """
    if state.get("status") == "NEEDS_REVIEW":
        return END
    return "file_read_node"

def route_file_read(state: CompareState) -> Literal["extractor_node", "__end__"]:
    """
    Checks if the file read node flagged an unreadable or corrupted file.
    If so, terminates the graph early. Otherwise, proceeds to extraction.
    """
    if state.get("status") == "NEEDS_REVIEW":
        return END
    return "extractor_node"

def route_extractor(state: CompareState) -> Literal["normalize_node", "__end__"]:
    """
    Checks if the extractor node flagged a wrong document type or missing values.
    If so, terminates the graph early. Otherwise, proceeds to normalization.
    """
    if state.get("status") == "NEEDS_REVIEW":
        return END
    return "normalize_node"