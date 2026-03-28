from ic_agent.drive import list_student_files
from ic_agent.config import GOOGLE_DRIVE_FOLDER_ID

if __name__ == '__main__':
    folder = GOOGLE_DRIVE_FOLDER_ID
    print('Using folder id:', folder)
    try:
        files = list_student_files(folder)
        print('Found', len(files), 'files')
        for f in files[:50]:
            print(f.get('id'), f.get('name'), f.get('mimeType'))
    except Exception as e:
        import traceback

        traceback.print_exc()
        print('Error:', e)
