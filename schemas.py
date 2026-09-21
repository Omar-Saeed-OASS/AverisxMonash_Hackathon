from pydantic import BaseModel, Field
from typing import Literal, Optional


class EmailRouterSchema(BaseModel):
    category: Literal[
        "BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"
    ] = Field(description="The exact category of the email intent.")

    reasoning: str = Field(
        description="A one-sentence justification for the chosen category."
    )


class ShipmentExtractionSchema(BaseModel):
    is_valid_doc: bool = Field(
        description="True if document is a Bill of Lading (BL) or Shipping Instruction (SI). False if it is a Commercial Invoice, Packing List, or Certificate of Origin."
    )
    shipper: Optional[str] = Field(description="Name of the shipper. Null if missing, '???', 'TBA', or '_______'.")
    consignee: Optional[str] = Field(
        description="Name of the consignee. Null if missing, '???', 'TBA', or '_______'.")
    notify_party: Optional[str] = Field(
        description="Name of the notify party. Null if missing, '???', 'TBA', or '_______'.")
    port_of_loading: Optional[str] = Field(description="Origin port. Null if missing, '???', 'TBA', or '_______'.")
    port_of_discharge: Optional[str] = Field(
        description="Destination port. Null if missing, '???', 'TBA', or '_______'.")
    container_count: Optional[int] = Field(
        description="Total number of containers as an integer. Null if missing, '???', 'TBA', or '_______'.")

    # Used to normalize the weight
    raw_weight_value: Optional[float] = Field(
        description="The numerical value of the gross weight exactly as written. Null if missing or '???'."
    )
    raw_weight_unit: Optional[str] = Field(
        description="The exact text of the unit of measurement (e.g., 'MT', 'KGS', 'LBS', 'Tonnes'). Null if missing."
    )