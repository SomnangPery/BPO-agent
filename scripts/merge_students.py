import sqlite3
import shutil
import sys
import time
from pathlib import Path

DB = 'ic_agent.db'

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python scripts/merge_students.py <source_id> <target_id>')
        sys.exit(1)
    source = int(sys.argv[1])
    target = int(sys.argv[2])

    db_path = Path(DB)
    if not db_path.exists():
        print('Database not found:', DB)
        sys.exit(1)

    # backup
    ts = time.strftime('%Y%m%d-%H%M%S')
    backup = db_path.with_suffix(f'.db.backup.{ts}')
    shutil.copy2(db_path, backup)
    print('Backup created at', backup)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        # verify students exist
        s = cur.execute('SELECT id, name FROM students WHERE id = ?', (source,)).fetchone()
        t = cur.execute('SELECT id, name FROM students WHERE id = ?', (target,)).fetchone()
        if not s:
            print('Source student not found:', source)
            sys.exit(1)
        if not t:
            print('Target student not found:', target)
            sys.exit(1)
        print(f"Merging reports from {s['id']} ({s['name']}) into {t['id']} ({t['name']})")

        before_source = cur.execute('SELECT COUNT(*) as c FROM reports WHERE student_id = ?', (source,)).fetchone()['c']
        before_target = cur.execute('SELECT COUNT(*) as c FROM reports WHERE student_id = ?', (target,)).fetchone()['c']
        print('Reports before - source:', before_source, 'target:', before_target)

        # perform update and delete inside transaction
        cur.execute('BEGIN')
        cur.execute('UPDATE reports SET student_id = ? WHERE student_id = ?', (target, source))
        cur.execute('DELETE FROM students WHERE id = ?', (source,))
        conn.commit()

        after_source = cur.execute('SELECT COUNT(*) as c FROM reports WHERE student_id = ?', (source,)).fetchone()['c']
        after_target = cur.execute('SELECT COUNT(*) as c FROM reports WHERE student_id = ?', (target,)).fetchone()['c']
        print('Reports after - source:', after_source, 'target:', after_target)
        print('Merge completed successfully.')
    except Exception as e:
        conn.rollback()
        print('Merge failed:', e)
        print('Restoring backup...')
        shutil.copy2(backup, db_path)
        print('Restored from', backup)
        sys.exit(1)
    finally:
        conn.close()
