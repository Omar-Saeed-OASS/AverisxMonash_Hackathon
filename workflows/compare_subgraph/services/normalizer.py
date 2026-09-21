import logging
from typing import Optional


def convert_weight_to_kg(value: Optional[float], unit: Optional[str]) -> Optional[float]:
    """
    Deterministically converts various shipping weight units into standard Kilograms.
    Returns None if the value is missing or the unit is completely unrecognized.
    """

    if value is None:
        return None

    if not unit:
        return round(value, 2)

    # Standardize the unit string (uppercase, strip spaces and punctuation)
    clean_unit = unit.upper().replace('.', '').strip()

    # Dictionary of multipliers to get to 1 KG
    unit_multipliers = {
        # Kilograms (Multiplier = 1)
        "KG": 1.0,
        "KGS": 1.0,
        "KILOS": 1.0,
        "KILOGRAMS": 1.0,

        # Metric Tons (Multiplier = 1000)
        "MT": 1000.0,
        "TONNES": 1000.0,
        "TONS": 1000.0,
        "MTS": 1000.0,
        "T": 1000.0,

        # Imperial Pounds (Multiplier = 0.453592)
        "LBS": 0.453592,
        "LB": 0.453592,
        "POUNDS": 0.453592,

        # Grams (Multiplier = 0.001)
        "G": 0.001,
        "GRAMS": 0.001
    }

    try:
        if clean_unit in unit_multipliers:
            multiplier = unit_multipliers[clean_unit]
            return round(value * multiplier, 2)
        else:
            logging.warning(f"Unrecognized weight unit encountered: {unit}")
            # Returning None automatically flags this document for NEEDS_REVIEW (missing_value)
            return None

    except Exception as e:
        logging.error(f"Failed to convert weight {value} {unit}: {e}")
        return None