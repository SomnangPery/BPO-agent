#!/usr/bin/env python3
from ic_agent.web import _format_detailed_project_summary, _format_detailed_student_summary

# Test project formatting
print("=" * 80)
print("PROJECT FORMATTING TEST")
print("=" * 80)
result = _format_detailed_project_summary(
    project_name='Photobooth',
    completion=100,
    reports=2,
    score=0,
    recommendation='reject',
    matched_items=[],
    missing_items=[
        'Sub-Objectives Main Tasks Schedule',
        'Define project scope and milestones',
        'Wireframing with Figma',
        'Visual Design and Prototyping',
        'Set up Development Environment'
    ],
    suspicious_signals=[],
    summary='Progress match is 0% and risk level is medium. Multiple critical tasks not addressed in the submitted report.'
)
print(result)

print("\n\n")
print("=" * 80)
print("STUDENT FORMATTING TEST")
print("=" * 80)
# Test student formatting
result2 = _format_detailed_student_summary(
    name='John Smith',
    total=5,
    completed=2,
    pending=3,
    score=45,
    recommendation='review',
    matched_items=['Initial planning', 'Team setup'],
    missing_items=[
        'Implementation of core features',
        'Testing and quality assurance',
        'Documentation with examples'
    ],
    suspicious_signals=['Vague progress descriptions'],
    summary='Some progress shown but critical components are missing evidence of work completion.'
)
print(result2)
