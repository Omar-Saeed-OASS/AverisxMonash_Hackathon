# import logging
# from typing import Optional
#
#
# def convert_weight_to_kg(value: Optional[float], unit: Optional[str]) -> Optional[float]:
#     """
#     Deterministically converts various shipping weight units into standard Kilograms.
#     Returns None if the value is missing or the unit is completely unrecognized.
#     """
#
#     if value is None:
#         return None
#
#     if not unit:
#         return round(value, 2)
#
#     # Standardize the unit string (uppercase, strip spaces and punctuation)
#     clean_unit = unit.upper().replace('.', '').strip()
#
#     # Dictionary of multipliers to get to 1 KG
#     unit_multipliers = {
#         # Kilograms (Multiplier = 1)
#         "KG": 1.0,
#         "KGS": 1.0,
#         "KILOS": 1.0,
#         "KILOGRAMS": 1.0,
#
#         # Metric Tons (Multiplier = 1000)
#         "MT": 1000.0,
#         "TONNES": 1000.0,
#         "TONS": 1000.0,
#         "MTS": 1000.0,
#         "T": 1000.0,
#
#         # Imperial Pounds (Multiplier = 0.453592)
#         "LBS": 0.453592,
#         "LB": 0.453592,
#         "POUNDS": 0.453592,
#
#         # Grams (Multiplier = 0.001)
#         "G": 0.001,
#         "GRAMS": 0.001
#     }
#
#     try:
#         if clean_unit in unit_multipliers:
#             multiplier = unit_multipliers[clean_unit]
#             return round(value * multiplier, 2)
#         else:
#             logging.warning(f"Unrecognized weight unit encountered: {unit}")
#             # Returning None automatically flags this document for NEEDS_REVIEW (missing_value)
#             return None
#
#     except Exception as e:
#         logging.error(f"Failed to convert weight {value} {unit}: {e}")
#         return None

import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def _clean_text(text: Optional[str]) -> Optional[str]:
    """
    Strips visual noise (casing, punctuation, extra spaces) to prepare strings
    for fuzzy matching. Does not attempt to guess or replace words.
    """
    if not text:
        return None

    # 1. Convert to uppercase and replace line breaks with spaces
    text = str(text).upper().replace('\n', ' ').replace('\t', ' ')

    # 2. Strip all punctuation (leaves only alphanumeric and spaces)
    text = re.sub(r'[^\w\s]', '', text)

    # 3. Collapse multiple spaces into a single space and trim edges
    return re.sub(r'\s+', ' ', text).strip()


def convert_weight_to_kg(value: Optional[float], unit: Optional[str]) -> Optional[float]:
    """
    Deterministically converts various shipping weight units into standard Kilograms.
    """
    if value is None:
        return None

    if not unit:
        return round(value, 2)

    clean_unit = unit.upper().replace('.', '').strip()
    unit_multipliers = {
        "KG": 1.0, "KGS": 1.0, "KILOS": 1.0, "KILOGRAMS": 1.0,
        "MT": 1000.0, "TONNES": 1000.0, "TONS": 1000.0, "MTS": 1000.0, "T": 1000.0,
        "LBS": 0.453592, "LB": 0.453592, "POUNDS": 0.453592,
        "G": 0.001, "GRAMS": 0.001
    }

    try:
        if clean_unit in unit_multipliers:
            multiplier = unit_multipliers[clean_unit]
            return round(value * multiplier, 2)
        else:
            logger.warning(f"Unrecognized weight unit encountered: {unit}")
            return None
    except Exception as e:
        logger.error(f"Failed to convert weight {value} {unit}: {e}")
        return None


def normalize_extracted_data(extracted_data: Any) -> Dict[str, Any]:
    """
    Prepares extracted data for the comparator node.
    """
    data = extracted_data.model_dump() if hasattr(extracted_data, "model_dump") else (extracted_data or {})

    if not data:
        return {}

    normalized = {}

    try:
        normalized["is_valid_doc"] = data.get("is_valid_doc")

        # Apply the safe, basic text cleaner to all string fields
        for field in ["shipper", "consignee", "notify_party", "port_of_loading", "port_of_discharge"]:
            normalized[field] = _clean_text(data.get(field))

        normalized["container_count"] = data.get("container_count")

        raw_val = data.get("raw_weight_value")
        raw_unit = data.get("raw_weight_unit")
        normalized["gross_weight_kg"] = convert_weight_to_kg(raw_val, raw_unit)

        return normalized

    except Exception as e:
        logger.error(f"Error during data normalization: {e}")
        return data