import re
from typing import Any


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r'[a-z0-9][a-z0-9+./-]{2,}', (text or '').lower()) if len(t) >= 3}


def build_compliance_matrix(analysis: dict, kb: dict) -> list[dict[str, Any]]:
    reqs = analysis.get('technical_requirements') or []
    if not reqs:
        reqs = analysis.get('scope_of_work') or []
    if isinstance(reqs, dict):
        reqs = [f'{k}: {v}' for k, v in reqs.items()]
    reqs = [str(x) for x in reqs]

    capabilities = []
    for cap in kb.get('capabilities', []):
        category = cap.get('category', '')
        for sol in cap.get('solutions', []):
            capabilities.append((category, str(sol)))

    matrix = []
    for idx, req in enumerate(reqs, start=1):
        rt = _tokens(req)
        ranked = []
        for cat, sol in capabilities:
            st = _tokens(sol + ' ' + cat)
            score = len(rt & st)
            if score:
                ranked.append((score, cat, sol))
        ranked.sort(reverse=True)
        if ranked:
            _, cat, sol = ranked[0]
            status = 'Likely Comply'
            confidence = min(95, 58 + ranked[0][0] * 12)
            note = f'Matched to TS capability: {cat} / {sol}. Engineering verification required.'
        else:
            status = 'To Verify'
            confidence = 35
            note = 'No direct capability match found in the current TS Knowledge Base.'
        matrix.append({
            'No.': idx,
            'Requirement': req,
            'TS Status': status,
            'Matched TS Solution': ranked[0][2] if ranked else '',
            'Confidence %': confidence,
            'Action / Evidence Needed': note,
        })
    return matrix


def tender_score(analysis: dict, compliance: list[dict]) -> dict:
    risks = analysis.get('risks') or []
    missing = analysis.get('missing_information') or []
    solutions = analysis.get('ts_solutions') or []
    bid = analysis.get('bid_decision') or {}
    ai_score = bid.get('score', analysis.get('confidence', 50))
    try:
        ai_score = float(ai_score)
    except Exception:
        ai_score = 50.0

    if compliance:
        matched = sum(1 for x in compliance if x.get('TS Status') == 'Likely Comply')
        technical_fit = round(100 * matched / len(compliance))
    else:
        technical_fit = min(100, 50 + len(solutions) * 8)

    information_quality = max(0, 100 - len(missing) * 8)
    risk_score = max(0, 100 - len(risks) * 10)
    commercial_fit = max(30, min(95, round(ai_score)))

    weighted = round(
        technical_fit * 0.40 +
        information_quality * 0.20 +
        risk_score * 0.20 +
        commercial_fit * 0.20
    )
    if weighted >= 80:
        rec = 'GO'
    elif weighted >= 65:
        rec = 'CONDITIONAL GO'
    elif weighted >= 45:
        rec = 'REVIEW'
    else:
        rec = 'NO-GO'
    return {
        'overall_score': weighted,
        'recommendation': rec,
        'technical_fit': technical_fit,
        'information_quality': information_quality,
        'risk_score': risk_score,
        'commercial_fit': commercial_fit,
        'weights': {'technical_fit': 40, 'information_quality': 20, 'risk_score': 20, 'commercial_fit': 20}
    }
