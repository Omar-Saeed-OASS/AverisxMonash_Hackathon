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
    shipper: Optional[str] = Field(description="Name of the shipper. Null if missing.")
    consignee: Optional[str] = Field(description="Name of the consignee. Null if missing.")
    notify_party: Optional[str] = Field(description="Name of the notify party. Null if missing.")
    port_of_loading: Optional[str] = Field(description="The origin port of loading. Null if missing.")
    port_of_discharge: Optional[str] = Field(description="The destination port of discharge. Null if missing.")
    container_count: Optional[int] = Field(description="The total number of containers as an integer. Null if missing.")
    gross_weight_kg: Optional[float] = Field(description="The gross weight converted strictly to kilograms. Null if missing.")