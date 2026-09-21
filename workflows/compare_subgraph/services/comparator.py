from typing import Any


COMPARISON_FIELDS = (
	"shipper",
	"consignee",
	"notify_party",
	"port_of_loading",
	"port_of_discharge",
	"container_count",
	"raw_weight_value",
)


def _normalized(value: Any) -> str:
	return " ".join(str(value or "").casefold().split())


def compare_documents(si_data: dict[str, Any], bl_data: dict[str, Any]) -> dict[str, Any]:
	"""Compare the extracted SI and BL fields without blocking the event loop."""
	mismatches = []
	for field in COMPARISON_FIELDS:
		si_value = si_data.get(field)
		bl_value = bl_data.get(field)
		if field in {"container_count", "raw_weight_value"}:
			equal = si_value == bl_value
		else:
			equal = _normalized(si_value) == _normalized(bl_value)
		if not equal:
			delta = None
			if isinstance(si_value, (int, float)) and isinstance(bl_value, (int, float)):
				delta = f"{bl_value - si_value:+g}"
			elif field not in {"container_count", "raw_weight_value"}:
				delta = "Text mismatch"
			mismatches.append(
				{
					"field": field,
					"si_value": si_value,
					"bl_value": bl_value,
					"delta": delta,
				}
			)
	return {
		"status": "MISMATCH" if mismatches else "OK",
		"has_defect": bool(mismatches),
		"defect_fields": [item["field"] for item in mismatches],
		"discrepancy_details": mismatches,
	}
