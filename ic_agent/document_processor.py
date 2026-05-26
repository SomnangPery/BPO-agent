"""
Document text normalization and processing utilities.
Handles text cleanup, semantic prioritization, and section extraction.
"""

import re
import logging
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


def normalize_text(text: str, preserve_structure: bool = False) -> str:
    """
    Normalize document text for analysis.
    
    Args:
        text: Raw text from document
        preserve_structure: If True, keep line breaks; else collapse to single text
        
    Returns:
        Normalized text ready for semantic analysis
    """
    if not text:
        return ""
    
    # Remove extra whitespace (but preserve paragraphs if requested)
    if preserve_structure:
        # Keep paragraph breaks, normalize internal whitespace
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines
        text = '\n'.join(lines)
    else:
        # Collapse everything to single line
        text = ' '.join(text.split())
    
    # Remove common artifacts
    text = re.sub(r'\x00', '', text)  # Null characters
    text = re.sub(r'[\r\f]', '', text)  # Form feeds
    
    return text


def extract_sections(text: str) -> Dict[str, str]:
    """
    Extract common document sections by keyword detection.
    
    Returns:
        {
            "objectives": "...",
            "scope": "...",
            "requirements": "...",
            "deliverables": "...",
            "timeline": "...",
            "other": "... rest of text ..."
        }
    """
    normalized = normalize_text(text, preserve_structure=True)
    sections = {
        "objectives": "",
        "scope": "",
        "requirements": "",
        "deliverables": "",
        "timeline": "",
        "constraints": "",
        "assumptions": "",
        "other": ""
    }
    
    # Define section patterns
    section_patterns = {
        "objectives": r"(?:objectives?|goals?|purpose|intended outcomes?):?\s+(.+?)(?=(?:scope|requirements|deliverables|timeline|constraints|assumptions|[A-Z][a-z]+:|\Z))",
        "scope": r"(?:scope|project scope):?\s+(.+?)(?=(?:objectives|requirements|deliverables|timeline|constraints|assumptions|[A-Z][a-z]+:|\Z))",
        "requirements": r"(?:requirements|functional requirements|non[- ]functional requirements|system requirements):?\s+(.+?)(?=(?:objectives|scope|deliverables|timeline|constraints|assumptions|[A-Z][a-z]+:|\Z))",
        "deliverables": r"(?:deliverables?|outputs?|outcomes?):?\s+(.+?)(?=(?:objectives|scope|requirements|timeline|constraints|assumptions|[A-Z][a-z]+:|\Z))",
        "timeline": r"(?:timeline|schedule|milestones?|timeline|duration):?\s+(.+?)(?=(?:objectives|scope|requirements|deliverables|constraints|assumptions|[A-Z][a-z]+:|\Z))",
        "constraints": r"(?:constraints?|limitations?|risks?):?\s+(.+?)(?=(?:objectives|scope|requirements|deliverables|timeline|assumptions|[A-Z][a-z]+:|\Z))",
        "assumptions": r"(?:assumptions?|prerequisites?):?\s+(.+?)(?=(?:objectives|scope|requirements|deliverables|timeline|constraints|[A-Z][a-z]+:|\Z))",
    }
    
    for section_name, pattern in section_patterns.items():
        match = re.search(pattern, normalized, re.IGNORECASE | re.DOTALL)
        if match:
            content = match.group(1).strip()
            sections[section_name] = content[:500]  # Limit to 500 chars per section
    
    # Remaining text goes to "other"
    used_text = ''.join(sections.values())
    if len(normalized) > len(used_text):
        sections["other"] = normalized[len(used_text):].strip()[:1000]
    
    return sections


