from ic_agent.config import GOOGLE_OPPM_FOLDER_ID, GOOGLE_SRS_FOLDER_ID
from ic_agent.drive import list_student_files
from ic_agent.web import _extract_student_name_from_filename


def dump(folder_id: str, label: str):
    print(f'--- {label} ({folder_id}) ---')
    files = list_student_files(folder_id)
    print('count=', len(files))
    for f in files[:50]:
        name = f.get('name', '')
        parsed = _extract_student_name_from_filename(name)
        print(f"{name}  =>  {parsed}")


if __name__ == '__main__':
    if GOOGLE_OPPM_FOLDER_ID:
        dump(GOOGLE_OPPM_FOLDER_ID, 'OPPM')
    if GOOGLE_SRS_FOLDER_ID:
        dump(GOOGLE_SRS_FOLDER_ID, 'SRS')
