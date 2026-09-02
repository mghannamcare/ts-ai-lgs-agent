import csv, io, re

def extract_boq(corpus: str, limit=300):
    rows=[]; src=''; sheet=''; page=''
    for line in (corpus or '').splitlines():
        m=re.match(r'\[SOURCE FILE: ([^\]|]+)',line)
        if m: src=m.group(1).strip(); continue
        m=re.match(r'\[PAGE (\d+)\]',line)
        if m: page=m.group(1); continue
        m=re.match(r'\[SHEET: (.+?)\]',line)
        if m: sheet=m.group(1); continue
        if ',' in line:
            try: vals=next(csv.reader(io.StringIO(line)))
            except: vals=[]
            vals=[v.strip() for v in vals]
            if 2 <= len(vals) <= 20 and any(re.search(r'\d',v) for v in vals):
                desc=max(vals,key=len) if vals else ''
                nums=[v for v in vals if re.fullmatch(r'[-+]?\d+(?:\.\d+)?',v.replace(',',''))]
                if desc and len(desc)>4:
                    rows.append({'source_file':src,'page':page,'sheet':sheet,'description':desc[:500], 'quantity':nums[0] if nums else '', 'unit':'', 'raw_row':' | '.join(vals)[:1200]})
        if len(rows)>=limit: break
    return rows
