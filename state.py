from typing import TypedDict, List, Optional, Literal, Dict, Any


class GraphState(TypedDict):
    # Raw Input Data
    email_id: str
    sender_email: Optional[str]
    email_content: str
    attachments: List[Dict[str, Any]]

    # Router Classification
    category: Optional[Literal[
        "BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"
    ]]

    #  Evaluation Output
    status: Optional[Literal["OK", "MISMATCH", "NEEDS_REVIEW"]]
    has_defect: Optional[bool]
    defect_fields: Optional[List[str]]
    review_reason: Optional[Literal[
        "wrong_doc_type", "missing_attachment", "unreadable", "missing_value"
    ]]

    # Internal Memory for HITL
    si_extracted_data: Optional[Dict[str, Any]]
    bl_extracted_data: Optional[Dict[str, Any]]
    routing_reasoning: Optional[str]  # Logs why the router chose a specific category

    # Operational details
    confidence_score: Optional[float]
    retry_count: int = 0

    # human_feedback: Optional[str]