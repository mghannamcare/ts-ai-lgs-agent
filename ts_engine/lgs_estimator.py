import json, math, os, re
from datetime import date

# Indicative Saudi baseline only. Replace/confirm with supplier quotations before commercial use.
PRICE_DB = [
 {"category":"LGS Structure","material":"Galvanized LGS steel C/U sections","unit":"kg","low":4.8,"high":6.5,"rate":5.65,"waste":7,"labor_h_per_unit":0.055},
 {"category":"External Wall","material":"Exterior cement board 12 mm","unit":"m2","low":42,"high":65,"rate":53.5,"waste":8,"labor_h_per_unit":0.22},
 {"category":"Internal Wall","material":"Gypsum board 12.5 mm","unit":"m2","low":18,"high":30,"rate":24,"waste":8,"labor_h_per_unit":0.16},
 {"category":"Insulation","material":"Rockwool insulation 50 mm","unit":"m2","low":24,"high":42,"rate":33,"waste":5,"labor_h_per_unit":0.08},
 {"category":"Membrane","material":"Breather / waterproof membrane","unit":"m2","low":7,"high":14,"rate":10.5,"waste":10,"labor_h_per_unit":0.05},
 {"category":"Roof","material":"Insulated sandwich roof panel","unit":"m2","low":95,"high":145,"rate":120,"waste":7,"labor_h_per_unit":0.20},
 {"category":"Floor","material":"Cement board / structural floor board","unit":"m2","low":55,"high":90,"rate":72.5,"waste":8,"labor_h_per_unit":0.18},
 {"category":"Ceiling","material":"Gypsum ceiling system","unit":"m2","low":38,"high":62,"rate":50,"waste":8,"labor_h_per_unit":0.20},
 {"category":"Finish","material":"Internal paint system","unit":"m2","low":10,"high":18,"rate":14,"waste":3,"labor_h_per_unit":0.12},
 {"category":"Finish","material":"External paint / texture system","unit":"m2","low":18,"high":32,"rate":25,"waste":3,"labor_h_per_unit":0.15},
 {"category":"Openings","material":"External steel door complete","unit":"no","low":900,"high":1600,"rate":1250,"waste":0,"labor_h_per_unit":2.5},
 {"category":"Openings","material":"Internal door complete","unit":"no","low":550,"high":950,"rate":750,"waste":0,"labor_h_per_unit":1.8},
 {"category":"Openings","material":"Aluminium window complete","unit":"m2","low":550,"high":850,"rate":700,"waste":3,"labor_h_per_unit":0.8},
 {"category":"Accessories","material":"Fasteners, anchors, sealants & accessories","unit":"lot","low":1800,"high":3500,"rate":2650,"waste":0,"labor_h_per_unit":8.0},
]
LABOR_RATE_SAR_H = 28.0

def price_database(): return [dict(x) for x in PRICE_DB]

def _row(category, material, unit, qty, source, confidence, note=""):
    p=next((x for x in PRICE_DB if x["material"]==material),None)
    if not p: return {}
    waste=p["waste"]; gross=qty*(1+waste/100)
    mh=gross*p["labor_h_per_unit"]
    return {"Category":category,"Material / Activity":material,"Unit":unit,"Net Qty":round(qty,2),
      "Waste %":waste,"Gross Qty":round(gross,2),"Indicative Unit Cost SAR":p["rate"],
      "Material Cost SAR":round(gross*p["rate"],2),"Labor Hours":round(mh,1),
      "Labor Rate SAR/h":LABOR_RATE_SAR_H,"Labor Cost SAR":round(mh*LABOR_RATE_SAR_H,2),
      "Total Direct Cost SAR":round(gross*p["rate"]+mh*LABOR_RATE_SAR_H,2),
      "Price Range SAR":f'{p["low"]:.2f}–{p["high"]:.2f}',"Quantity Source":source,
      "Confidence":confidence,"Notes":note}

