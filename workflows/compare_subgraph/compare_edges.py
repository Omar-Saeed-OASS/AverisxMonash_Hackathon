from typing import Literal
from langgraph.graph import END
from .compare_state import CompareState

def route_preflight(state: CompareState) -> Literal["file_read_node", "db_save_node"]:
    if state.get("status") == "NEEDS_REVIEW":
        return "db_save_node"
    return "file_read_node"

def route_file_read(state: CompareState) -> Literal["extractor_node", "db_save_node"]:
    if state.get("status") == "NEEDS_REVIEW":
        return "db_save_node"
    return "extractor_node"

def route_extractor(state: CompareState) -> Literal["normalize_node", "db_save_node"]:
    if state.get("status") == "NEEDS_REVIEW":
        return "db_save_node"
    return "normalize_node"