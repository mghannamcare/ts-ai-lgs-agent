from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak


def _money(v):
    try: return f"SAR {float(v):,.0f}"
    except: return "-"


def build_executive_pdf(analysis: dict, scorecard: dict, commercial: dict, output_path: str|Path):
    output_path=Path(output_path)
    doc=SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=16*mm,leftMargin=16*mm,topMargin=15*mm,bottomMargin=15*mm)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TSHeading', parent=styles['Heading2'], fontSize=13, leading=16, spaceBefore=8, spaceAfter=6))
    styles.add(ParagraphStyle(name='Small', parent=styles['BodyText'], fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name='Body2', parent=styles['BodyText'], fontSize=9.5, leading=13, alignment=TA_LEFT))
    story=[]
    story.append(Paragraph("TS AI Tender & Sales Engineer", styles['Title']))
    story.append(Paragraph("Executive Tender Assessment - AI Assisted Draft", styles['Heading3']))
    story.append(Spacer(1,5*mm))
    meta=[['Project', analysis.get('project','')],['Client',analysis.get('client','')],['Recommendation',scorecard.get('recommendation','')],['Tender Score',f"{scorecard.get('overall_score',0)}/100"],['AI Confidence',f"{analysis.get('confidence',0)}%"]]
    t=Table(meta,colWidths=[42*mm,125*mm]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),colors.HexColor('#EEEEEE')),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#CCCCCC')),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6)])); story.append(t)
    story.append(Paragraph('Executive Summary',styles['TSHeading'])); story.append(Paragraph(str(analysis.get('executive_summary','')),styles['Body2']))
    if commercial:
        story.append(Paragraph('Commercial Snapshot',styles['TSHeading']))
        cm=[['ROM Sell',_money(commercial.get('estimated_sell_sar'))],['Cost + Contingency',_money(commercial.get('cost_with_contingency_sar'))],['Expected Gross Profit',_money(commercial.get('expected_gross_profit_sar'))],['Expected Margin',f"{commercial.get('expected_margin_pct',0):.1f}%"],['Pricing Coverage',f"{commercial.get('pricing_coverage_pct',0):.0f}%"]]
        ct=Table(cm,colWidths=[55*mm,70*mm]); ct.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#CCCCCC')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#F5F5F5')),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9)])); story.append(ct)
    for title,key in [('Key Scope','scope_of_work'),('Key Risks','risks'),('Required Clarifications','clarifications'),('Recommended Next Actions','next_actions')]:
        story.append(Paragraph(title,styles['TSHeading']))
        vals=analysis.get(key,[]) or []
        if vals:
            for x in vals[:10]: story.append(Paragraph(f"- {x}",styles['Body2']))
        else: story.append(Paragraph('-',styles['Body2']))
    sols=analysis.get('ts_solutions',[]) or []
    if sols:
        story.append(PageBreak()); story.append(Paragraph('TS Solution Fit',styles['TSHeading']))
        data=[['Requirement','TS Solution','Match']]
        for x in sols[:20]: data.append([str(x.get('Requirement','')),str(x.get('TS Solution','')),str(x.get('Match',''))])
        st=Table(data,colWidths=[52*mm,91*mm,24*mm],repeatRows=1); st.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#222222')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#BBBBBB')),('FONTSIZE',(0,0),(-1,-1),8),('VALIGN',(0,0),(-1,-1),'TOP')])) ; story.append(st)
    story.append(Spacer(1,7*mm)); story.append(Paragraph('Disclaimer: AI-assisted pre-tender assessment. Technical, contractual, commercial and compliance outputs require authorized TS review before submission or commitment.',styles['Small']))
    doc.build(story)
    return output_path
