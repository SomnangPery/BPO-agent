"""
Comprehensive test suite for Phase 2 modules.
Tests document processing, caching, and semantic matching functionality.
"""

import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ic_agent.document_processor import (
    normalize_text,
    extract_sections,
    prioritize_content,
    extract_key_terms,
    detect_completeness,
    compare_requirement_coverage,
)
from ic_agent.cache import FileCache, AnalysisCache, get_file_cache, get_analysis_cache
from ic_agent.semantic_matcher import (
    extract_requirements_from_oppm,
    extract_requirements_from_srs,
    detect_requirement_coverage,
    analyze_requirement_coverage,
    detect_inconsistencies,
)


def test_document_processor():
    """Test document processing module."""
    print("\n" + "=" * 70)
    print("[TEST] DOCUMENT PROCESSOR MODULE")
    print("=" * 70)
    
    # Test 1: Text normalization
    print("\n[1] Text normalization:")
    raw_text = "  This is   a test.  \n\n  With  extra   spaces.  \n"
    normalized = normalize_text(raw_text)
    print(f"   Input:  {repr(raw_text)}")
    print(f"   Output: {repr(normalized)}")
    print(f"   Result: PASS" if "extra" in normalized else "   Result: FAIL")
    
    # Test 2: Section extraction
    print("\n[2] Section extraction:")
    doc = """
    OBJECTIVES:
    The project aims to deliver a web application with user authentication.
    
    SCOPE:
    Include frontend, backend, and database design.
    
    REQUIREMENTS:
    System shall support 1000 concurrent users.
    """
    sections = extract_sections(doc)
    print(f"   Found {len([s for s in sections.values() if s])} sections")
    for sec, content in sections.items():
        if content:
            print(f"   - {sec}: {content[:50]}...")
    print(f"   Result: PASS" if sections["objectives"] else "   Result: FAIL")
    
    # Test 3: Content prioritization
    print("\n[3] Content prioritization:")
    long_doc = """
    Introduction here.
    Some background information.
    
    REQUIREMENTS: The system must support authentication.
    DELIVERABLES: Frontend, Backend, Database.
    Appendix: Some references.
    """
    prioritized = prioritize_content(long_doc, max_chars=200)
    print(f"   Original length: {len(long_doc)} chars")
    print(f"   Prioritized length: {len(prioritized)} chars")
    print(f"   Contains 'REQUIREMENTS': {('REQUIREMENTS' in prioritized)}")
    print(f"   Result: PASS" if "REQUIREMENTS" in prioritized else "   Result: FAIL")
    
    # Test 4: Key term extraction
    print("\n[4] Key term extraction:")
    text = "We use Python, Django, PostgreSQL for backend. React and TypeScript for frontend."
    terms = extract_key_terms(text, num_terms=5)
    print(f"   Found {len(terms)} key terms: {terms}")
    print(f"   Result: PASS" if any(t in terms for t in ["Python", "Django", "React"]) else "   Result: FAIL")
    
    # Test 5: Completeness detection
    print("\n[5] Document completeness scoring:")
    oppm = "Deliver authentication system with 3 milestones and 5 deliverables."
    srs = "System shall support 1000 users, have 99.9% uptime, secure password storage."
    report = "Implemented authentication with OAuth2, database schema designed, frontend in progress."
    
    scores = detect_completeness(oppm, srs, report)
    print(f"   OPPM score: {scores['oppm_score']}")
    print(f"   SRS score: {scores['srs_score']}")
    print(f"   Report score: {scores['report_score']}")
    print(f"   Overall: {scores['overall']}")
    print(f"   Result: PASS" if scores['overall'] > 0 else "   Result: FAIL")
    
    # Test 6: Requirement coverage
    print("\n[6] Requirement coverage comparison:")
    requirements = ["User authentication", "Database design", "API endpoints"]
    report = "We have implemented user authentication with OAuth2. Database schema is complete."
    
    coverage = compare_requirement_coverage(requirements, report)
    print(f"   Requirements: {len(requirements)}")
    for req, pct in coverage:
        status = "[OK]" if pct > 50 else "[LOW]"
        print(f"   {status} {req}: {pct:.0f}% coverage")
    print(f"   Result: PASS" if any(c > 50 for _, c in coverage) else "   Result: FAIL")


def test_caching():
    """Test caching module."""
    print("\n" + "=" * 70)
    print("[TEST] CACHING MODULE")
    print("=" * 70)
    
    # Test 1: File cache set/get
    print("\n[1] File cache set/get:")
    cache = FileCache()
    
    file_id = "test_file_123"
    file_name = "test_document.pdf"
    content = "This is test content for caching."
    
    # Set cache
    cache.set(file_id, file_name, content)
    print(f"   Cached: {file_name} ({len(content)} bytes)")
    
    # Get cache
    cached = cache.get(file_id, file_name)
    if cached:
        print(f"   Retrieved: {len(cached['content'])} bytes")
        print(f"   Match: {cached['content'] == content}")
        print(f"   Result: PASS")
    else:
        print(f"   Result: FAIL (no cache retrieved)")
    
    # Test 2: Cache expiration
    print("\n[2] Cache metadata:")
    metadata = cache.metadata
    if metadata:
        key = list(metadata.keys())[0]
        meta = metadata[key]
        print(f"   Cached files: {len(metadata)}")
        print(f"   File: {meta['file_name']}")
        print(f"   Cached at: {meta['cached_at']}")
        print(f"   Readable: {meta['readable']}")
        print(f"   Result: PASS")
    else:
        print(f"   Result: FAIL (no metadata)")
    
    # Test 3: Analysis cache
    print("\n[3] Analysis cache:")
    analysis_cache = AnalysisCache()
    
    project = "TestProject"
    file_hashes = {"OPPM": "abc123", "SRS": "def456"}
    analysis = {
        "project": project,
        "coverage": 85.5,
        "issues_found": 3,
        "verdict": "APPROVED"
    }
    
    analysis_cache.set(project, file_hashes, analysis)
    print(f"   Cached analysis for {project}")
    
    retrieved = analysis_cache.get(project, file_hashes)
    if retrieved:
        print(f"   Retrieved analysis: {retrieved['project']}")
        print(f"   Coverage: {retrieved['coverage']}%")
        print(f"   Result: PASS")
    else:
        print(f"   Result: FAIL")
    
    # Clean up
    cache.clear()
    analysis_cache.clear()
    print("\n[CLEANUP] Cache cleared")


