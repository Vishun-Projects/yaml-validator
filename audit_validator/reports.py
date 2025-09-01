import json
from typing import Dict, Any
import pandas as pd
import os

def write_json(report: Dict[str, Any], path: str) -> None:
    # ensure directory exists
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

def to_excel(report: Dict[str, Any], path: str) -> None:
    """
    Two sheets:
      - summary: meta
      - details: field-by-field status
    """
    meta = report.get("meta", {})
    fields = report.get("fields", {})

    # Summary DataFrame
    summary_rows = []
    for k, v in meta.items():
        summary_rows.append({"key": k, "value": v})
    df_meta = pd.DataFrame(summary_rows)

    # Details DataFrame
    details_rows = []
    for field, info in fields.items():
        details_rows.append({
            "field": field,
            "found_key": info.get("found_key"),
            "value": info.get("value"),
            "status": info.get("status"),
            "closest_match": info.get("closest_match"),
            "similarity": info.get("similarity"),
            "allowed": ", ".join(info.get("allowed") or []),
        })
    df_details = pd.DataFrame(details_rows)

    # Write Excel
    # Ensure directory exists
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df_meta.to_excel(writer, index=False, sheet_name="summary")
        df_details.to_excel(writer, index=False, sheet_name="details")
