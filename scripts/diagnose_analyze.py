from ic_agent.config import GOOGLE_DRIVE_FOLDER_ID, GOOGLE_OPPM_FOLDER_ID, GOOGLE_SRS_FOLDER_ID
from ic_agent.database import search_students_by_name, get_latest_report_for_student
from ic_agent.drive import list_student_files, list_files_recursive, read_file_content
from ic_agent.analyzer import analyze_student_work
import json

STUDENT_ID = 1

print('GOOGLE_DRIVE_FOLDER_ID=', GOOGLE_DRIVE_FOLDER_ID)
print('GOOGLE_OPPM_FOLDER_ID=', GOOGLE_OPPM_FOLDER_ID)
print('GOOGLE_SRS_FOLDER_ID=', GOOGLE_SRS_FOLDER_ID)

students = [s for s in search_students_by_name('') if s.get('id') == STUDENT_ID]
if not students:
    print('student not found')
    raise SystemExit(1)
student = students[0]
student_name = student.get('name')
print('Found student:', student_name, 'id=', STUDENT_ID)

# Collect files
files = []
if GOOGLE_OPPM_FOLDER_ID or GOOGLE_SRS_FOLDER_ID:
    try:
        if GOOGLE_OPPM_FOLDER_ID:
            print('Listing OPPM folder...')
            files += list_student_files(GOOGLE_OPPM_FOLDER_ID)
        if GOOGLE_SRS_FOLDER_ID:
            print('Listing SRS folder...')
            files += list_student_files(GOOGLE_SRS_FOLDER_ID)
    except Exception as e:
        print('Error listing explicit folders:', e)
else:
    try:
        print('Recursively listing under main folder...')
        files = list_files_recursive(GOOGLE_DRIVE_FOLDER_ID)
    except Exception as e:
        print('Recursive list failed, falling back to non-recursive:', e)
        try:
            files = list_student_files(GOOGLE_DRIVE_FOLDER_ID)
        except Exception as e2:
            print('Non-recursive list also failed:', e2)

print('Total files found:', len(files))
# show first 10
for f in files[:10]:
    print('-', f.get('id'), f.get('name'), f.get('parent_folder_name', ''))

# find oppm/srs
def matches_for_type(f, token):
    name = str(f.get('name','') or '')
    parent = str(f.get('parent_folder_name','') or '')
    return token in name.lower() or token in parent.lower()

oppm = next((f for f in files if matches_for_type(f,'oppm') and f.get('name') and f.get('name') and True), None)
srs = next((f for f in files if matches_for_type(f,'srs') and f.get('name') and True), None)

print('OPPM:', oppm)
print('SRS :', srs)

if not oppm or not srs:
    print('Could not locate OPPM and SRS files for this student in Drive.')
    raise SystemExit(2)

# read content
try:
    print('Reading OPPM content...')
    oppm_content = read_file_content(oppm['id'])
    print('OPPM length:', len(oppm_content))
except Exception as e:
    print('Failed to read OPPM:', e)
    raise

try:
    print('Reading SRS content...')
    srs_content = read_file_content(srs['id'])
    print('SRS length:', len(srs_content))
except Exception as e:
    print('Failed to read SRS:', e)
    raise

# run analysis
try:
    print('Running analyzer...')
    analysis = analyze_student_work(student_name, oppm_content, srs_content)
    print('Analysis result keys:', list(analysis.keys()))
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
except Exception as e:
    print('Analyzer exception:', e)
    raise