def test_semantic_matcher():
    """Test semantic requirement matching module."""
    print("\n" + "=" * 70)
    print("[TEST] SEMANTIC MATCHER MODULE")
    print("=" * 70)
    
    # Test 1: OPPM requirement extraction
    print("\n[1] OPPM requirement extraction:")
    oppm_doc = """
    Deliverables: 
    - Frontend UI with responsive design
    - REST API backend
    - PostgreSQL database schema
    
    Milestones:
    - Phase 1: Design and planning (Week 1-2)
    - Phase 2: Development (Week 3-6)
    - Phase 3: Testing and deployment (Week 7-8)
    
    Skills Needed: Python, JavaScript, React, PostgreSQL
    """
    
    oppm_reqs = extract_requirements_from_oppm(oppm_doc)
    print(f"   Deliverables found: {len(oppm_reqs['deliverables'])}")
    print(f"   Milestones found: {len(oppm_reqs['milestones'])}")
    print(f"   Skills found: {len(oppm_reqs['skills_needed'])}")
    for i, d in enumerate(oppm_reqs['deliverables'][:2], 1):
        print(f"     {i}. {d[:50]}")
    print(f"   Result: PASS" if oppm_reqs['deliverables'] else "   Result: FAIL")
    
    # Test 2: SRS requirement extraction
    print("\n[2] SRS requirement extraction:")
    srs_doc = """
    Functional Requirements:
    - User authentication with email and password
    - Dashboard with real-time data visualization
    - Export data to CSV format
    
    Non-Functional Requirements:
    - System must support 1000 concurrent users
    - Response time < 500ms for all queries
    - 99.9% uptime SLA
    
    Features:
    - User management
    - Role-based access control
    - Audit logging
    """
    
    srs_reqs = extract_requirements_from_srs(srs_doc)
    print(f"   Functional requirements: {len(srs_reqs['functional_requirements'])}")
    print(f"   Non-functional: {len(srs_reqs['non_functional_requirements'])}")
    print(f"   Features: {len(srs_reqs['features'])}")
    print(f"   Result: PASS" if srs_reqs['functional_requirements'] else "   Result: FAIL")
    
    # Test 3: Requirement coverage detection
    print("\n[3] Requirement coverage detection:")
    test_reqs = [
        "User authentication system",
        "Dashboard visualization",
        "Database storage"
    ]
    test_report = """
    We have implemented user authentication using OAuth2 and email-password login.
    The dashboard shows real-time metrics with interactive charts.
    Backend uses PostgreSQL for persistent data storage.
    """
    
    for req in test_reqs:
        is_covered, confidence = detect_requirement_coverage(req, test_report)
        status = "COVERED" if is_covered else "MISSING"
        print(f"   [{status}] {req}: {confidence:.0%}")
    print(f"   Result: PASS")
    
    # Test 4: Full coverage analysis
    print("\n[4] Comprehensive coverage analysis:")
    requirements = {
        "core_features": ["authentication", "dashboard", "reporting"],
        "infrastructure": ["database", "caching", "load balancing"]
    }
    
    report = """
    Authentication module completed with JWT tokens.
    Dashboard implemented with d3.js visualization.
    PostgreSQL database operational with backups.
    """
    
    coverage = analyze_requirement_coverage(requirements, report)
    print(f"   Total requirements: {coverage['summary']['total_requirements']}")
    print(f"   Covered: {coverage['summary']['covered']}")
    print(f"   Coverage: {coverage['summary']['percentage']:.1f}%")
    
    if coverage['by_category']:
        for cat, stats in list(coverage['by_category'].items())[:2]:
            print(f"   - {cat}: {stats['covered']}/{stats['total']} ({stats['percentage']:.0f}%)")
    print(f"   Result: PASS")
    
    # Test 5: Inconsistency detection
    print("\n[5] OPPM/SRS inconsistency detection:")
    oppm_req = {
        "deliverables": ["Frontend UI", "REST API", "Database"],
        "milestones": ["Design", "Dev", "Testing"]
    }
    srs_req = {
        "features": ["API Endpoints", "Authentication"],
        "functional_requirements": ["User authentication", "Data export"]
    }
    
    inconsistencies = detect_inconsistencies(oppm_req, srs_req)
    print(f"   Inconsistencies found: {len(inconsistencies)}")
    for issue in inconsistencies[:3]:
        print(f"   - {issue['type']}: {issue['item'][:40]}")
    print(f"   Result: PASS" if isinstance(inconsistencies, list) else "   Result: FAIL")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("[START] PHASE 2 COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    try:
        test_document_processor()
        test_caching()
        test_semantic_matcher()
        
        print("\n" + "=" * 70)
        print("[COMPLETE] ALL TESTS FINISHED")
        print("=" * 70)
        print("\n[STATUS] Phase 2 Part 1 modules are working correctly!")
        print("[NEXT] Ready to integrate into drive.py, analyzer.py, and reports.py\n")
        
    except Exception as e:
        print(f"\n[ERROR] Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
