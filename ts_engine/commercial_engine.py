import csv, io, re
from pathlib import Path
from typing import Any


def _num(v):
    if v is None: return None
    s=str(v).strip().replace(',', '').replace('SAR','').replace('ر.س','')
    m=re.search(r'-?\d+(?:\.\d+)?', s)
    try: return float(m.group()) if m else None
    except: return None


def normalize_price_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out=[]
    aliases={
        'description':['description','item','product','material','service','scope','name'],
        'code':['code','item code','sku','part number','part no','model'],
        'unit':['unit','uom'],
        'unit_cost':['unit cost','cost','buying price','purchase price','rate','cost price'],
        'unit_sell':['unit sell','selling price','sales price','sell price','price'],
        'vendor':['vendor','supplier','manufacturer','make'],
    }
    for r in rows:
        low={str(k).strip().lower():v for k,v in r.items()}
        n={}
        for key,names in aliases.items():
            for name in names:
                if name in low and str(low[name]).strip(): n[key]=low[name]; break
        if n.get('description') or n.get('code'):
            n['unit_cost']=_num(n.get('unit_cost'))
            n['unit_sell']=_num(n.get('unit_sell'))
            out.append(n)
    return out


def parse_price_file(path: str) -> list[dict[str, Any]]:
    p=Path(path); ext=p.suffix.lower(); rows=[]
    if ext in {'.xlsx','.xls'}:
        import pandas as pd
        book=pd.read_excel(p, sheet_name=None)
        for sh,df in book.items():
            for rec in df.fillna('').to_dict('records'):
                rec['_sheet']=sh; rows.append(rec)
    elif ext=='.csv':
        with open(p,'r',encoding='utf-8-sig',errors='ignore',newline='') as f:
            rows=list(csv.DictReader(f))
    return normalize_price_rows(rows)


def _tokens(s):
    stop={'the','and','for','with','supply','install','installation','system','complete','including','of','to','a','an'}
    return {x for x in re.findall(r'[a-z0-9]{2,}', str(s).lower()) if x not in stop}


def match_boq_to_prices(boq: list[dict], prices: list[dict], default_margin_pct: float=25.0) -> list[dict]:
    out=[]
    for i,b in enumerate(boq or [],1):
        desc=str(b.get('description','')); bt=_tokens(desc); best=None; bestscore=0
        for p in prices:
            pt=_tokens(str(p.get('description',''))+' '+str(p.get('code','')))
            score=(len(bt & pt)/max(1,len(bt | pt))) if bt and pt else 0
            if score>bestscore: bestscore=score; best=p
        qty=_num(b.get('quantity')) or 1.0
        matched=best if bestscore>=0.12 else None
        cost=matched.get('unit_cost') if matched else None
        sell=matched.get('unit_sell') if matched else None
        if sell is None and cost is not None and default_margin_pct < 100:
            sell=cost/(1-default_margin_pct/100)
        total_cost=qty*cost if cost is not None else None
        total_sell=qty*sell if sell is not None else None
        margin=((total_sell-total_cost)/total_sell*100) if total_sell and total_cost is not None else None
        out.append({
            'No.':i,'BOQ Description':desc,'Qty':qty,'Unit':b.get('unit',''),
            'Matched Price Item': matched.get('description','') if matched else '',
            'Item Code': matched.get('code','') if matched else '', 'Vendor': matched.get('vendor','') if matched else '',
            'Match Confidence %': round(bestscore*100), 'Unit Cost SAR':cost,'Unit Sell SAR':sell,
            'Total Cost SAR':round(total_cost,2) if total_cost is not None else None,
            'Total Sell SAR':round(total_sell,2) if total_sell is not None else None,
            'Margin %':round(margin,1) if margin is not None else None,
            'Pricing Status':'PRICED' if cost is not None else 'UNPRICED',
            'Source': b.get('source_file',''), 'Page/Sheet': b.get('page') or b.get('sheet',''),
        })
    return out


def commercial_summary(rows: list[dict], contingency_pct: float=5.0) -> dict:
    cost=sum(float(r['Total Cost SAR']) for r in rows if r.get('Total Cost SAR') is not None)
    sell=sum(float(r['Total Sell SAR']) for r in rows if r.get('Total Sell SAR') is not None)
    priced=sum(1 for r in rows if r.get('Pricing Status')=='PRICED'); total=len(rows); unpriced=total-priced
    contingency=cost*contingency_pct/100
    cost_with_cont=cost+contingency
    gp=sell-cost_with_cont
    margin=(gp/sell*100) if sell else 0
    coverage=(priced/total*100) if total else 0
    return {'priced_items':priced,'unpriced_items':unpriced,'pricing_coverage_pct':round(coverage,1),
            'estimated_cost_sar':round(cost,2),'contingency_sar':round(contingency,2),
            'cost_with_contingency_sar':round(cost_with_cont,2),'estimated_sell_sar':round(sell,2),
            'gross_profit_sar':round(gp,2),'expected_margin_pct':round(margin,1)}


def procurement_actions(rows: list[dict]) -> list[dict]:
    actions=[]
    for r in rows:
        if r.get('Pricing Status')=='UNPRICED':
            actions.append({'Priority':'High','Action':f"Obtain vendor quotation for: {r.get('BOQ Description','')}",'Vendor':r.get('Vendor',''),'Status':'Open'})
        elif (r.get('Match Confidence %') or 0)<35:
            actions.append({'Priority':'Medium','Action':f"Verify price-list match for: {r.get('BOQ Description','')}",'Vendor':r.get('Vendor',''),'Status':'Open'})
    vendors=sorted({str(r.get('Vendor')).strip() for r in rows if str(r.get('Vendor','')).strip()})
    for v in vendors:
        actions.append({'Priority':'Medium','Action':f'Confirm quotation validity, lead time and commercial terms with {v}','Vendor':v,'Status':'Open'})
    return actions


def commercial_go_no_go(tender_score: float, summary: dict, min_margin_pct: float=15.0) -> dict:
    coverage=summary.get('pricing_coverage_pct',0); margin=summary.get('expected_margin_pct',0)
    score=0.5*float(tender_score or 0)+0.25*coverage+0.25*max(0,min(100,margin*4))
    if coverage < 50: rec='HOLD - PRICING INCOMPLETE'
    elif margin < min_margin_pct: rec='COMMERCIAL REVIEW'
    elif score >= 75: rec='GO'
    elif score >= 60: rec='CONDITIONAL GO'
    else: rec='REVIEW / NO-GO'
    return {'commercial_decision_score':round(score,1),'recommendation':rec,'minimum_margin_pct':min_margin_pct,
            'pricing_coverage_pct':coverage,'expected_margin_pct':margin}
