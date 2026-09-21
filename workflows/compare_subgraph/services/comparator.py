from typing import Dict, Any
from rapidfuzz import fuzz

# 90% threshold allows for missing suffixes (e.g., "Ltd") or minor typos
FUZZY_MATCH_THRESHOLD = 90.0
# Allows for minor floating-point rounding differences in weight
WEIGHT_TOLERANCE_KG = 1.0


def compare_text(val1: Any, val2: Any) -> bool:
    """Uses Token Sort Ratio to compare strings regardless of word order/casing."""
    if not val1 and not val2:
        return True
    if not val1 or not val2:
        return False

    # Token sort ratio alphabetizes words before comparing
    score = fuzz.token_sort_ratio(str(val1), str(val2))
    return score >= FUZZY_MATCH_THRESHOLD


def compare_numeric(val1: Any, val2: Any, tolerance: float) -> bool:
    """Compares numbers allowing for a defined tolerance."""
    if val1 is None and val2 is None:
        return True
    if val1 is None or val2 is None:
        return False

    try:
        return abs(float(val1) - float(val2)) <= tolerance
    except ValueError:
        return False


def compare_documents(si_data: Dict[str, Any], bl_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically compares SI and BL data.
    Returns the exact schema required for the LangGraph state.
    """
    defect_fields = []
    discrepancy_details = []

    # Compare Text Fields
    text_fields = [
        "shipper", "consignee", "notify_party",
        "port_of_loading", "port_of_discharge"
    ]

    for field in text_fields:
        si_val = si_data.get(field)
        bl_val = bl_data.get(field)

        if not compare_text(si_val, bl_val):
            defect_fields.append(field)
            discrepancy_details.append({
                "field": field,
                "si_value": si_val,
                "bl_value": bl_val,
                "delta": "Text mismatch"
            })

    # Compare Container Count (Strict Equality)
    si_count = si_data.get("container_count")
    bl_count = bl_data.get("container_count")

    if not compare_numeric(si_count, bl_count, tolerance=0.0):
        defect_fields.append("container_count")

        # Calculate strict mathematical delta
        if si_count is not None and bl_count is not None:
            delta = f"{int(bl_count) - int(si_count):+d} containers"
        else:
            delta = "Missing value"

        discrepancy_details.append({
            "field": "container_count",
            "si_value": si_count,
            "bl_value": bl_count,
            "delta": delta
        })

    # Compare Gross Weight (Tolerance-based)
    si_weight = si_data.get("gross_weight_kg")
    bl_weight = bl_data.get("gross_weight_kg")

    if not compare_numeric(si_weight, bl_weight, tolerance=WEIGHT_TOLERANCE_KG):
        defect_fields.append("gross_weight_kg")

        # Calculate strict mathematical delta
        if si_weight is not None and bl_weight is not None:
            delta = f"{float(bl_weight) - float(si_weight):+.2f} kg"
        else:
            delta = "Missing value"

        discrepancy_details.append({
            "field": "gross_weight_kg",
            "si_value": si_weight,
            "bl_value": bl_weight,
            "delta": delta
        })

    # Final Aggregation
    has_defect = len(defect_fields) > 0

    return {
        "status": "MISMATCH" if has_defect else "OK",
        "has_defect": has_defect,
        "defect_fields": defect_fields,
        "discrepancy_details": discrepancy_details
    }