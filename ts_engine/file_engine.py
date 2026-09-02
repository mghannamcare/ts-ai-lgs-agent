import json
from pathlib import Path


def detect_file_type(path: str | Path) -> str:
    ext = Path(path).suffix.lower()
    mapping = {
        ".pdf": "pdf", ".doc": "word", ".docx": "word",
        ".xls": "excel", ".xlsx": "excel", ".csv": "excel",
        ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
        ".dwg": "cad", ".dxf": "cad", ".rvt": "bim", ".ifc": "bim",
    }
    return mapping.get(ext, "other")


def flatten_aps_properties(aps_result: dict, limit: int = 2500) -> str:
    """Convert APS model metadata/property payload into compact AI-readable text."""
    lines = []
    for pset in aps_result.get("property_sets", []):
        view_name = pset.get("name") or pset.get("guid")
        lines.append(f"VIEW: {view_name}")
        collection = pset.get("properties", {}).get("data", {}).get("collection", [])
        for item in collection:
            name = item.get("name") or item.get("objectid")
            props = item.get("properties", {})
            compact = []
            for category, values in props.items():
                if not isinstance(values, dict):
                    continue
                for key, value in values.items():
                    if value not in (None, "", [], {}):
                        compact.append(f"{category}.{key}={value}")
            if compact:
                lines.append(f"{name}: " + "; ".join(compact[:30]))
            if len(lines) >= limit:
                lines.append("[TRUNCATED]")
                return "\n".join(lines)
    return "\n".join(lines)
