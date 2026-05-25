import os
import sys
import logging
from ic_agent.config import GOOGLE_DRIVE_FOLDER_ID
from ic_agent.database import init_db, get_or_create_project, save_submission, update_submission_analysis
from ic_agent.drive import get_all_projects, classify_project_files
from ic_agent.analyzer import analyze_project
from ic_agent.reports import format_report_message

logging.basicConfig(level=logging.ERROR)

def main():
    init_db()
    print("Welcome to IC Agent (Project-Only Mode)")
    print("Type 'analyze [project name]' or 'exit'")
    
    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in ("exit", "quit"):
                break
            
            if user_input.lower().startswith("analyze "):
                project_query = user_input[8:].strip()
                
                # 1. Find
                all_p = get_all_projects(GOOGLE_DRIVE_FOLDER_ID)
                matches = [p for p in all_p if project_query.lower() in p["project_name"].lower()]
                
                if not matches:
                    print(f"No project found matching '{project_query}'")
                    continue
                if len(matches) > 1:
                    print(f"Multiple matches: {', '.join(m['project_name'] for m in matches)}")
                    continue
                    
                target = matches[0]
                p_name = target["project_name"]
                f_id = target["folder_id"]
                
                print(f"📁 Project: {p_name}")
                print("⏳ Classifying files...")
                
                # 2. Classify
                classified = classify_project_files(f_id)
                
                # 3. DB
                project_record = get_or_create_project(p_name, f_id)
                sub_id = save_submission(project_record["id"], [r["file_name"] for r in classified["reports"]])
                
                print("🧠 Running AI analysis (5 steps)...")
                # 4. Analyze
                analysis = analyze_project(p_name, classified)
                
                # 5. Save & Report
                update_submission_analysis(sub_id, analysis)
                print(format_report_message(analysis))
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
