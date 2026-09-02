import re, sqlite3
from pathlib import Path

DB = Path.home()/'.ts_ai_tender_kb.sqlite3'

def _conn():
    c=sqlite3.connect(DB)
    c.execute('create table if not exists kb_chunks(id integer primary key, source text, chunk_no integer, content text)')
    try:c.execute('create virtual table if not exists kb_fts using fts5(content, source, content="kb_chunks", content_rowid="id")')
    except sqlite3.OperationalError: pass
    c.commit(); return c

def chunk_text(text, size=1800, overlap=250):
    text=re.sub(r'\n{3,}','\n\n',text or '').strip(); out=[]; i=0
    while i < len(text):
        out.append(text[i:i+size]); i += max(1,size-overlap)
    return out

def add_source(source, text):
    c=_conn(); cur=c.cursor(); cur.execute('delete from kb_chunks where source=?',(source,))
    for n,ch in enumerate(chunk_text(text),1): cur.execute('insert into kb_chunks(source,chunk_no,content) values(?,?,?)',(source,n,ch))
    c.commit(); c.close(); return n if text else 0

def list_sources():
    c=_conn(); rows=c.execute('select source,count(*),sum(length(content)) from kb_chunks group by source order by source').fetchall(); c.close()
    return [{'source':a,'chunks':b,'chars':d or 0} for a,b,d in rows]

def clear_source(source):
    c=_conn(); c.execute('delete from kb_chunks where source=?',(source,)); c.commit(); c.close()

def retrieve(query, top_k=8):
    c=_conn(); terms=[t for t in re.findall(r'[A-Za-z0-9_-]{3,}',query or '')][:20]
    rows=[]
    if terms:
        q=' OR '.join(terms)
        try: rows=c.execute('select source,content,bm25(kb_fts) from kb_fts where kb_fts match ? order by bm25(kb_fts) limit ?',(q,top_k)).fetchall()
        except sqlite3.OperationalError: rows=[]
    if not rows: rows=c.execute('select source,content,0 from kb_chunks order by id desc limit ?',(top_k,)).fetchall()
    c.close(); return [{'source':a,'content':b,'rank':r} for a,b,r in rows]
