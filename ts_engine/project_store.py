import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / 'ts_projects.db'


def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT NOT NULL,
        client TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        status TEXT DEFAULT 'Analyzed',
        analysis_json TEXT,
        corpus TEXT
    )''')
    return con


def save_project(project_name: str, client: str, analysis: dict, corpus: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    con = _conn()
    cur = con.execute(
        'INSERT INTO projects(project_name, client, created_at, updated_at, analysis_json, corpus) VALUES(?,?,?,?,?,?)',
        (project_name or 'Untitled Project', client or '', now, now, json.dumps(analysis, ensure_ascii=False), corpus or '')
    )
    con.commit()
    pid = cur.lastrowid
    con.close()
    return int(pid)


def list_projects(limit: int = 100) -> list[dict]:
    con = _conn()
    rows = con.execute('SELECT id, project_name, client, created_at, updated_at, status FROM projects ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def load_project(project_id: int) -> dict | None:
    con = _conn()
    row = con.execute('SELECT * FROM projects WHERE id=?', (int(project_id),)).fetchone()
    con.close()
    if not row:
        return None
    data = dict(row)
    data['analysis'] = json.loads(data.pop('analysis_json') or '{}')
    return data


def delete_project(project_id: int) -> None:
    con = _conn()
    con.execute('DELETE FROM projects WHERE id=?', (int(project_id),))
    con.commit()
    con.close()
