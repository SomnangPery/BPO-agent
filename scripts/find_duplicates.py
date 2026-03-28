import sqlite3
import re
import sys

DB = 'ic_agent.db'

def normalize(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', name.lower())

if __name__ == '__main__':
    q = ' '.join(sys.argv[1:]).strip()
    if not q:
        print('Usage: python scripts/find_duplicates.py "name"')
        sys.exit(1)
    nq = normalize(q)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute('SELECT id, name, student_identifier FROM students').fetchall()
    matches = []
    for r in rows:
        n = normalize(r['name'] or '')
        if nq and (nq in n or n in nq):
            matches.append(dict(r))
    if not matches:
        print('No matching students found for:', q)
        sys.exit(0)
    print(f"Found {len(matches)} matching students for: {q}\n")
    for m in matches:
        # get submission counts
        counts = cur.execute('SELECT COUNT(*) as total, SUM(CASE WHEN status = "pending" THEN 1 ELSE 0 END) as pending FROM reports WHERE student_id = ?', (m['id'],)).fetchone()
        total = counts['total'] or 0
        pending = counts['pending'] or 0
        print(f"ID: {m['id']}\tIdentifier: {m.get('student_identifier') or '-'}\tName: {m['name']}\tTotal submissions: {total}\tPending: {pending}")
    conn.close()
