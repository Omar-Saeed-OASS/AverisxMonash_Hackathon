from .router_state import RouterState


def route_category(state: RouterState) -> str:
    category = state.get("category")
    if category == "SPAM":
        return "spam"
    if category == "BL_COMPARISON":
        return "compare"
    if category in {"GENERAL", "SI_REQUEST", "INVOICE_QUERY"}:
        return "general"
    return "unhandled"