def prioritize_content(text: str, max_chars: int = 5000) -> str:
    """
    Prioritize semantic content by importance.
    Returns most relevant content up to max_chars.
    
    Priority:
    1. First 20% (intro/summary)
    2. Sections with keywords (requirements, deliverables, objectives)
    3. Mid-document content
    4. Appendices/references (deprioritized)
    """
    if not text:
        return ""
    
    normalized = normalize_text(text, preserve_structure=True)
    
    if len(normalized) <= max_chars:
        return normalized
    
    lines = normalized.split('\n')
    total_lines = len(lines)
    
    # Keyword importance scores
    keyword_importance = {
        "requirement": 10,
        "deliverable": 10,
        "objective": 9,
        "scope": 8,
        "milestone": 8,
        "feature": 7,
        "constraint": 7,
        "timeline": 6,
        "risk": 6,
        "assumption": 5,
        "appendix": 0,
        "reference": 0,
        "footnote": 0,
    }
    
    # Score each line
    scored_lines = []
    for i, line in enumerate(lines):
        # Priority boost for early lines (intro section)
        position_score = max(0, 10 - (i / total_lines * 10))
        
        # Score based on keywords
        keyword_score = 0
        for keyword, score in keyword_importance.items():
            if keyword.lower() in line.lower():
                keyword_score = max(keyword_score, score)
        
        total_score = position_score + keyword_score
        scored_lines.append((total_score, line))
    
    # Sort by importance but preserve some order
    # Keep first 10% + highest scored middle content
    first_chunk = int(total_lines * 0.1)
    important_lines = [(0, lines[i]) for i in range(first_chunk)]  # Keep first 10%
    important_lines.extend(sorted(scored_lines[first_chunk:], key=lambda x: -x[0]))
    
    # Build result up to max_chars
    result = []
    char_count = 0
    for _, line in important_lines:
        if char_count + len(line) > max_chars:
            break
        result.append(line)
        char_count += len(line) + 1  # +1 for newline
    
    return '\n'.join(result)


def extract_key_terms(text: str, num_terms: int = 20) -> List[str]:
    """
    Extract key terms/concepts from document.
    Uses capitalization and frequency heuristics.
    """
    if not text:
        return []
    
    # Extract capitalized phrases (likely important terms)
    # Looking for 1-4 word phrases that start with capitals
    pattern = r'\b[A-Z][a-z]*(?:\s+[A-Z][a-z]*){0,3}\b'
    candidates = re.findall(pattern, text)
    
    # Filter out common words
    common_words = {'The', 'And', 'For', 'With', 'This', 'That', 'Which', 'From', 'To', 'In', 'On', 'At', 'By', 'As'}
    candidates = [c for c in candidates if c not in common_words and len(c) > 2]
    
    # Count frequency
    from collections import Counter
    freq = Counter(candidates)
    
    # Return top terms
    return [term for term, _ in freq.most_common(num_terms)]


def detect_completeness(oppm_content: str, srs_content: str, report_content: str) -> Dict[str, float]:
    """
    Assess document completeness based on content quality.
    
    Returns:
        {
            "oppm_score": 0.0-1.0,
            "srs_score": 0.0-1.0,
            "report_score": 0.0-1.0,
            "overall": 0.0-1.0
        }
    """
    def content_score(text: str) -> float:
        """Score content from 0-1 based on size and richness."""
        if not text:
            return 0.0
        
        text = normalize_text(text)
        
        # Size factor (up to 2000 chars = 0.4)
        size_score = min(len(text) / 5000, 0.4)
        
        # Complexity factor (number of unique words, sentences, etc.)
        words = len(text.split())
        sentences = len(re.split(r'[.!?]', text))
        variety = len(set(w.lower() for w in text.split())) / max(words, 1)
        
        complexity_score = min((words / 500) * 0.3, 0.3) + (variety * 0.3)
        
        return min(size_score + complexity_score, 1.0)
    
    oppm_score = content_score(oppm_content)
    srs_score = content_score(srs_content)
    report_score = content_score(report_content)
    
    return {
        "oppm_score": round(oppm_score, 2),
        "srs_score": round(srs_score, 2),
        "report_score": round(report_score, 2),
        "overall": round((oppm_score + srs_score + report_score) / 3, 2)
    }


def compare_requirement_coverage(requirements: List[str], report_content: str) -> List[Tuple[str, float]]:
    """
    For each requirement, estimate coverage percentage based on report content.
    Uses simple keyword matching with fuzzy tolerance.
    
    Returns:
        [(requirement, coverage_percent), ...]
    """
    if not report_content:
        return [(req, 0.0) for req in requirements]
    
    report_lower = normalize_text(report_content).lower()
    results = []
    
    for requirement in requirements:
        req_lower = normalize_text(requirement).lower()
        
        # Extract key phrases from requirement (2-3 word chunks)
        key_phrases = re.findall(r'\b\w+\s+\w+(?:\s+\w+)?\b', req_lower)
        
        if not key_phrases:
            # Fall back to single word matching
            key_phrases = re.findall(r'\b\w{3,}\b', req_lower)
        
        # Check coverage
        covered_phrases = sum(1 for phrase in key_phrases if phrase in report_lower)
        coverage = (covered_phrases / len(key_phrases)) * 100 if key_phrases else 0.0
        
        results.append((requirement, round(coverage, 1)))
    
    return results
