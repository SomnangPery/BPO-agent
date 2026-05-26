"""
Fuzzy matching utilities for file classification and project name resolution.
Supports typo-tolerant matching, case-insensitive keywords, and similarity scoring.
"""

import logging
from typing import Optional, Tuple
from fuzzywuzzy import fuzz
from fuzzywuzzy import process as fuzzy_process

logger = logging.getLogger(__name__)

# Keyword patterns for file type identification
OPPM_KEYWORDS = [
    "oppm",
    "project charter",
    "one page project manager",
    "project overview",
    "charter",
    "project plan"
]

SRS_KEYWORDS = [
    "srs",
    "software requirement",
    "software requirements specification",
    "system requirements",
    "requirements specification",
    "functional requirement",
    "non-functional requirement"
]

REPORT_KEYWORDS = [
    "report",
    "final report",
    "project report",
    "implementation report",
    "progress report",
    "status report",
    "submission"
]


def normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip whitespace."""
    return text.strip().lower()


def classify_file_by_name(
    file_name: str,
    threshold: int = 75
) -> Tuple[Optional[str], int]:
    """
    Classify a file as OPPM, SRS, or Report based on fuzzy matching.
    
    Args:
        file_name: Name of the file (with or without extension)
        threshold: Minimum similarity score (0-100) to match
        
    Returns:
        Tuple of (category, confidence_score) where category is one of:
        - "oppm"
        - "srs"
        - "report"
        - None if no match found
    """
    normalized = normalize_text(file_name)
    
    # Remove common extensions for cleaner matching
    for ext in [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".xls"]:
        if normalized.endswith(ext):
            normalized = normalized[:-len(ext)]
    
    # Replace underscores and dashes with spaces for better word matching
    normalized = normalized.replace("_", " ").replace("-", " ")
    
    # Check OPPM matches
    oppm_matches = fuzzy_process.extract(
        normalized, OPPM_KEYWORDS, scorer=fuzz.token_set_ratio, limit=1
    )
    if oppm_matches and oppm_matches[0][1] >= threshold:
        return "oppm", oppm_matches[0][1]
    
    # Check SRS matches
    srs_matches = fuzzy_process.extract(
        normalized, SRS_KEYWORDS, scorer=fuzz.token_set_ratio, limit=1
    )
    if srs_matches and srs_matches[0][1] >= threshold:
        return "srs", srs_matches[0][1]
    
    # Check Report matches
    report_matches = fuzzy_process.extract(
        normalized, REPORT_KEYWORDS, scorer=fuzz.token_set_ratio, limit=1
    )
    if report_matches and report_matches[0][1] >= threshold:
        return "report", report_matches[0][1]
    
    # If no category matched, it's a report by default (uncategorized submission)
    return "report", 0


def match_project_name(
    query: str,
    project_names: list[str],
    threshold: int = 75
) -> Tuple[Optional[str], int]:
    """
    Find best matching project name using fuzzy matching.
    
    Args:
        query: User query or partial project name
        project_names: List of available project names
        threshold: Minimum similarity score (0-100) to match
        
    Returns:
        Tuple of (best_match_name, confidence_score) or (None, 0) if no match
    """
    if not project_names:
        return None, 0
    
    normalized_query = normalize_text(query)
    
    # Use token_set_ratio for better partial matching
    matches = fuzzy_process.extract(
        normalized_query,
        project_names,
        scorer=fuzz.token_set_ratio,
        limit=1
    )
    
    if matches and matches[0][1] >= threshold:
        return matches[0][0], matches[0][1]
    
    return None, 0


def find_best_project_match(
    query: str,
    projects: list[dict],
    threshold: int = 75
) -> Tuple[Optional[dict], int]:
    """
    Find the best matching project from a list of project dicts.
    
    Args:
        query: User query or partial project name
        projects: List of project dicts with 'project_name' key
        threshold: Minimum similarity score (0-100) to match
        
    Returns:
        Tuple of (best_match_project_dict, confidence_score) or (None, 0)
    """
    if not projects:
        return None, 0
    
    project_names = [p["project_name"] for p in projects]
    best_name, score = match_project_name(query, project_names, threshold)
    
    if best_name:
        project = next(p for p in projects if p["project_name"] == best_name)
        return project, score
    
    return None, 0


def get_file_category_with_confidence(file_name: str) -> dict:
    """
    Get detailed file classification with confidence information.
    
    Returns:
        {
            "file_name": str,
            "category": str ("oppm", "srs", "report", or None),
            "confidence": int (0-100),
            "is_confident": bool (True if confidence >= 75),
            "reason": str
        }
    """
    category, confidence = classify_file_by_name(file_name)
    
    reasons = {
        "oppm": "Matches OPPM document patterns",
        "srs": "Matches SRS/Requirements document patterns",
        "report": "Matches project report patterns"
    }
    
    return {
        "file_name": file_name,
        "category": category,
        "confidence": confidence,
        "is_confident": confidence >= 75,
        "reason": reasons.get(category, "Categorized as report by default")
    }


def get_project_match_with_confidence(query: str, project_names: list[str]) -> dict:
    """
    Get detailed project name matching with confidence information.
    
    Returns:
        {
            "query": str,
            "matched_project": str or None,
            "confidence": int (0-100),
            "is_confident": bool (True if confidence >= 75),
            "reason": str
        }
    """
    matched, confidence = match_project_name(query, project_names)
    
    if confidence >= 90:
        reason = "Exact or near-exact match"
    elif confidence >= 75:
        reason = "Good match with minor differences"
    elif confidence >= 50:
        reason = "Partial match - may need clarification"
    else:
        reason = "No confident match found"
    
    return {
        "query": query,
        "matched_project": matched,
        "confidence": confidence,
        "is_confident": confidence >= 75,
        "reason": reason
    }
