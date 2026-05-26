"""
Test script demonstrating fuzzy matching capabilities for file classification and project name resolution.
"""

from ic_agent.fuzzy import (
    classify_file_by_name,
    match_project_name,
    get_file_category_with_confidence,
    get_project_match_with_confidence,
)


def test_file_classification():
    """Test file classification with various file names."""
    print("=" * 70)
    print("📄 FILE CLASSIFICATION TESTS")
    print("=" * 70)
    
    test_cases = [
        # OPPM variations
        "Tiger_OPPM.pdf",
        "OPPM.docx",
        "project_charter.pdf",
        "Project Charter v2.docx",
        "One Page Project Manager.pdf",
        "oppm_final.pdf",
        
        # SRS variations
        "Tiger_SRS.docx",
        "SRS_Final.pdf",
        "Software Requirements Specification.pdf",
        "srs_v2_final.docx",
        "functional_requirements.pdf",
        "system_requirements.pdf",
        
        # Report variations
        "Final_Report.pdf",
        "Report_v2.docx",
        "project_report.pdf",
        "implementation_report.docx",
        "Progress Report.pdf",
        "Submission_Final.pdf",
        
        # Edge cases
        "README.md",
        "notes.txt",
        "config.json",
        "project charter (draft).pdf",
        "srs_v1_updated_final_v3.docx",
    ]
    
    for file_name in test_cases:
        result = get_file_category_with_confidence(file_name)
        confidence_bar = "█" * (result["confidence"] // 10) + "░" * ((100 - result["confidence"]) // 10)
        confidence_icon = "✅" if result["is_confident"] else "⚠️"
        
        print(f"\n{confidence_icon} {file_name}")
        print(f"   Category  : {result['category']}")
        print(f"   Confidence: {result['confidence']:3d}% [{confidence_bar}]")
        print(f"   Reason    : {result['reason']}")


def test_project_name_matching():
    """Test project name matching with various queries."""
    print("\n" + "=" * 70)
    print("🗂️  PROJECT NAME MATCHING TESTS")
    print("=" * 70)
    
    projects = ["Tiger", "SchoolSystem", "BPO-Agent", "DataAnalysis", "WebPortal"]
    
    test_queries = [
        # Exact matches
        "Tiger",
        "SchoolSystem",
        
        # Case variations
        "tiger",
        "TIGER",
        "schoolsystem",
        
        # Partial matches
        "tige",
        "tiger project",
        "school",
        "bpo",
        
        # Typos
        "tigerr",
        "tigre",
        "schooll",
        "bpo agent",
        
        # Near misses
        "data",
        "web",
        
        # Bad matches
        "xyz",
        "notaproject",
        "random",
    ]
    
    for query in test_queries:
        result = get_project_match_with_confidence(query, projects)
        confidence_bar = "█" * (result["confidence"] // 10) + "░" * ((100 - result["confidence"]) // 10)
        matched_text = result["matched_project"] if result["matched_project"] else "None"
        confidence_icon = "✅" if result["is_confident"] else ("⚠️" if result["confidence"] > 0 else "❌")
        
        print(f"\n{confidence_icon} Query: '{query}'")
        print(f"   Matched   : {matched_text}")
        print(f"   Confidence: {result['confidence']:3d}% [{confidence_bar}]")
        print(f"   Assessment: {result['reason']}")


def test_matching_thresholds():
    """Test how confidence thresholds affect matching."""
    print("\n" + "=" * 70)
    print("🎯 THRESHOLD SENSITIVITY ANALYSIS")
    print("=" * 70)
    
    projects = ["Tiger", "SchoolSystem", "DataAnalysis"]
    queries = ["tigerr", "schooll", "data"]
    
    thresholds = [50, 70, 75, 90]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        for threshold in thresholds:
            matched, confidence = match_project_name(query, projects, threshold)
            if matched:
                print(f"  Threshold {threshold}: ✅ {matched} ({confidence}%)")
            else:
                print(f"  Threshold {threshold}: ❌ No match (confidence required: {threshold}%)")


if __name__ == "__main__":
    print("\n[TEST] IC AGENT FUZZY MATCHING TEST SUITE\n")
    
    test_file_classification()
    test_project_name_matching()
    test_matching_thresholds()
    
    print("\n" + "=" * 70)
    print("[PASS] Test suite completed!")
    print("=" * 70 + "\n")
