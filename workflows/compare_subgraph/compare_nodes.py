import asyncio
import logging
from typing import Dict, Any
from langchain_core.runnables.config import RunnableConfig

# --- Existing Services ---
from services.file_ingestion import ingest_document
from services.extractor import extract_shipment_data
from services.vision_ocr import transcribe_scanned_pdf
from database_manager import DBManager

# --- Services to Implement Next ---
from services.normalizer import normalize_extracted_data
from services.comparator import compare_documents
# from services.intelligence_layer import generate_risk_report

logger = logging.getLogger(__name__)
db_manager = DBManager()


async def preflight_node(state: CompareState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Identifies document roles (SI vs BL).
    Injects NEEDS_REVIEW instantly if attachments are missing.
    """
    attachments = state.get("attachments", [])

    if not attachments or len(attachments) < 2:
        return {
            "status": "NEEDS_REVIEW",
            "review_reason": "missing_attachment",
            "has_defect": False,
            "defect_fields": []
        }

    si_path, bl_path = None, None
    for path in attachments:
        upper_path = path.upper()
        if "_SI" in upper_path:
            si_path = path
        elif "_BL" in upper_path:
            bl_path = path

    # Fallback to sequential assuming 1st is SI, 2nd is BL
    if not si_path or not bl_path:
        si_path, bl_path = attachments[0], attachments[1]

    return {"si_path": si_path, "bl_path": bl_path}


async def file_read_node(state: CompareState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Downloads files concurrently, parses them, and falls back to OCR if scanned.
    Injects NEEDS_REVIEW if files are fundamentally corrupted.
    """
    si_path = state["si_path"]
    bl_path = state["bl_path"]

    try:
        si_bytes, bl_bytes = await asyncio.gather(
            db_manager.download_file_bytes(db_manager.bucket, si_path),
            db_manager.download_file_bytes(db_manager.bucket, bl_path)
        )

        si_ext = f".{si_path.split('.')[-1]}" if "." in si_path else ""
        bl_ext = f".{bl_path.split('.')[-1]}" if "." in bl_path else ""

        # Standard Ingestion
        si_res = await asyncio.to_thread(ingest_document, si_ext, si_bytes)
        bl_res = await asyncio.to_thread(ingest_document, bl_ext, bl_bytes)

        # Vision OCR Fallback for scanned documents
        if si_res.get("is_scanned"):
            si_res = await transcribe_scanned_pdf(si_bytes)
        if bl_res.get("is_scanned"):
            bl_res = await transcribe_scanned_pdf(bl_bytes)

        # Guardrail: Total failure or 0-byte
        if si_res.get("error") or bl_res.get("error"):
            return {
                "status": "NEEDS_REVIEW",
                "review_reason": "unreadable",
                "has_defect": False,
                "defect_fields": []
            }

        return {
            "si_text": si_res.get("content", ""),
            "bl_text": bl_res.get("content", "")
        }

    except Exception as e:
        logger.error(f"Download/Parse failed: {e}")
        return {
            "status": "NEEDS_REVIEW",
            "review_reason": "unreadable",
            "has_defect": False,
            "defect_fields": []
        }


async def extractor_node(state: CompareState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Calls Gemini concurrently to extract fields.
    Injects NEEDS_REVIEW if documents are invalid types or values are '???'.
    """
    si_res, bl_res = await asyncio.gather(
        extract_shipment_data(state.get("si_text", "")),
        extract_shipment_data(state.get("bl_text", ""))
    )

    si_data = si_res.get("data") or {}
    bl_data = bl_res.get("data") or {}

    # Invoice / Packing List Guardrail
    if not si_data.get("is_valid_doc") or not bl_data.get("is_valid_doc"):
        return {
            "status": "NEEDS_REVIEW",
            "review_reason": "wrong_doc_type",
            "has_defect": False,
            "defect_fields": []
        }

    # Missing Value Guardrail ('???', 'TBA')
    required_keys = [
        "shipper", "consignee", "notify_party", "port_of_loading",
        "port_of_discharge", "container_count", "raw_weight_value"
    ]
    for key in required_keys:
        if si_data.get(key) is None or bl_data.get(key) is None:
            return {
                "status": "NEEDS_REVIEW",
                "review_reason": "missing_value",
                "has_defect": False,
                "defect_fields": []
            }

    return {
        "si_extracted": si_data,
        "bl_extracted": bl_data
    }


async def normalize_node(state: CompareState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Cleans strings and mathematically resolves weight tuples into KG.
    """
    si_clean = normalize_extracted_data(state.get("si_extracted", {}))
    bl_clean = normalize_extracted_data(state.get("bl_extracted", {}))

    return {
        "si_extracted": si_clean,
        "bl_extracted": bl_clean
    }


async def compare_node(state: CompareState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Runs deterministic fuzzy matching logic across the 7 fields.
    Updates the final MISMATCH / OK status.
    """

    # comparator.py will handle RapidFuzz token sorting and exact match checks
    result = compare_documents(
        state.get("si_extracted", {}),
        state.get("bl_extracted", {})
    )

    return {
        "status": result.get("status", "OK"),
        "has_defect": result.get("has_defect", False),
        "defect_fields": result.get("defect_fields", []),
        "discrepancy_details": result.get("discrepancy_details", [])
    }

async def intelligence_node(state: CompareState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Asynchronous enterprise capabilities: HS Codes, compliance flags,
    and predictive tariffs applied to the final BL data.
    """
    pass

#     risk_report = await generate_risk_report(state.get("bl_extracted", {}))
#
#     return {
#         "enterprise_risk_report": risk_report
#     }