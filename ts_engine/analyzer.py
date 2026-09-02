import json
import os
import re
from typing import Any

from .knowledge_base import knowledge_as_text
from .rag_store import retrieve
from .boq_engine import extract_boq


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, flags=re.S)
        if not m:
            raise ValueError("AI response did not contain JSON")
        return json.loads(m.group(0))


def _fallback_analysis(corpus: str, kb: dict, project: str, client: str) -> dict:
    low = corpus.lower()
    keyword_map = {
        "CCTV": ["cctv", "camera", "surveillance"],
        "Access Control": ["access control", "card reader", "turnstile"],
        "Structured Cabling": ["structured cabling", "cat6", "fiber optic", "data outlet"],
        "BMS": ["bms", "building management"],
        "AV": ["audio visual", "av system", "display", "meeting room"],
        "Modular Buildings": ["modular", "prefab", "prefabricated", "lgs", "light gauge steel"],
        "Hoarding/Fencing": ["hoarding", "temporary fence", "fencing"],
        "Solar Support": ["solar", "pv", "photovoltaic"],
        "Blast Resistant": ["blast", "explosion", "blast resistant"]
    }
    matched = [name for name, kws in keyword_map.items() if any(k in low for k in kws)]
    risk_terms = []
    for term, label in [("liquidated damages", "Liquidated damages"), ("performance bond", "Performance bond"), ("warranty", "Warranty obligations"), ("penalty", "Penalty clauses"), ("approved vendor", "Vendor approval requirement")]:
        if term in low:
            risk_terms.append(label)
    if not corpus.strip():
        confidence = 20
    else:
        confidence = min(82, 48 + len(matched) * 5)
    fit = "GO" if matched else "REVIEW"
    solutions = [{"solution": x, "reason": "Matched by tender/document keywords; verify against detailed scope."} for x in matched]
    local_boq = extract_boq(corpus)[:150]
    return {
        "mode": "local_fallback",
        "project": project,
        "client": client,
        "executive_summary": "Automated local pre-analysis completed. Configure OPENAI_API_KEY for deeper semantic tender analysis and vision extraction.",
        "scope_of_work": matched or ["Scope requires AI/manual review"],
        "boq_summary": local_boq,
        "technical_requirements": [],
        "missing_information": ["Confirm full tender package completeness", "Confirm quantities and latest drawing revisions", "Confirm applicable standards and approved makes"],
        "clarifications": ["Please confirm final scope boundaries and interfaces.", "Please confirm latest BOQ/drawing revision and precedence of documents."],
        "risks": risk_terms,
        "ts_solutions": solutions,
        "bid_decision": {"recommendation": fit, "score": confidence, "rationale": "Keyword-based local screening only."},
        "confidence": confidence,
        "evidence": [],
        "next_actions": ["Run AI analysis with configured API key", "Validate extracted scope with a sales engineer"]
    }


def analyze_tender(corpus: str, kb: dict, project: str = "", client: str = "", model: str | None = None) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_analysis(corpus, kb, project, client)

    from openai import OpenAI
    client_api = OpenAI(api_key=api_key)
    model = model or os.getenv("OPENAI_MODEL") or "gpt-5.6-terra"
    rag_hits = retrieve(corpus[:12000], top_k=10)
    rag_context = "\n\n".join(f"[RAG SOURCE: {x['source']}]\n{x['content']}" for x in rag_hits)
    prompt = f"""You are TS AI Tender & Sales Engineer. Analyze a project/tender package for a Saudi engineering company.

PROJECT: {project}
CLIENT: {client}

TS KNOWLEDGE BASE:
{knowledge_as_text(kb)}

RETRIEVED TS KNOWLEDGE:
{rag_context}

SOURCE CORPUS:
{corpus[:350000]}

Rules:
- Distinguish explicit source facts from inference.
- Do not claim TS compliance/capability unless supported by the TS knowledge base.
- Identify ELV, security, modular/LGS, hoarding/fencing, solar structures and other relevant scope.
- Highlight technical, scope, schedule and commercial information gaps.
- Provide Bid/No-Bid recommendation as GO, CONDITIONAL GO, REVIEW, or NO-GO.
- Add evidence references using source/file/page markers when available.
- Output JSON only.

JSON keys exactly:
mode, project, client, executive_summary, scope_of_work, boq_summary, technical_requirements, missing_information, clarifications, risks, ts_solutions, bid_decision, confidence, evidence, next_actions.
For evidence use objects with claim, source_file, page_or_sheet, excerpt. For boq_summary use objects with item, description, quantity, unit, source_file, page_or_sheet where available.
Use arrays of concise objects/strings where appropriate. bid_decision must contain recommendation, score (0-100), rationale. confidence is 0-100.
"""
    try:
        response = client_api.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=12000,
        )
        result = _extract_json(response.output_text)
        result.setdefault("mode", "openai")
        if not result.get("boq_summary"):
            result["boq_summary"] = extract_boq(corpus)[:150]
        return result
    except Exception as exc:
        fallback = _fallback_analysis(corpus, kb, project, client)
        fallback["ai_error"] = str(exc)
        return fallback


def extract_image_text_with_ai(data_urls: list[str], context: str = "") -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not data_urls:
        return ""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_VISION_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-5.6-terra"
    content: list[dict[str, Any]] = [{
        "type": "input_text",
        "text": "Extract all useful tender/project information visible in these images. Preserve headings, tables, quantities, equipment tags and notes. Do not guess unreadable text. " + context
    }]
    for url in data_urls[:8]:
        content.append({"type": "input_image", "image_url": url})
    response = client.responses.create(model=model, input=[{"role": "user", "content": content}], max_output_tokens=8000)
    return response.output_text or ""