def parametric_takeoff(length_m=12,width_m=6,height_m=3,partitions_m=18,external_doors=2,internal_doors=4,window_area_m2=12,
                       steel_kg_m2=38):
    area=length_m*width_m; perimeter=2*(length_m+width_m); ext_wall=perimeter*height_m
    int_wall=max(0,partitions_m)*height_m
    wall_board_ext=ext_wall
    gypsum=(ext_wall+2*int_wall)
    insulation=ext_wall+int_wall
    roof=area*1.05
    rows=[
      _row("LGS Structure","Galvanized LGS steel C/U sections","kg",area*steel_kg_m2,"Parametric model","MEDIUM","Default steel intensity is editable."),
      _row("External Wall","Exterior cement board 12 mm","m2",wall_board_ext,"Geometry","MEDIUM"),
      _row("Internal Wall","Gypsum board 12.5 mm","m2",gypsum,"Geometry","MEDIUM","Includes internal face to external walls and both faces of partitions."),
      _row("Insulation","Rockwool insulation 50 mm","m2",insulation,"Geometry","MEDIUM"),
      _row("Membrane","Breather / waterproof membrane","m2",ext_wall,"Geometry","MEDIUM"),
      _row("Roof","Insulated sandwich roof panel","m2",roof,"Geometry","MEDIUM"),
      _row("Floor","Cement board / structural floor board","m2",area,"Geometry","MEDIUM"),
      _row("Ceiling","Gypsum ceiling system","m2",area,"Geometry","MEDIUM"),
      _row("Finish","Internal paint system","m2",gypsum,"Geometry","LOW"),
      _row("Finish","External paint / texture system","m2",ext_wall,"Geometry","LOW"),
      _row("Openings","External steel door complete","no",external_doors,"User / drawing input","MEDIUM"),
      _row("Openings","Internal door complete","no",internal_doors,"User / drawing input","MEDIUM"),
      _row("Openings","Aluminium window complete","m2",window_area_m2,"User / drawing input","MEDIUM"),
      _row("Accessories","Fasteners, anchors, sealants & accessories","lot",1,"Allowance","LOW"),
    ]
    return [r for r in rows if r]

def summarize(rows):
    mat=sum(float(r.get("Material Cost SAR",0) or 0) for r in rows)
    hrs=sum(float(r.get("Labor Hours",0) or 0) for r in rows)
    labor=sum(float(r.get("Labor Cost SAR",0) or 0) for r in rows)
    total=mat+labor
    return {"material_cost_sar":round(mat,2),"labor_hours":round(hrs,1),"labor_cost_sar":round(labor,2),
            "direct_cost_sar":round(total,2)}

def apply_overheads(rows, transport_pct=3, equipment_pct=2, contingency_pct=5):
    s=summarize(rows); direct=s["direct_cost_sar"]
    transport=direct*transport_pct/100; equipment=direct*equipment_pct/100; contingency=direct*contingency_pct/100
    return {**s,"transport_sar":round(transport,2),"equipment_consumables_sar":round(equipment,2),
      "contingency_sar":round(contingency,2),"estimated_cost_sar":round(direct+transport+equipment+contingency,2)}

def _source_building_names(corpus: str):
    """Recognize all uploaded building drawing filenames so failed Vision never makes a building disappear."""
    names=[]
    for name in re.findall(r"\[SOURCE FILE:\s*([^\]]+)\]", corpus or "", flags=re.I):
        low=name.lower()
        if low.endswith((".pdf", ".png", ".jpg", ".jpeg", ".webp")):
            clean=re.sub(r"\.(pdf|png|jpg|jpeg|webp)$", "", name, flags=re.I)
            clean=re.sub(r"\s*-?\s*model\s*$", "", clean, flags=re.I)
            clean=re.sub(r"[_-]+", " ", clean).strip()
            if clean and clean not in names:
                names.append(clean)
    return names


