import argparse
import json
import traceback
from typing import Optional

from ic_agent.config import GOOGLE_DRIVE_FOLDER_ID, GOOGLE_CREDENTIALS_PATH
from ic_agent.drive import list_student_files
from ic_agent.web import _extract_student_name_from_filename, _identifier_from_name
from ic_agent.database import add_student, save_report


def read_service_account_email() -> Optional[str]:
    try:
        with open(GOOGLE_CREDENTIALS_PATH, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            return data.get('client_email')
    except Exception:
        return None


def main(folder_id: Optional[str] = None, dry_run: bool = True):
    folder_id = folder_id or GOOGLE_DRIVE_FOLDER_ID
    if not folder_id:
        raise ValueError("GOOGLE_DRIVE_FOLDER_ID is not set. Export it or pass --folder.")

    print('Using folder id:', folder_id)
    sa_email = read_service_account_email()
    if sa_email:
        print('Service account email:', sa_email)

    files = list_student_files(folder_id)
    print('Found files:', [f['name'] for f in files])

    pairs = []
    used = set()
    for f in files:
        name = f['name']
        parsed = _extract_student_name_from_filename(name)
        if not parsed:
            continue
        if parsed in used:
            continue
        oppm = next((x for x in files if 'oppm' in x['name'].lower() and parsed == (_extract_student_name_from_filename(x['name']) or '')), None)
        srs = next((x for x in files if 'srs' in x['name'].lower() and parsed == (_extract_student_name_from_filename(x['name']) or '')), None)
        if not oppm or not srs:
            candidates = [x for x in files if parsed == (_extract_student_name_from_filename(x['name']) or '')]
            if len(candidates) >= 2:
                oppm, srs = candidates[0], candidates[1]
        if oppm and srs:
            pairs.append((parsed, oppm, srs))
            used.add(parsed)

    print('Pairs found:', [(p[0], p[1]['name'], p[2]['name']) for p in pairs])

    created = 0
    for parsed, oppm, srs in pairs:
        identifier = _identifier_from_name(parsed)
        if dry_run:
            print(f"[dry-run] Would add student: {parsed} (id {identifier}) and save report: {oppm['name']}, {srs['name']}")
        else:
            sid = add_student(parsed, identifier, None)
            fname = f"{oppm['name']}, {srs['name']}"
            rid = save_report(sid, fname, '{}')
            print('Saved report', rid, 'for student', sid, parsed)
            created += 1

    print('Reports created (real):', created)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sync reports from Google Drive folder')
    parser.add_argument('--folder', '-f', help='Google Drive folder id to scan')
    parser.add_argument('--no-dry-run', dest='dry_run', action='store_false', help='Actually create students/reports in DB')
    args = parser.parse_args()

    try:
        main(folder_id=args.folder, dry_run=args.dry_run)
    except Exception:
        traceback.print_exc()
        raise
