import json, traceback
from ic_agent.config import GOOGLE_DRIVE_FOLDER_ID, GOOGLE_CREDENTIALS_PATH
from ic_agent import drive

print('GOOGLE_DRIVE_FOLDER_ID=', GOOGLE_DRIVE_FOLDER_ID)
try:
    with open(GOOGLE_CREDENTIALS_PATH, 'r', encoding='utf-8') as f:
        creds = json.load(f)
    print('service_account_email=', creds.get('client_email'))
except Exception as e:
    print('failed reading creds:', e)

try:
    files = drive.list_student_files(GOOGLE_DRIVE_FOLDER_ID)
    print('files_count=', len(files))
    print('files:', [f.get('name') for f in files])
except Exception:
    print('list_student_files error')
    traceback.print_exc()

try:
    svc = drive._get_drive_service()
    meta = svc.files().get(fileId=GOOGLE_DRIVE_FOLDER_ID, fields='id,name,mimeType', supportsAllDrives=True).execute()
    print('folder_meta:', meta)
except Exception:
    print('get folder metadata error')
    traceback.print_exc()