def ai_lgs_takeoff(corpus, project="", model=None):
    """Multi-building AI takeoff. Never silently drops drawings when Vision/API is unavailable."""
    key=os.getenv("OPENAI_API_KEY")
    detected=_source_building_names(corpus)
    if not key:
        return {
            "project": project,
            "mode": "local_coverage_only",
            "buildings": [{"building_name":n,"status":"RECOGNIZED - AI/VISION REQUIRED","quantity_rows":[],"assumptions":[],
                           "clarifications":["Drawing recognized, but AI/Vision is not configured; exact drawing quantities were not inferred."]} for n in detected],
            "quantity_rows": [],
            "assumptions": [],
            "clarifications": ["AI/Vision is required for image-based drawing quantity extraction."],
            "detected_buildings": detected,
        }
    from openai import OpenAI
    client=OpenAI(api_key=key); model=model or os.getenv("OPENAI_MODEL") or "gpt-5.6-terra"
    prompt=f"""You are a senior LGS quantity surveyor in Saudi Arabia. Analyze ONLY the LGS/prefabricated-building scope in the supplied drawings/specifications/BOQ text.
Project: {project}
SOURCE:
{corpus[:300000]}

CRITICAL MULTI-BUILDING RULES:
- Treat EACH uploaded building drawing as a separate building. Do not merge buildings and never stop at the first building.
- First inventory every building/source file. A building must remain in the output even if its dimensions/quantities cannot be read.
- Reconcile building names and explicit quantities in the BOQ with drawing filenames where possible.
- Do not invent exact dimensions or quantities. If unavailable, keep the building with status NEEDS_REVIEW and explain what is missing.
- Preserve source file/page/sheet references.

Return JSON only with keys: project, buildings, assumptions, clarifications.
Each object in buildings must contain: building_name, source_files, status, building_dimensions, area_m2, assumptions, clarifications, quantity_rows.
quantity_rows is an array. Each object: category, material, unit, net_qty, waste_pct, source_reference, confidence, notes.
Break down galvanized light gauge steel framing, tracks/studs/joists/trusses where evidence permits, boards, insulation, membranes, roof, floor, ceiling, finishes, doors/windows, fasteners/anchors/sealants/accessories.
Do NOT price. Quantities only."""
    try:
        r=client.responses.create(model=model,input=prompt,max_output_tokens=16000)
        raw=(r.output_text or "").strip()
        if raw.startswith("```"): raw=re.sub(r"^```(?:json)?\s*|\s*```$","",raw,flags=re.I|re.S).strip()
        result=json.loads(raw)
        buildings=result.get("buildings") or []
        returned={str(b.get("building_name","")).strip().lower() for b in buildings}
        # Coverage guard: any uploaded building omitted by AI is inserted as needs-review.
        for n in detected:
            if n.lower() not in returned and not any(n.lower() in x or x in n.lower() for x in returned if x):
                buildings.append({"building_name":n,"source_files":[],"status":"NEEDS_REVIEW","building_dimensions":None,"area_m2":None,
                                  "assumptions":[],"clarifications":["Uploaded drawing was recognized but omitted by AI response; manual/vision re-analysis required."],"quantity_rows":[]})
        result["buildings"]=buildings
        flat=[]
        for b in buildings:
            bname=b.get("building_name") or "Unassigned Building"
            for q in b.get("quantity_rows") or []:
                q=dict(q); q["building_name"]=bname; flat.append(q)
        result["quantity_rows"]=flat
        result["detected_buildings"]=detected
        return result
    except Exception as e:
        msg=str(e)
        credit=("429" in msg or "credit" in msg.lower() or "quota" in msg.lower())
        return {
            "project":project,"mode":"ai_unavailable","error":msg,"detected_buildings":detected,
            "buildings":[{"building_name":n,"source_files":[],"status":"VISION CREDIT REQUIRED" if credit else "AI ERROR",
                          "building_dimensions":None,"area_m2":None,"assumptions":[],
                          "clarifications":["Building was recognized but drawing vision could not be completed. No exact quantity was invented."],"quantity_rows":[]} for n in detected],
            "quantity_rows":[],"assumptions":[],
            "clarifications":["AI/Vision credits are exhausted. Local extraction remains available; recharge/change API key for drawing vision." if credit else "AI extraction failed; local extraction remains available."]}


def price_ai_rows(ai_rows):
    out=[]
    for q in ai_rows or []:
        desc=str(q.get("material","")); building=q.get("building_name") or q.get("Building") or "Unassigned Building"
        low=desc.lower(); candidates=[]
        for p in PRICE_DB:
            words=[w for w in re.findall(r"[a-z0-9]+",p["material"].lower()) if len(w)>3]
            score=sum(w in low for w in words); candidates.append((score,p))
        score,p=max(candidates,key=lambda x:x[0]) if candidates else (0,None)
        if not p or score==0:
            out.append({"Building":building,"Category":q.get("category",""),"Material / Activity":desc,"Unit":q.get("unit",""),
             "Net Qty":q.get("net_qty",0),"Waste %":q.get("waste_pct",0),"Gross Qty":q.get("net_qty",0),
             "Indicative Unit Cost SAR":None,"Material Cost SAR":None,"Labor Hours":None,"Labor Rate SAR/h":LABOR_RATE_SAR_H,
             "Labor Cost SAR":None,"Total Direct Cost SAR":None,"Price Range SAR":"PRICE REQUIRED",
             "Quantity Source":q.get("source_reference","AI extraction"),"Confidence":q.get("confidence","LOW"),
             "Notes":str(q.get("notes","") or "")+" | No reliable baseline price match."}); continue
        qty=float(q.get("net_qty",0) or 0); waste=float(q.get("waste_pct",p["waste"]) or 0); gross=qty*(1+waste/100); mh=gross*p["labor_h_per_unit"]
        out.append({"Building":building,"Category":q.get("category",""),"Material / Activity":desc,"Unit":q.get("unit",p["unit"]),
          "Net Qty":round(qty,2),"Waste %":waste,"Gross Qty":round(gross,2),"Indicative Unit Cost SAR":p["rate"],
          "Material Cost SAR":round(gross*p["rate"],2),"Labor Hours":round(mh,1),"Labor Rate SAR/h":LABOR_RATE_SAR_H,
          "Labor Cost SAR":round(mh*LABOR_RATE_SAR_H,2),"Total Direct Cost SAR":round(gross*p["rate"]+mh*LABOR_RATE_SAR_H,2),
          "Price Range SAR":f'{p["low"]:.2f}–{p["high"]:.2f}',"Quantity Source":q.get("source_reference","AI extraction"),
          "Confidence":q.get("confidence","LOW"),"Notes":q.get("notes","")})
    return out

