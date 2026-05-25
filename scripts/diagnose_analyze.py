from ic_agent.config import GOOGLE_DRIVE_FOLDER_ID, GOOGLE_OPPM_FOLDER_ID, GOOGLE_SRS_FOLDER_ID
from ic_agent.database import search_students_by_name, get_latest_report_for_student
from ic_agent.drive import classify_student_files
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

try:
    print('Classifying student files in Drive folder...')
    classified = classify_student_files(GOOGLE_DRIVE_FOLDER_ID)
except Exception as e:
    print('File classification failed:', e)
    raise

print('OPPM:', classified.get('oppm', {}).get('file_name', ''))
print('SRS :', classified.get('srs', {}).get('file_name', ''))
print('Report count:', len(classified.get('reports', [])))

# run analysis
try:
    print('Running analyzer...')
    analysis = analyze_student_work(student_name, classified)
    print('Analysis result keys:', list(analysis.keys()))
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
except Exception as e:
    print('Analyzer exception:', e)
    raise
