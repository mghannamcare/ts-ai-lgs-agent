import re

def _num(v):
    try:
        if v is None or v=='': return None
        m=re.search(r'-?\d+(?:\.\d+)?', str(v).replace(',',''))
        return float(m.group()) if m else None
    except: return None


def normalize_vendor_quotes(rows):
    out=[]
    aliases={
      'item':['item','description','product','material','boq description'],
      'vendor':['vendor','supplier','manufacturer'],
      'unit_price':['unit price','price','rate','unit cost','cost'],
      'lead_time_days':['lead time','lead time days','delivery days'],
      'warranty_months':['warranty','warranty months'],
      'validity_days':['validity','validity days'],
      'payment_terms':['payment terms','terms'],
    }
    for r in rows:
        low={str(k).strip().lower():v for k,v in r.items()}; n={}
        for key,names in aliases.items():
            for name in names:
                if name in low and str(low[name]).strip()!='': n[key]=low[name]; break
        if n.get('item') and n.get('vendor'):
            for k in ('unit_price','lead_time_days','warranty_months','validity_days'): n[k]=_num(n.get(k))
            out.append(n)
    return out


def vendor_comparison(rows, price_weight=50, lead_weight=25, warranty_weight=15, validity_weight=10):
    groups={}
    for r in normalize_vendor_quotes(rows): groups.setdefault(str(r['item']),[]).append(r)
    result=[]
    for item,quotes in groups.items():
        prices=[q['unit_price'] for q in quotes if q.get('unit_price') not in (None,0)]; leads=[q['lead_time_days'] for q in quotes if q.get('lead_time_days') is not None]
        warranties=[q['warranty_months'] for q in quotes if q.get('warranty_months') is not None]; validities=[q['validity_days'] for q in quotes if q.get('validity_days') is not None]
        minp=min(prices) if prices else None; minlead=min(leads) if leads else None; maxwar=max(warranties) if warranties else None; maxval=max(validities) if validities else None
        ranked=[]
        for q in quotes:
            ps=(minp/q['unit_price']*100) if minp and q.get('unit_price') else 0
            ls=(minlead/q['lead_time_days']*100) if minlead is not None and q.get('lead_time_days') not in (None,0) else 0
            ws=(q.get('warranty_months')/maxwar*100) if maxwar and q.get('warranty_months') is not None else 0
            vs=(q.get('validity_days')/maxval*100) if maxval and q.get('validity_days') is not None else 0
            score=(ps*price_weight+ls*lead_weight+ws*warranty_weight+vs*validity_weight)/100
            ranked.append({**q,'commercial_score':round(score,1)})
        ranked.sort(key=lambda x:x['commercial_score'],reverse=True)
        for idx,q in enumerate(ranked,1): result.append({**q,'rank':idx,'recommended':'YES' if idx==1 else ''})
    return result


def margin_scenarios(cost: float, base_sell: float, discounts=(0,5,10), cost_escalations=(0,5,10)):
    out=[]
    cost=float(cost or 0); base_sell=float(base_sell or 0)
    for d in discounts:
        for e in cost_escalations:
            sell=base_sell*(1-float(d)/100); adj_cost=cost*(1+float(e)/100); gp=sell-adj_cost; margin=(gp/sell*100) if sell else 0
            out.append({'Discount %':d,'Cost Escalation %':e,'Sell SAR':round(sell,2),'Cost SAR':round(adj_cost,2),'Gross Profit SAR':round(gp,2),'Margin %':round(margin,1)})
    return out