def benchmark_project_1_rows():
    """Preloaded benchmark based on supplied SRA contractor office plan + BOQ.
    Quantities are preliminary and keep confidence/source notes for reviewer adjustment.
    """
    raw = [
      ("LGS Structure","Galvanized LGS wall studs/tracks, Z275 assumed","kg",7500,7,5.80,0.070,"LOW","Parametric: total LGS intensity split by walls/roof; structural design required","GI coil baseline plus roll-forming/fabrication allowance"),
      ("LGS Structure","Galvanized LGS roof trusses/purlins, Z275 assumed","kg",5000,7,5.80,0.075,"LOW","Parametric allowance for 27.7×13.2 m single-storey office","Same baseline as LGS wall steel"),
      ("LGS Structure","LGS bracing, connection plates & misc. formed steel","kg",800,7,6.20,0.080,"LOW","Allowance","Allowance above raw GI material"),
      ("External Envelope","Fire-rated insulated sandwich wall panel system","m2",221.4,7,155,0.22,"MEDIUM","Perimeter×3.0 m height less assumed openings","Panel type/thickness/fire rating to confirm"),
      ("Roofing","Fire-rated insulated roof sandwich panel","m2",383.92,7,175,0.28,"MEDIUM","Plan area +5% roof slope/laps","Roof panel spec to confirm"),
      ("Roofing","Rainwater gutter","m",55.4,5,45,0.15,"LOW","Two long elevations assumed","Allowance"),
      ("Roofing","Rainwater downpipes","m",12,5,35,0.12,"LOW","4 downpipes × 3 m assumed","Allowance"),
      ("Internal Partitions","Fire-rated gypsum-board partition wall system","m2",247,8,45,0.30,"LOW","Approx. wall surface allocation from plan; verify wall schedule","Allowance"),
      ("Internal Partitions","Moisture-resistant gypsum/cement board wet-area partition finish","m2",65,8,52,0.32,"LOW","Wet-area wall surface allowance","Allowance"),
      ("Internal Partitions","Tempered-glass office frontage partitions","m2",45,5,210,0.65,"LOW","Plan-based allowance; verify elevations","Allowance"),
      ("Wall Finishes","Ceramic/porcelain wall tiles to toilets/pantry","m2",85,10,55,0.30,"LOW","Half-height tiling for contractor office per BOQ; area allowance","Allowance"),
      ("Wall Finishes","Internal paint system to board surfaces","m2",600,5,12,0.10,"LOW","Wall surface allowance after glazed/tiled areas","Allowance"),
      ("Ceilings","600×600 mineral-fibre suspended ceiling – general areas","m2",285,5,38,0.22,"LOW","Area allocation assumption","Allowance"),
      ("Ceilings","Moisture-resistant suspended ceiling – toilets/wet areas","m2",30,5,50,0.25,"LOW","Area allocation assumption","Allowance"),
      ("Ceilings","Decorative/double-level gypsum ceiling – meeting area","m2",50.64,8,70,0.40,"LOW","Residual meeting/feature ceiling allocation","Allowance"),
      ("Floor Finishes","600×600 porcelain/ceramic floor tiles incl. skirting allowance","m2",330,8,55,0.28,"LOW","General area allocation","Bulk material allowance"),
      ("Floor Finishes","300×300 anti-slip floor tiles to wet areas","m2",35.64,10,60,0.32,"LOW","Wet-area allowance","Allowance"),
      ("Waterproofing","Wet-area waterproofing membrane/system","m2",40,10,22,0.20,"LOW","Wet floors plus upturn allowance","Allowance"),
      ("Doors & Windows","Double-leaf aluminium entrance door complete","no",1,0,3200,4.0,"MEDIUM","BOQ scope item; quantity inferred from plan","Budget allowance"),
      ("Doors & Windows","Single-leaf emergency fire-rated steel door complete","no",1,0,2800,3.0,"MEDIUM","BOQ scope item; quantity inferred from plan","Budget allowance"),
      ("Doors & Windows","Internal tempered-glass office doors","no",7,0,1350,2.0,"LOW","Plan-based count assumption","Allowance"),
      ("Doors & Windows","Aluminium toilet doors","no",4,0,950,1.8,"LOW","Plan-based count assumption","Allowance"),
      ("Doors & Windows","Powder-coated aluminium glazed windows","m2",16,5,650,0.80,"LOW","Window area estimated from plan; elevations required","Allowance"),
      ("Doors & Windows","Ventilation louvers","m2",2,5,350,0.50,"LOW","Allowance; MEP/elevations required","Allowance"),
      ("Fixed Furniture","Pantry/kitchen cabinets + solid-surface counter","lm",8,5,650,0.80,"LOW","Allowance from plan/scope matrix","Allowance"),
      ("Sanitary","Floor-mounted WC complete","no",4,0,850,1.5,"LOW","Plan-based count assumption","Allowance"),
      ("Sanitary","Wash basin + mixer complete","no",4,0,650,1.2,"LOW","Plan-based count assumption","Allowance"),
      ("Sanitary","Toilet accessories set","set",4,0,450,0.8,"LOW","Allowance","Allowance"),
      ("Accessories","Fasteners, anchors, sealants, trims, flashings & consumables","lot",1,0,18000,80,"LOW","Project allowance","Allowance"),
      ("Civil / Foundation","Concrete slab/foundations provisional quantity","m3",65,5,310,0.45,"LOW","No structural foundation drawings; provisional only","Budget allowance"),
      ("Civil / Foundation","Reinforcement steel provisional quantity","t",6,5,2850,3.0,"LOW","No structural foundation drawings; provisional only","Market allowance"),
      ("Lifting / Erection","Crane, lifting equipment & erection plant allowance","lot",1,0,18000,0,"LOW","BOQ requires lifting equipment","Provisional allowance"),
      ("Testing / Handover","Testing, commissioning, documentation & handover allowance","lot",1,0,12000,120,"LOW","BOQ requires T&C and handover","Provisional allowance"),
    ]
    out = []
    for cat, mat, unit, qty, waste, rate, lh, conf, basis, note in raw:
        gross = qty * (1 + waste/100)
        hours = gross * lh
        mat_cost = gross * rate
        labor_cost = hours * LABOR_RATE_SAR_H
        out.append({
            "Category": cat, "Material / Activity": mat, "Unit": unit,
            "Net Qty": round(qty, 2), "Waste %": waste, "Gross Qty": round(gross, 2),
            "Indicative Unit Cost SAR": rate, "Material Cost SAR": round(mat_cost, 2),
            "Labor Hours": round(hours, 1), "Labor Rate SAR/h": LABOR_RATE_SAR_H,
            "Labor Cost SAR": round(labor_cost, 2), "Total Direct Cost SAR": round(mat_cost + labor_cost, 2),
            "Price Range SAR": "Demo / editable", "Quantity Source": basis,
            "Confidence": conf, "Notes": note
        })
    return out

def benchmark_project_1_meta():
    return {
        "project": "SRA – Royal Hangars Upgrade Program at KAIA",
        "building": "Contractor's Prefab Office",
        "dimensions": "27.7 × 13.2 m",
        "area_m2": 365.64,
        "perimeter_m": 81.8,
        "assumed_height_m": 3.0,
        "status": "PRELIMINARY / NOT FOR CONTRACT",
        "assumptions": [
            "Building footprint and area are taken from the uploaded plan/BOQ.",
            "Wall height is assumed at 3.0 m because elevation/section drawings are not supplied.",
            "LGS profiles, gauge, spacing and structural design are not available and must be engineered before final quotation.",
            "MEP is treated as provisional allowance because layouts and loads are missing.",
            "All rates are indicative baselines and must be replaced with supplier quotations before commercial submission."
        ],
        "clarifications": [
            "Confirm wall/roof panel core, thickness, fire rating and sheet gauge.",
            "Issue elevations, sections, wall build-up and LGS profile schedule.",
            "Issue MEP design: HVAC, electrical, ELV/fire, plumbing and drainage.",
            "Confirm furniture, appliances and signage schedules.",
            "Confirm foundation design and site external works interface."
        ]
    }
