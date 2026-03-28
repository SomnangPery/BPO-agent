import sqlite3, json
conn = sqlite3.connect('ic_agent.db')
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT r.id, s.name AS student_name, r.file_name, r.status, r.ai_analysis FROM reports r JOIN students s ON s.id = r.student_id ORDER BY r.submitted_at DESC"
).fetchall()
print(json.dumps([dict(row) for row in rows], indent=2))
