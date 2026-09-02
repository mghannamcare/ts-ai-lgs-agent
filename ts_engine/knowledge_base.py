import json
from pathlib import Path

DEFAULT_KB = {
    "company": "TS",
    "capabilities": [
        {"category": "ELV", "solutions": ["CCTV", "Access Control", "Structured Cabling", "AV", "BMS", "Intercom", "Security Systems"]},
        {"category": "Industrial / Modular", "solutions": ["Prefab modular buildings", "LGS buildings", "Temporary facilities", "Guard rooms", "Site offices", "Internal partitions", "2D wall panels", "Temporary hoarding and fencing", "Solar PV support structures"]},
        {"category": "Special Applications", "solutions": ["Blast-resistant modular building engineering subject to project-specific structural and blast criteria"]}
    ],
    "commercial_preferences": [
        "Prefer technically clear opportunities with manageable payment risk",
        "Highlight scope gaps before quotation",
        "Avoid committing to unsupported compliance or performance claims without evidence"
    ]
}


def load_knowledge_base(path: str | Path | None = None) -> dict:
    if path and Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    bundled = Path(__file__).with_name("ts_knowledge_base.json")
    if bundled.exists():
        return json.loads(bundled.read_text(encoding="utf-8"))
    return DEFAULT_KB


def save_knowledge_base(data: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def knowledge_as_text(kb: dict) -> str:
    return json.dumps(kb, ensure_ascii=False, indent=2)
