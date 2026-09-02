from datetime import date, timedelta


def demo_analysis():
    return {
        "project": "Riyadh Smart Operations Center",
        "client": "Demo Main Contractor",
        "executive_summary": "Integrated ELV and modular technical facilities package for a Riyadh operations center, covering CCTV, access control, structured cabling, BMS integration and a prefab technical room. Tender is technically aligned with TS capabilities; final submission depends on approved-make confirmation and closure of three commercial/technical clarifications.",
        "scope_of_work": [
            "CCTV system including cameras, recording, network interfaces and control-room integration",
            "Access control for critical doors and technical areas",
            "Structured cabling and ICT passive infrastructure",
            "BMS interface for selected ELV alarms and status points",
            "Prefab modular technical room including internal partitions and MEP coordination",
        ],
        "boq_summary": [
            {"Item":"IP CCTV Camera","Description":"4MP outdoor IP camera","Qty":48,"Unit":"No.","Source":"Demo_BOQ.xlsx | ELV"},
            {"Item":"Access Control Door","Description":"Complete controlled door package","Qty":12,"Unit":"Door","Source":"Demo_BOQ.xlsx | ELV"},
            {"Item":"Cat6A Data Outlet","Description":"Cat6A outlet complete","Qty":180,"Unit":"Point","Source":"Demo_BOQ.xlsx | ICT"},
            {"Item":"Prefab Technical Room","Description":"LGS modular technical room","Qty":1,"Unit":"Lot","Source":"Demo_BOQ.xlsx | Modular"},
        ],
        "technical_requirements": [
            "CCTV products shall be from consultant-approved manufacturers.",
            "Access control shall integrate with the central security management platform.",
            "All structured cabling shall be tested and certified.",
            "Prefab technical room shall comply with project structural, fire and MEP requirements.",
            "Shop drawings, calculations, material submittals and as-built documentation are required.",
        ],
        "missing_information": [
            "Final approved-makes list is not included in the received package.",
            "Detailed integration protocol and API responsibility are not clearly defined.",
            "Final civil foundation interface for the modular room requires confirmation.",
        ],
        "clarifications": [
            "Confirm approved CCTV and access-control manufacturers and whether equivalent products are acceptable.",
            "Confirm party responsible for head-end software licenses and third-party integration gateways.",
            "Confirm foundation design boundary and required site loads for the modular technical room.",
        ],
        "risks": [
            "Approved-vendor restriction may reduce sourcing flexibility.",
            "Integration scope may expand if third-party APIs are not included by others.",
            "Modular-room foundation interface can affect schedule if frozen late.",
        ],
        "ts_solutions": [
            {"Requirement":"CCTV","TS Solution":"Security & ELV - CCTV solution","Match":"High"},
            {"Requirement":"Access Control","TS Solution":"Security & ELV - Access Control","Match":"High"},
            {"Requirement":"Structured Cabling","TS Solution":"ICT / Structured Cabling","Match":"High"},
            {"Requirement":"BMS Interface","TS Solution":"BMS / ELV Integration","Match":"Medium"},
            {"Requirement":"Prefab Technical Room","TS Solution":"Industrial - LGS Modular Building","Match":"High"},
        ],
        "confidence": 88,
        "next_actions": [
            "Issue RFI for approved makes and software-integration responsibility.",
            "Obtain vendor quotations for cameras, controllers and network active components.",
            "Freeze modular-room dimensions and foundation interface before final costing.",
            "Complete commercial review and management Go/No-Go approval.",
        ],
        "evidence": [
            {"Claim":"48 IP cameras required","Source":"Demo_BOQ.xlsx","Page/Sheet":"ELV","Excerpt":"IP CCTV Camera - Qty 48"},
            {"Claim":"Approved manufacturer requirement","Source":"Demo_Specification.pdf","Page/Sheet":"Sec. 28 20 00","Excerpt":"Products shall be from approved manufacturers"},
            {"Claim":"Modular technical room required","Source":"Demo_Scope.docx","Page/Sheet":"Scope","Excerpt":"Provide prefab technical room complete"},
        ],
        "mode": "demo_release",
    }


def demo_commercial():
    rows = [
        {"BOQ Item":"IP CCTV Camera","Qty":48,"Unit":"No.","Matched Price Item":"4MP IP Camera","Unit Cost SAR":900,"Suggested Unit Sell SAR":1200,"Total Cost SAR":43200,"Total Sell SAR":57600,"Pricing Status":"PRICED"},
        {"BOQ Item":"Access Control Door","Qty":12,"Unit":"Door","Matched Price Item":"Access Door Package","Unit Cost SAR":2650,"Suggested Unit Sell SAR":3500,"Total Cost SAR":31800,"Total Sell SAR":42000,"Pricing Status":"PRICED"},
        {"BOQ Item":"Cat6A Data Outlet","Qty":180,"Unit":"Point","Matched Price Item":"Cat6A Outlet Complete","Unit Cost SAR":330,"Suggested Unit Sell SAR":450,"Total Cost SAR":59400,"Total Sell SAR":81000,"Pricing Status":"PRICED"},
        {"BOQ Item":"Prefab Technical Room","Qty":1,"Unit":"Lot","Matched Price Item":"LGS Modular Technical Room","Unit Cost SAR":385000,"Suggested Unit Sell SAR":515000,"Total Cost SAR":385000,"Total Sell SAR":515000,"Pricing Status":"PRICED"},
    ]
    total_cost=sum(x["Total Cost SAR"] for x in rows); total_sell=sum(x["Total Sell SAR"] for x in rows)
    cont=round(total_cost*0.05,2); cost_cont=total_cost+cont
    return rows, {
        "estimated_sell_sar": total_sell,
        "raw_cost_sar": total_cost,
        "contingency_sar": cont,
        "cost_with_contingency_sar": cost_cont,
        "expected_gross_profit_sar": round(total_sell-cost_cont,2),
        "expected_margin_pct": round((total_sell-cost_cont)/total_sell*100,1),
        "pricing_coverage_pct": 100.0,
    }


def demo_pipeline_rows():
    today=date.today()
    return [
        {"id":1,"opportunity":"Riyadh Smart Operations Center","client":"Demo Main Contractor","owner":"Sales Team","stage":"Pricing","probability":55,"estimated_value":695600,"expected_margin":22.1,"deadline":(today+timedelta(days=5)).isoformat(),"next_action":"Close RFIs and finalize vendor quotes","status":"Open"},
        {"id":2,"opportunity":"Jeddah Logistics Hub ELV","client":"Demo Developer","owner":"Presales Team","stage":"Tender Review","probability":40,"estimated_value":1250000,"expected_margin":20,"deadline":(today+timedelta(days=12)).isoformat(),"next_action":"Complete compliance matrix","status":"Open"},
        {"id":3,"opportunity":"Eastern Region Modular Offices","client":"Demo EPC","owner":"Industrial Sales","stage":"Negotiation","probability":80,"estimated_value":890000,"expected_margin":24,"deadline":(today+timedelta(days=20)).isoformat(),"next_action":"Submit final commercial revision","status":"Open"},
    ]
