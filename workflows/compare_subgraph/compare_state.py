from typing import TypedDict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from schemas import ShipmentExtractionSchema


class DiscrepancyDetail(BaseModel):
    field: str = Field(description="The exact name of the field that mismatched.")
    si_value: Any = Field(description="The normalized value extracted from the SI.")
    bl_value: Any = Field(description="The normalized value extracted from the BL.")
    delta: Optional[str] = Field(default=None, description="The mathematical or textual difference (e.g., '+2000 kg').")

class CompareState(TypedDict):
    # Inputs from Parent Graph
    email_id: str
    attachments: List[str]

    # Preflight & Ingestion Memory
    si_path: Optional[str]
    bl_path: Optional[str]
    si_text: Optional[str]
    bl_text: Optional[str]

    # Extraction Memory
    si_extracted: Optional[ShipmentExtractionSchema]
    bl_extracted: Optional[ShipmentExtractionSchema]

    # Scoring & Evaluation Outputs
    status: Optional[Literal["OK", "MISMATCH", "NEEDS_REVIEW"]]
    review_reason: Optional[Literal["wrong_doc_type", "missing_attachment", "unreadable", "missing_value"]]
    has_defect: Optional[bool]
    defect_fields: Optional[List[str]]

    # Extensions (UI & Custom Features)
    discrepancy_details: Optional[List[DiscrepancyDetail]]
    enterprise_risk_report: Optional[dict]