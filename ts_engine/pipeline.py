import sqlite3
from datetime import datetime, timezone, date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / 'ts_projects.db'


def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('''CREATE TABLE IF NOT EXISTS pipeline (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        opportunity TEXT NOT NULL,
        client TEXT,
        owner TEXT,
        stage TEXT DEFAULT 'Qualification',
        probability REAL DEFAULT 25,
        estimated_value REAL DEFAULT 0,
        expected_margin REAL DEFAULT 0,
        deadline TEXT,
        next_action TEXT,
        status TEXT DEFAULT 'Open',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )''')
    return con


def upsert_opportunity(opportunity: str, client: str='', owner: str='', stage: str='Qualification', probability: float=25,
                       estimated_value: float=0, expected_margin: float=0, deadline: str='', next_action: str='', project_id=None):
    now=datetime.now(timezone.utc).isoformat(); con=_conn()
    if project_id:
        row=con.execute('SELECT id FROM pipeline WHERE project_id=?',(int(project_id),)).fetchone()
        if row:
            con.execute('''UPDATE pipeline SET opportunity=?,client=?,owner=?,stage=?,probability=?,estimated_value=?,expected_margin=?,deadline=?,next_action=?,updated_at=? WHERE project_id=?''',
                        (opportunity,client,owner,stage,probability,estimated_value,expected_margin,deadline,next_action,now,int(project_id)))
            con.commit(); oid=row['id']; con.close(); return int(oid)
    cur=con.execute('''INSERT INTO pipeline(project_id,opportunity,client,owner,stage,probability,estimated_value,expected_margin,deadline,next_action,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',(project_id,opportunity or 'Untitled',client,owner,stage,probability,estimated_value,expected_margin,deadline,next_action,now,now))
    con.commit(); oid=cur.lastrowid; con.close(); return int(oid)


def list_pipeline(limit=500):
    con=_conn(); rows=con.execute('SELECT * FROM pipeline ORDER BY COALESCE(deadline,\'9999-12-31\'), id DESC LIMIT ?',(limit,)).fetchall(); con.close()
    return [dict(r) for r in rows]


def update_stage(opp_id:int, stage:str, probability:float|None=None):
    con=_conn(); now=datetime.now(timezone.utc).isoformat()
    if probability is None: con.execute('UPDATE pipeline SET stage=?,updated_at=? WHERE id=?',(stage,now,int(opp_id)))
    else: con.execute('UPDATE pipeline SET stage=?,probability=?,updated_at=? WHERE id=?',(stage,probability,now,int(opp_id)))
    con.commit(); con.close()


def pipeline_metrics(rows=None):
    rows=rows if rows is not None else list_pipeline()
    open_rows=[r for r in rows if str(r.get('status','Open')).lower()!='closed']
    total=sum(float(r.get('estimated_value') or 0) for r in open_rows)
    weighted=sum(float(r.get('estimated_value') or 0)*float(r.get('probability') or 0)/100 for r in open_rows)
    gp=sum(float(r.get('estimated_value') or 0)*float(r.get('expected_margin') or 0)/100 for r in open_rows)
    today=date.today(); due7=0; overdue=0
    for r in open_rows:
        try:
            d=date.fromisoformat(str(r.get('deadline') or '')[:10]); days=(d-today).days
            if days<0: overdue+=1
            elif days<=7: due7+=1
        except: pass
    return {'open_opportunities':len(open_rows),'pipeline_value':round(total,2),'weighted_pipeline':round(weighted,2),'expected_gross_profit':round(gp,2),'due_next_7_days':due7,'overdue':overdue}


def deadline_alerts(rows=None, days=14):
    rows=rows if rows is not None else list_pipeline(); today=date.today(); out=[]
    for r in rows:
        if str(r.get('status','Open')).lower()=='closed': continue
        try:
            d=date.fromisoformat(str(r.get('deadline') or '')[:10]); delta=(d-today).days
        except: continue
        if delta <= days:
            out.append({**r,'days_to_deadline':delta,'alert':'OVERDUE' if delta<0 else ('URGENT' if delta<=3 else 'UPCOMING')})
    return sorted(out,key=lambda x:x['days_to_deadline'])
