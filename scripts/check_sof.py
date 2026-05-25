import os
from ic_agent.config import GOOGLE_DRIVE_FOLDER_ID
from ic_agent.drive import list_files_recursive, classify_project_files

def check_sof():
    print(f"Root Folder ID: {GOOGLE_DRIVE_FOLDER_ID}")
    files = list_files_recursive(GOOGLE_DRIVE_FOLDER_ID)
    print(f"Total files found recursively: {len(files)}")
    
    student_name = "Sof"
    print(f"\nSearching for files belonging to: {student_name}")
    
    student_name_lower = student_name.lower()
    for f in files:
        name = f.get('name', '').lower()
        parent = f.get('parent_folder_name', '').lower()
        parent_path_names = [p.lower() for p in f.get('parent_path_names', [])]

        # Simulated logic from web.py
        meta = _extract_submission_meta(name, parent, parent_path_names)
        belongs = _submission_belongs_to_student(f, "report", student_name_lower) or \
                  _submission_belongs_to_student(f, "oppm", student_name_lower) or \
                  _submission_belongs_to_student(f, "srs", student_name_lower)

        kind = _detect_kind_from_text(name, parent)

        if student_name_lower in name or student_name_lower in parent or belongs:
            print(f"File: {f.get('name')}")
            print(f"  Parent: {f.get('parent_folder_name')}")
            print(f"  Meta: {meta}")
            print(f"  Detected Kind: {kind}")
            print(f"  Belongs to {student_name}: {belongs}")
            print("-" * 20)

def _extract_submission_meta(name, parent, parent_path_names):
    return {
        "name": name,
        "parent": parent,
        "path": "/".join(parent_path_names)
    }

def _submission_belongs_to_student(file, kind, student_name):
    return kind in file.get("name", "").lower() and student_name.lower() in file.get("name", "").lower()

def _detect_kind_from_text(name, parent):
    if "oppm" in name.lower() or "oppm" in parent.lower():
        return "oppm"
    elif "srs" in name.lower() or "srs" in parent.lower():
        return "srs"
    elif "report" in name.lower() or "report" in parent.lower():
        return "report"
    return "unknown"

if __name__ == '__main__':
    check_sof()
