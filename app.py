import os, tempfile
from pathlib import Path
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from ts_engine.document_parser import parse_document, image_to_data_url, pdf_pages_as_data_urls
from ts_engine.analyzer import extract_image_text_with_ai
from ts_engine.lgs_estimator import (
    price_database, parametric_takeoff, summarize, apply_overheads, ai_lgs_takeoff, price_ai_rows,
    benchmark_project_1_rows, benchmark_project_1_meta
)

load_dotenv()
st.set_page_config(page_title="TS AI – LGS Quantity & Cost Estimator", page_icon="🏗️", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.2rem;max-width:1500px}.hero{padding:18px 22px;border:1px solid #ddd;border-radius:14px;margin-bottom:14px}
.hero h1{margin:0}.hero p{margin:5px 0 0;opacity:.75}[data-testid="stMetric"]{border:1px solid #e5e5e5;padding:10px;border-radius:10px}
</style>""",unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>TS AI – LGS Quantity & Cost Estimator</h1><p>Multi-Building AI Agent: Drawings + Specifications + BOQ → Building-by-Building Takeoff → Labor Hours → Indicative Saudi Cost</p></div>',unsafe_allow_html=True)
st.warning("Cost rates are indicative Saudi-market baselines for estimating only. Confirm supplier/subcontractor quotations before issuing a commercial offer.")

for k,d in {"rows":[],"ai_result":{},"corpus":"","file_records":[]}.items():
    if k not in st.session_state: st.session_state[k]=d

def vision_credit_error(exc):
    s=str(exc).lower(); return "429" in s or "credit" in s or "quota" in s or "billing" in s

def building_name_from_file(name):
    stem=Path(name).stem
    import re
    stem=re.sub(r"\s*-?\s*model\s*$","",stem,flags=re.I)
    return stem.replace("_"," ").strip()

with st.sidebar:
    st.subheader("Engine")
    st.write("Local document parser: Ready")
    st.write("AI/Vision:", "Configured" if os.getenv("OPENAI_API_KEY") else "API key required for drawing vision")
    st.caption("PDF text and Excel are read locally first. Vision is an enhancement, not a prerequisite for retaining a file in the project.")
    st.divider()
    if st.button("Load Demo Project - SRA Contractor Office", use_container_width=True):
        st.session_state.rows=benchmark_project_1_rows(); st.session_state.ai_result=benchmark_project_1_meta()
        st.session_state.corpus="Demo Project - SRA Contractor Office loaded from supplied SRA layout + BOQ."
        st.success("Demo project loaded. Go to Cost Estimate.")
    st.divider(); st.subheader("Cost Allowances")
    transport=st.number_input("Transport %",0.0,30.0,3.0,0.5); equipment=st.number_input("Equipment / consumables %",0.0,30.0,2.0,0.5)
    contingency=st.number_input("Contingency %",0.0,30.0,5.0,0.5); mep_rate=st.number_input("MEP provisional SAR/m²",0.0,2500.0,450.0,25.0)

tab1,tab2,tab3,tab4=st.tabs(["1. Project Documents","2. Multi-Building Takeoff","3. Cost Estimate","4. Price Database"])

with tab1:
    c1,c2,c3=st.columns(3)
    project=c1.text_input("Project","LGS Building Estimate"); client=c2.text_input("Client",""); location=c3.text_input("Location","")
    files=st.file_uploader("Upload drawings, specifications and BOQ",accept_multiple_files=True,type=["pdf","docx","xlsx","xls","csv","png","jpg","jpeg","webp"])
    if st.button("Read Project Files",type="primary",use_container_width=True):
        corpus=[]; status=[]; records=[]
        for f in files or []:
            suffix=Path(f.name).suffix; tmp=Path(tempfile.gettempdir())/(f"ts_lgs_{abs(hash((f.name,len(f.getvalue()))))}{suffix}"); tmp.write_bytes(f.getvalue())
            try:
                parsed=parse_document(tmp); local_text=parsed.get("text","") or ""; text=local_text; details=[]; vision_status="Not required"
                if parsed.get("needs_vision"):
                    vision_status="Required"
                    if os.getenv("OPENAI_API_KEY"):
                        try:
                            urls=pdf_pages_as_data_urls(tmp,8) if suffix.lower()==".pdf" else [image_to_data_url(tmp)]
                            vtext=extract_image_text_with_ai(urls,"Focus on dimensions, building name, wall/roof/floor build-ups, openings, LGS framing notes, material specifications and quantities.")
                            if vtext: text += "\n[VISION EXTRACTION]\n"+vtext; vision_status="Completed"
                            else: details.append("Vision returned no text")
                        except Exception as ve:
                            vision_status="Credits required" if vision_credit_error(ve) else "Vision error"
                            details.append(f"Vision unavailable: {ve}")
                    else: details.append("AI/Vision API key not configured")
                # Always retain source marker and local extraction, even if Vision fails.
                corpus.append(f"\n[SOURCE FILE: {f.name}]\n{text}\n")
                status_label="Read" if text.strip() else "Recognized"
                if parsed.get("needs_vision") and vision_status!="Completed": status_label="Read locally / Vision pending" if local_text.strip() else "Recognized / Vision pending"
                row={"File":f.name,"Status":status_label,"Details":" | ".join(details),"Type":parsed.get("file_type"),"Needs Vision":bool(parsed.get("needs_vision")),"Vision":vision_status}
                status.append(row); records.append({**row,"Building":building_name_from_file(f.name) if suffix.lower() in [".pdf",".png",".jpg",".jpeg",".webp"] else ""})
            except Exception as e:
                # True parser failure only; do not confuse API billing with file failure.
                status.append({"File":f.name,"Status":"Parser Error","Details":str(e),"Type":None,"Needs Vision":False,"Vision":"Not reached"})
        st.session_state.corpus="\n".join(corpus); st.session_state.file_records=records
        st.dataframe(pd.DataFrame(status),use_container_width=True,hide_index=True)
        n_draw=sum(bool(r.get("Building")) for r in records); n_vis=sum(r.get("Vision")=="Completed" for r in records if r.get("Building"))
        st.success(f"Files registered: {len(records)} | Building drawings recognized: {n_draw} | Vision completed: {n_vis} | Local corpus: {len(st.session_state.corpus):,} characters.")
        if n_draw and n_vis<n_draw:
            st.warning(f"{n_draw-n_vis} building drawing(s) remain recognized in the project but still need Vision. They will NOT be silently omitted from the building list.")
    if st.session_state.file_records:
        b=[{"Building":r["Building"],"Source File":r["File"],"File Status":r["Status"],"Vision":r["Vision"]} for r in st.session_state.file_records if r.get("Building")]
        if b:
            st.subheader("Building Coverage Register"); st.dataframe(pd.DataFrame(b),use_container_width=True,hide_index=True)
    if st.session_state.corpus:
        with st.expander("Extracted source text"):
            st.text_area("Source",st.session_state.corpus[:120000],height=300)

with tab2:
    st.subheader("Building-by-Building AI Takeoff")
    if st.button("Analyze ALL Buildings",use_container_width=True,type="primary"):
        if not st.session_state.corpus: st.error("Upload and read project files first.")
        else:
            with st.spinner("Inventorying and analyzing all buildings..."):
                res=ai_lgs_takeoff(st.session_state.corpus,project); st.session_state.ai_result=res or {}; st.session_state.rows=price_ai_rows((res or {}).get("quantity_rows",[]))
            if (res or {}).get("error"):
                st.warning("All uploaded buildings were retained in the register, but AI/Vision could not complete quantity extraction. Check API credits/key.")
            else: st.success("Multi-building analysis completed.")
    r=st.session_state.ai_result or {}
    buildings=r.get("buildings") or []
    if buildings:
        summary=[]
        for b in buildings:
            summary.append({"Building":b.get("building_name"),"Status":b.get("status","Analyzed"),"Dimensions":b.get("building_dimensions"),"Area m²":b.get("area_m2"),"Takeoff Lines":len(b.get("quantity_rows") or []),"Clarifications":"; ".join(b.get("clarifications") or [])})
        st.subheader("All Buildings – Coverage & Analysis Status"); st.dataframe(pd.DataFrame(summary),use_container_width=True,hide_index=True)
    elif st.session_state.file_records:
        recognized=[r for r in st.session_state.file_records if r.get("Building")]
        if recognized:
            st.info(f"{len(recognized)} building drawing(s) recognized. Click Analyze ALL Buildings for takeoff; drawings remain listed even if Vision is unavailable.")
    if r.get("clarifications"):
        st.write("**Project Clarifications**")
        for x in r.get("clarifications",[]): st.write("•",x)

    st.divider(); st.subheader("Parametric Fallback / Quick Estimate")
    c1,c2,c3,c4=st.columns(4); L=c1.number_input("Length (m)",1.0,200.0,12.0,.5); W=c2.number_input("Width (m)",1.0,100.0,6.0,.5); H=c3.number_input("Wall height (m)",2.0,12.0,3.0,.1); P=c4.number_input("Internal partition length (m)",0.0,500.0,18.0,1.0)
    c1,c2,c3,c4=st.columns(4); ed=c1.number_input("External doors",0,100,2); idr=c2.number_input("Internal doors",0,200,4); wa=c3.number_input("Window area (m²)",0.0,500.0,12.0,1.0); steel=c4.number_input("LGS steel intensity (kg/m²)",15.0,90.0,38.0,1.0)
    if st.button("Generate Parametric Takeoff",use_container_width=True):
        st.session_state.rows=parametric_takeoff(L,W,H,P,ed,idr,wa,steel); st.session_state.ai_result={"assumptions":["Parametric estimate generated from entered dimensions. Verify against IFC/shop drawings."],"clarifications":[]}; st.success("Parametric takeoff generated.")
    if st.session_state.rows:
        st.subheader("Detailed Quantity Takeoff"); df=pd.DataFrame(st.session_state.rows); edited=st.data_editor(df,use_container_width=True,hide_index=True,num_rows="dynamic"); st.session_state.rows=edited.to_dict("records")

with tab3:
    rows=st.session_state.rows
    if not rows: st.info("Generate a takeoff first. If AI/Vision credits are unavailable, the Building Coverage Register still proves that all drawings were retained, but exact visual quantities cannot be responsibly invented.")
    else:
        priced=[r for r in rows if pd.notna(r.get("Material Cost SAR"))]; total=apply_overheads(priced,transport,equipment,contingency)
        areas=[float(b.get("area_m2") or 0) for b in (st.session_state.ai_result or {}).get("buildings",[]) if b.get("area_m2")]
        area_m2=sum(areas) or float((st.session_state.ai_result or {}).get("area_m2") or 0); mep_provisional=area_m2*mep_rate if area_m2 else 0
        total["mep_provisional_sar"]=round(mep_provisional,2); total["estimated_cost_with_mep_sar"]=round(total["estimated_cost_sar"]+mep_provisional,2)
        c=st.columns(5); c[0].metric("Material Cost",f"{total['material_cost_sar']:,.0f} SAR"); c[1].metric("Labor Hours",f"{total['labor_hours']:,.0f} h"); c[2].metric("Labor Cost",f"{total['labor_cost_sar']:,.0f} SAR"); c[3].metric("Direct Cost",f"{total['direct_cost_sar']:,.0f} SAR"); c[4].metric("PROJECT TOTAL",f"{total['estimated_cost_with_mep_sar']:,.0f} SAR")
        if "Building" in pd.DataFrame(rows).columns:
            st.subheader("Cost by Building")
            d=pd.DataFrame(rows); d2=d.groupby("Building",dropna=False).agg(**{"Material Cost SAR":("Material Cost SAR","sum"),"Labor Hours":("Labor Hours","sum"),"Labor Cost SAR":("Labor Cost SAR","sum"),"Direct Cost SAR":("Total Direct Cost SAR","sum")}).reset_index(); st.dataframe(d2,use_container_width=True,hide_index=True)
        st.subheader("Project Detailed Takeoff"); st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        unpriced=[r for r in rows if pd.isna(r.get("Material Cost SAR"))]
        if unpriced: st.warning(f"{len(unpriced)} item(s) require supplier pricing before the estimate is complete.")

        def make_xlsx():
            wb=Workbook(); ws=wb.active; ws.title="LGS Cost Estimate"; headers=list(pd.DataFrame(rows).columns); ws.append(headers)
            for cell in ws[1]: cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor="17365D"); cell.alignment=Alignment(horizontal="center")
            for rr in rows: ws.append([rr.get(h) for h in headers])
            ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions
            for col in ws.columns: ws.column_dimensions[col[0].column_letter].width=min(38,max(12,max(len(str(c.value or "")) for c in col)+2))
            s=wb.create_sheet("Project Cost Summary"); s.append(["Cost Component","SAR"])
            for k,label in [("material_cost_sar","Material"),("labor_cost_sar","Labor"),("transport_sar","Transport"),("equipment_consumables_sar","Equipment / Consumables"),("contingency_sar","Contingency"),("estimated_cost_sar","Estimated Cost excl. MEP"),("mep_provisional_sar","MEP Provisional"),("estimated_cost_with_mep_sar","PROJECT TOTAL incl. MEP")]: s.append([label,total[k]])
            p=wb.create_sheet("Price Database"); pdb=price_database(); ph=list(pdb[0].keys()); p.append(ph)
            for x in pdb:p.append([x.get(h) for h in ph])
            out=Path(tempfile.gettempdir())/"TS_LGS_Multi_Building_Cost_Estimate.xlsx"; wb.save(out); return out
        if st.button("Prepare Excel Cost Estimate",type="primary",use_container_width=True): out=make_xlsx(); st.session_state["xlsx_bytes"]=out.read_bytes()
        if st.session_state.get("xlsx_bytes"): st.download_button("Download Multi-Building Cost Estimate Excel",st.session_state["xlsx_bytes"],"TS_LGS_Multi_Building_Cost_Estimate.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)

with tab4:
    st.subheader("Indicative Saudi Cost Baseline"); st.caption("Estimating baselines, not supplier quotations. Update with current TS procurement prices before commercial submission."); st.dataframe(pd.DataFrame(price_database()),use_container_width=True,hide_index=True)
