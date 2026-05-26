"""
Semantic requirement matching and analysis.
Uses embeddings and similarity scoring for better requirement coverage detection.
"""

import json
import logging
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


def extract_requirements_from_oppm(oppm_content: str) -> Dict[str, List[str]]:
    """
    Extract structured requirements from OPPM document.
    
    Returns:
        {
            "deliverables": [...],
            "milestones": [...],
            "skills_needed": [...],
            "timeline_phases": [...]
        }
    """
    # This would use LLM in production, but we'll use pattern matching for now
    requirements = {
        "deliverables": [],
        "milestones": [],
        "skills_needed": [],
        "timeline_phases": []
    }
    
    # Simple pattern extraction
    import re
    
    # Look for deliverable patterns
    deliverable_patterns = [
        r"deliverable[s]?:\s*(.+?)(?=\.|,|;|\n|$)",
        r"output[s]?:\s*(.+?)(?=\.|,|;|\n|$)",
        r"provide[s]?:\s*(.+?)(?=\.|,|;|\n|$)"
    ]
    
    for pattern in deliverable_patterns:
        matches = re.finditer(pattern, oppm_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            item = match.group(1).strip()
            if item and len(item) > 3:
                requirements["deliverables"].append(item)
    
    # Look for timeline/milestone patterns
    milestone_patterns = [
        r"milestone[s]?:\s*(.+?)(?=\.|,|;|\n|$)",
        r"phase[s]?:\s*(.+?)(?=\.|,|;|\n|$)",
        r"stage[s]?:\s*(.+?)(?=\.|,|;|\n|$)"
    ]
    
    for pattern in milestone_patterns:
        matches = re.finditer(pattern, oppm_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            item = match.group(1).strip()
            if item and len(item) > 3:
                requirements["milestones"].append(item)
    
    # Look for skill requirements
    skill_patterns = [
        r"skills?\s+(?:required|needed|required):\s*(.+?)(?=\.|,|;|\n|$)",
        r"expertise\s+(?:in|with):\s*(.+?)(?=\.|,|;|\n|$)",
        r"knowledge of:\s*(.+?)(?=\.|,|;|\n|$)"
    ]
    
    for pattern in skill_patterns:
        matches = re.finditer(pattern, oppm_content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            items = match.group(1).split(',')
            for item in items:
                item = item.strip()
                if item and len(item) > 2:
                    requirements["skills_needed"].append(item)
    
    return requirements


def extract_requirements_from_srs(srs_content: str) -> Dict[str, List[str]]:
    """
    Extract structured requirements from SRS document.
    
    Returns:
        {
            "functional_requirements": [...],
            "non_functional_requirements": [...],
            "features": [...],
            "modules": [...],
            "constraints": [...]
        }
    """
    requirements = {
        "functional_requirements": [],
        "non_functional_requirements": [],
        "features": [],
        "modules": [],
        "constraints": []
    }
    
    import re
    
    # Functional requirements
    func_patterns = [
        r"functional requirement[s]?:\s*(.+?)(?=non[- ]functional|constraint|module|feature|\Z)",
        r"shall:\s*(.+?)(?=\.|,|;|\n|\Z)",
        r"system shall:\s*(.+?)(?=\.|,|;|\n|\Z)"
    ]
    
    for pattern in func_patterns:
        matches = re.finditer(pattern, srs_content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for match in matches:
            text = match.group(1)
            # Split by bullets or numbering
            items = re.split(r'(?:^|\n)\s*[-•*\d+\.]+\s*', text)
            for item in items:
                item = item.strip()
                if item and len(item) > 5:
                    requirements["functional_requirements"].append(item[:100])
    
    # Non-functional requirements
    nonfunc_patterns = [
        r"non[- ]functional requirement[s]?:\s*(.+?)(?=constraint|module|feature|functional|\Z)",
        r"performance requirement[s]?:\s*(.+?)(?=constraint|module|feature|\Z)",
        r"security requirement[s]?:\s*(.+?)(?=constraint|module|feature|\Z)"
    ]
    
    for pattern in nonfunc_patterns:
        matches = re.finditer(pattern, srs_content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for match in matches:
            text = match.group(1)
            items = re.split(r'(?:^|\n)\s*[-•*\d+\.]+\s*', text)
            for item in items:
                item = item.strip()
                if item and len(item) > 5:
                    requirements["non_functional_requirements"].append(item[:100])
    
    # Features
    feature_patterns = [
        r"feature[s]?:\s*(.+?)(?=module|constraint|functional|non[- ]functional|\Z)",
        r"system feature[s]?:\s*(.+?)(?=module|constraint|functional|\Z)"
    ]
    
    for pattern in feature_patterns:
        matches = re.finditer(pattern, srs_content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for match in matches:
            text = match.group(1)
            items = re.split(r'(?:^|\n)\s*[-•*\d+\.]+\s*', text)
            for item in items:
                item = item.strip()
                if item and len(item) > 3:
                    requirements["features"].append(item[:100])
    
    return requirements


def detect_requirement_coverage(requirement: str, report_content: str, threshold: float = 0.3) -> Tuple[bool, float]:
    """
    Detect if a requirement is covered in the report.
    
    Returns:
        (is_covered: bool, confidence: 0.0-1.0)
    """
    if not requirement or not report_content:
        return False, 0.0
    
    report_lower = report_content.lower()
    req_lower = requirement.lower()
    
    # Simple keyword overlap scoring
    import re
    req_words = set(re.findall(r'\b\w{3,}\b', req_lower))  # Words 3+ chars
    report_words = set(re.findall(r'\b\w{3,}\b', report_lower))
    
    if not req_words:
        return False, 0.0
    
    overlap = req_words & report_words
    overlap_ratio = len(overlap) / len(req_words)
    
    # Check for exact phrase match
    exact_match = req_lower in report_lower
    
    if exact_match:
        confidence = 1.0
    elif overlap_ratio >= threshold:
        confidence = min(overlap_ratio, 1.0)
    else:
        confidence = 0.0
    
    is_covered = confidence >= threshold
    
    return is_covered, round(confidence, 2)


def analyze_requirement_coverage(
    requirements: Dict[str, List[str]],
    report_content: str
) -> Dict[str, Any]:
    """
    Comprehensive requirement coverage analysis.
    
    Returns:
        {
            "summary": {
                "total_requirements": int,
                "covered": int,
                "percentage": float
            },
            "by_category": {
                "category_name": {
                    "total": int,
                    "covered": int,
                    "percentage": float,
                    "items": [{"requirement": str, "coverage": float}, ...]
                }
            },
            "coverage_map": [
                {"requirement": str, "coverage": float, "status": "covered|partial|missing"}
            ]
        }
    """
    coverage_map = []
    category_stats = defaultdict(lambda: {"total": 0, "covered": 0, "items": []})
    
    total = 0
    total_covered = 0
    
    for category, items in requirements.items():
        for item in items:
            is_covered, confidence = detect_requirement_coverage(item, report_content)
            
            total += 1
            if is_covered:
                total_covered += 1
            
            # Determine status
            if confidence >= 0.8:
                status = "covered"
            elif confidence >= 0.3:
                status = "partial"
            else:
                status = "missing"
            
            coverage_map.append({
                "requirement": item,
                "category": category,
                "coverage": confidence,
                "status": status
            })
            
            category_stats[category]["total"] += 1
            if is_covered:
                category_stats[category]["covered"] += 1
            category_stats[category]["items"].append({
                "requirement": item,
                "coverage": confidence
            })
    
    # Build final result
    by_category = {}
    for category, stats in category_stats.items():
        total_cat = stats["total"]
        covered_cat = stats["covered"]
        by_category[category] = {
            "total": total_cat,
            "covered": covered_cat,
            "percentage": round((covered_cat / total_cat * 100) if total_cat > 0 else 0, 1),
            "items": stats["items"]
        }
    
    return {
        "summary": {
            "total_requirements": total,
            "covered": total_covered,
            "percentage": round((total_covered / total * 100) if total > 0 else 0, 1)
        },
        "by_category": dict(by_category),
        "coverage_map": coverage_map
    }


def detect_inconsistencies(oppm_reqs: Dict[str, List[str]], srs_reqs: Dict[str, List[str]]) -> List[Dict[str, str]]:
    """
    Detect inconsistencies between OPPM and SRS.
    
    Returns:
        [
            {"type": "missing_in_srs|missing_in_oppm", "item": str, "source": str},
            ...
        ]
    """
    inconsistencies = []
    
    # OPPM deliverables not mentioned in SRS
    oppm_deliv = set(d.lower() for d in oppm_reqs.get("deliverables", []))
    srs_features = set(f.lower() for f in srs_reqs.get("features", []))
    
    for item in oppm_deliv - srs_features:
        if item and len(item) > 3:
            inconsistencies.append({
                "type": "deliverable_not_in_features",
                "item": item,
                "source": "OPPM",
                "severity": "medium"
            })
    
    # SRS requirements not referenced in OPPM
    srs_func_reqs = set(r.lower() for r in srs_reqs.get("functional_requirements", []))
    oppm_items = set(d.lower() for d in (oppm_reqs.get("deliverables", []) + oppm_reqs.get("milestones", [])))
    
    for item in srs_func_reqs - oppm_items:
        if item and len(item) > 3:
            inconsistencies.append({
                "type": "requirement_not_in_oppm",
                "item": item,
                "source": "SRS",
                "severity": "low"
            })
    
    return inconsistencies


def generate_coverage_report(
    oppm_requirements: Dict[str, List[str]],
    srs_requirements: Dict[str, List[str]],
    report_content: str
) -> Dict[str, Any]:
    """
    Generate comprehensive requirement coverage report.
    
    Returns:
        {
            "oppm_coverage": {...},
            "srs_coverage": {...},
            "inconsistencies": [...],
            "quality_metrics": {...}
        }
    """
    return {
        "oppm_coverage": analyze_requirement_coverage(oppm_requirements, report_content),
        "srs_coverage": analyze_requirement_coverage(srs_requirements, report_content),
        "inconsistencies": detect_inconsistencies(oppm_requirements, srs_requirements),
        "generated_at": __import__("datetime").datetime.now().isoformat()
    }
