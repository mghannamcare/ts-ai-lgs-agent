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
    price_database, parametric_takeoff, summarize, apply_overheads, ai_lgs_takeoff, price_ai_rows, benchmark_project_1_rows, benchmark_project_1_meta
)

load_dotenv()
st.set_page_config(page_title="TS AI – LGS Quantity & Cost Estimator", page_icon="🏗️", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.2rem;max-width:1500px}
.hero{padding:18px 22px;border:1px solid #ddd;border-radius:14px;margin-bottom:14px}
.hero h1{margin:0}.hero p{margin:5px 0 0;opacity:.75}
[data-testid="stMetric"]{border:1px solid #e5e5e5;padding:10px;border-radius:10px}
</style>""",unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>TS AI – LGS Quantity & Cost Estimator</h1><p>Drawings + Specifications + BOQ → Detailed LGS Quantity Takeoff → Labor Hours → Indicative Saudi Cost</p></div>',unsafe_allow_html=True)
st.warning("Cost rates are indicative Saudi-market baselines for estimating only. Confirm supplier/subcontractor quotations before issuing a commercial offer.")

if "rows" not in st.session_state: st.session_state.rows=[]
if "ai_result" not in st.session_state: st.session_state.ai_result={}
if "corpus" not in st.session_state: st.session_state.corpus=""

with st.sidebar:
    st.subheader("Engine")
    st.write("Document parser: Ready")
    st.write("AI/Vision:", "Ready" if os.getenv("OPENAI_API_KEY") else "API key required for drawing intelligence")
    st.caption("Supported locally: PDF, DOCX, XLS/XLSX, CSV, PNG/JPG. CAD/BIM should be exported to PDF for the final estimating workflow.")
    st.divider()
    if st.button("Load Demo Project - SRA Contractor Office", use_container_width=True):
        st.session_state.rows = benchmark_project_1_rows()
        st.session_state.ai_result = benchmark_project_1_meta()
        st.session_state.corpus = "Demo Project - SRA Contractor Office loaded from supplied SRA layout + BOQ. Quantities include assumptions and confidence levels."
        st.success("Demo Project - SRA Contractor Office loaded. Go to Cost Estimate tab.")
    st.divider()
    st.subheader("Cost Allowances")
    transport=st.number_input("Transport %",0.0,30.0,3.0,0.5)
    equipment=st.number_input("Equipment / consumables %",0.0,30.0,2.0,0.5)
    contingency=st.number_input("Contingency %",0.0,30.0,5.0,0.5)
    mep_rate=st.number_input("MEP provisional SAR/m²",0.0,2500.0,450.0,25.0)

tab1,tab2,tab3,tab4=st.tabs(["1. Upload & Extract","2. Quantity Takeoff","3. Cost Estimate","4. Price Database"])

with tab1:
    project=st.text_input("Project Name","LGS Building Estimate")
    files=st.file_uploader("Upload drawings, specifications and BOQ",accept_multiple_files=True,
        type=["pdf","docx","xlsx","xls","csv","png","jpg","jpeg","webp"])
    if st.button("Read Project Files",type="primary",use_container_width=True):
        corpus=[]; status=[]
        for f in files or []:
            suffix=Path(f.name).suffix
            tmp=Path(tempfile.gettempdir())/(f"ts_lgs_{abs(hash(f.name))}{suffix}")
            tmp.write_bytes(f.getvalue())
            try:
                parsed=parse_document(tmp); text=parsed.get("text","")
                if parsed.get("needs_vision") and os.getenv("OPENAI_API_KEY"):
                    urls=pdf_pages_as_data_urls(tmp,8) if suffix.lower()==".pdf" else [image_to_data_url(tmp)]
                    text += "\n"+extract_image_text_with_ai(urls,"Focus on dimensions, wall/roof/floor build-ups, openings, LGS framing notes, material specifications and quantities.")
                corpus.append(f"\n[SOURCE FILE: {f.name}]\n{text}")
                status.append({"File":f.name,"Type":parsed.get("file_type"),"Status":"Read","Needs Vision":parsed.get("needs_vision",False)})
            except Exception as e:
                status.append({"File":f.name,"Status":"Error","Details":str(e)})
        st.session_state.corpus="\n".join(corpus)
        st.dataframe(pd.DataFrame(status),use_container_width=True,hide_index=True)
        st.success(f"Files processed. Extracted corpus: {len(st.session_state.corpus):,} characters.")
    if st.session_state.corpus:
        with st.expander("Extracted source text"):
            st.text_area("Source",st.session_state.corpus[:120000],height=350)

with tab2:
    st.subheader("A. AI Takeoff from Uploaded Documents")
    if st.button("Generate LGS Takeoff from Documents",use_container_width=True):
        if not st.session_state.corpus:
            st.error("Upload and read project files first.")
        elif not os.getenv("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY is required for intelligent drawing/specification takeoff. Use the parametric estimator below for offline testing.")
        else:
            with st.spinner("Analyzing LGS scope..."):
                res=ai_lgs_takeoff(st.session_state.corpus,project)
                st.session_state.ai_result=res or {}
                st.session_state.rows=price_ai_rows((res or {}).get("quantity_rows",[]))
            st.success("LGS takeoff generated.")
    if st.session_state.ai_result:
        r=st.session_state.ai_result
        if r.get("dimensions"): st.write("**Benchmark dimensions:**", r["dimensions"], " | Area:", r.get("area_m2"), "m²")
        if r.get("building_dimensions"): st.write("**Detected dimensions:**",r["building_dimensions"])
        c1,c2=st.columns(2)
        with c1:
            st.write("**Assumptions**")
            for x in r.get("assumptions",[]): st.write("•",x)
        with c2:
            st.write("**Clarifications required**")
            for x in r.get("clarifications",[]): st.write("•",x)

    st.divider()
    st.subheader("B. Parametric Fallback / Quick Estimate")
    c1,c2,c3,c4=st.columns(4)
    L=c1.number_input("Length (m)",1.0,200.0,12.0,.5); W=c2.number_input("Width (m)",1.0,100.0,6.0,.5)
    H=c3.number_input("Wall height (m)",2.0,12.0,3.0,.1); P=c4.number_input("Internal partition length (m)",0.0,500.0,18.0,1.0)
    c1,c2,c3,c4=st.columns(4)
    ed=c1.number_input("External doors",0,100,2); idr=c2.number_input("Internal doors",0,200,4)
    wa=c3.number_input("Window area (m²)",0.0,500.0,12.0,1.0); steel=c4.number_input("LGS steel intensity (kg/m²)",15.0,90.0,38.0,1.0)
    if st.button("Generate Parametric Takeoff",use_container_width=True):
        st.session_state.rows=parametric_takeoff(L,W,H,P,ed,idr,wa,steel)
        st.session_state.ai_result={"assumptions":["Parametric estimate generated from entered dimensions. Verify against IFC/shop drawings."],
          "clarifications":[]}
        st.success("Parametric takeoff generated.")

    if st.session_state.rows:
        st.subheader("Detailed Quantity Takeoff")
        df=pd.DataFrame(st.session_state.rows)
        edited=st.data_editor(df,use_container_width=True,hide_index=True,num_rows="dynamic")
        st.session_state.rows=edited.to_dict("records")

with tab3:
    rows=st.session_state.rows
    if not rows:
        st.info("Generate a takeoff first.")
    else:
        priced=[r for r in rows if pd.notna(r.get("Material Cost SAR"))]
        total=apply_overheads(priced,transport,equipment,contingency)
        area_m2 = float((st.session_state.ai_result or {}).get("area_m2") or 0)
        mep_provisional = area_m2 * mep_rate if area_m2 else 0
        total["mep_provisional_sar"] = round(mep_provisional,2)
        total["estimated_cost_with_mep_sar"] = round(total["estimated_cost_sar"] + mep_provisional,2)
        c=st.columns(5)
        c[0].metric("Material Cost",f"{total['material_cost_sar']:,.0f} SAR")
        c[1].metric("Labor Hours",f"{total['labor_hours']:,.0f} h")
        c[2].metric("Labor Cost",f"{total['labor_cost_sar']:,.0f} SAR")
        c[3].metric("Direct Cost",f"{total['direct_cost_sar']:,.0f} SAR")
        c[4].metric("Estimated Cost",f"{total['estimated_cost_with_mep_sar']:,.0f} SAR")
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        unpriced=[r for r in rows if pd.isna(r.get("Material Cost SAR"))]
        if unpriced: st.warning(f"{len(unpriced)} item(s) require supplier pricing before the estimate is complete.")

        def make_xlsx():
            wb=Workbook(); ws=wb.active; ws.title="LGS Cost Estimate"
            headers=list(pd.DataFrame(rows).columns)
            ws.append(headers)
            for cell in ws[1]:
                cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor="17365D"); cell.alignment=Alignment(horizontal="center")
            for r in rows: ws.append([r.get(h) for h in headers])
            ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions
            for col in ws.columns:
                letter=col[0].column_letter
                ws.column_dimensions[letter].width=min(38,max(12,max(len(str(c.value or "")) for c in col)+2))
            s=wb.create_sheet("Cost Summary"); s.append(["Cost Component","SAR"])
            for k,label in [("material_cost_sar","Material"),("labor_cost_sar","Labor"),("transport_sar","Transport"),("equipment_consumables_sar","Equipment / Consumables"),("contingency_sar","Contingency"),("estimated_cost_sar","Estimated Cost excl. MEP"),("mep_provisional_sar","MEP Provisional"),("estimated_cost_with_mep_sar","Estimated Cost incl. MEP")]:
                s.append([label,total[k]])
            p=wb.create_sheet("Price Database"); pdb=price_database(); ph=list(pdb[0].keys()); p.append(ph)
            for x in pdb:p.append([x.get(h) for h in ph])
            out=Path(tempfile.gettempdir())/"TS_LGS_Detailed_Cost_Estimate.xlsx"; wb.save(out); return out
        if st.button("Prepare Excel Cost Estimate",type="primary",use_container_width=True):
            out=make_xlsx(); st.session_state["xlsx_bytes"]=out.read_bytes()
        if st.session_state.get("xlsx_bytes"):
            st.download_button("Download TS LGS Cost Estimate Excel",st.session_state["xlsx_bytes"],"TS_LGS_Detailed_Cost_Estimate.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)

with tab4:
    st.subheader("Indicative Saudi Cost Baseline")
    st.caption("These are estimating baselines, not supplier quotations. Update them when current TS procurement prices are available.")
    st.dataframe(pd.DataFrame(price_database()),use_container_width=True,hide_index=True)
