"""
Sample Marking Schemes for Testing

Provides 3-5 test marking schemes of varying complexity
for use in unit and integration tests.
"""

import json
from datetime import datetime
from decimal import Decimal


# Simple rubric: 2 criteria, 4 levels each
SIMPLE_SCHEME_JSON = {
    "version": "1.0.0",
    "metadata": {
        "name": "Simple Essay Rubric",
        "description": "Basic essay grading rubric for primary school students",
        "exported_at": datetime.now().isoformat(),
        "exported_by": "teacher@example.com"
    },
    "criteria": [
        {
            "id": "c1-organization",
            "name": "Organization",
            "description": "Structure and flow of the essay",
            "weight": 0.5,
            "point_value": 20,
            "descriptors": [
                {
                    "level": "excellent",
                    "description": "Essay has clear introduction, body, and conclusion with logical flow",
                    "points": 20
                },
                {
                    "level": "good",
                    "description": "Essay has most required sections with mostly logical flow",
                    "points": 15
                },
                {
                    "level": "satisfactory",
                    "description": "Essay has basic structure but flow is unclear",
                    "points": 10
                },
                {
                    "level": "poor",
                    "description": "Essay structure is unclear or missing sections",
                    "points": 5
                },
                {
                    "level": "fail",
                    "description": "No clear structure",
                    "points": 0
                }
            ]
        },
        {
            "id": "c2-mechanics",
            "name": "Grammar and Mechanics",
            "description": "Spelling, punctuation, and grammar",
            "weight": 0.5,
            "point_value": 20,
            "descriptors": [
                {
                    "level": "excellent",
                    "description": "Virtually no errors in grammar, spelling, or punctuation",
                    "points": 20
                },
                {
                    "level": "good",
                    "description": "Few errors that don't interfere with understanding",
                    "points": 15
                },
                {
                    "level": "satisfactory",
                    "description": "Some errors but most sentences are correct",
                    "points": 10
                },
                {
                    "level": "poor",
                    "description": "Many errors that sometimes interfere with understanding",
                    "points": 5
                },
                {
                    "level": "fail",
                    "description": "Numerous errors that prevent understanding",
                    "points": 0
                }
            ]
        }
    ]
}


# Medium rubric: 4 criteria, 4 levels each (academic paper)
MEDIUM_SCHEME_JSON = {
    "version": "1.0.0",
    "metadata": {
        "name": "Academic Paper Rubric",
        "description": "Comprehensive rubric for university-level research papers",
        "exported_at": datetime.now().isoformat(),
        "exported_by": "professor@example.edu"
    },
    "criteria": [
        {
            "id": "c1-thesis",
            "name": "Thesis Statement",
            "description": "Clarity and strength of main argument",
            "weight": 0.25,
            "point_value": 25,
            "descriptors": [
                {
                    "level": "excellent",
                    "description": "Thesis is clear, specific, and arguable. Guides entire paper.",
                    "points": 25
                },
                {
                    "level": "good",
                    "description": "Thesis is mostly clear but could be more specific",
                    "points": 19
                },
                {
                    "level": "satisfactory",
                    "description": "Thesis is present but somewhat vague or general",
                    "points": 12
                },
                {
                    "level": "poor",
                    "description": "Thesis is unclear or missing",
                    "points": 0
                }
            ]
        },
        {
            "id": "c2-evidence",
            "name": "Evidence and Support",
            "description": "Quality and relevance of sources and examples",
            "weight": 0.25,
            "point_value": 25,
            "descriptors": [
                {
                    "level": "excellent",
                    "description": "Excellent use of diverse, credible sources. Evidence clearly supports claims.",
                    "points": 25
                },
                {
                    "level": "good",
                    "description": "Good use of sources, mostly credible, mostly relevant",
                    "points": 19
                },
                {
                    "level": "satisfactory",
                    "description": "Adequate sources but some are questionable or weak",
                    "points": 12
                },
                {
                    "level": "poor",
                    "description": "Few or no credible sources, weak evidence",
                    "points": 0
                }
            ]
        },
        {
            "id": "c3-analysis",
            "name": "Critical Analysis",
            "description": "Depth of thinking and interpretation",
            "weight": 0.25,
            "point_value": 25,
            "descriptors": [
                {
                    "level": "excellent",
                    "description": "Deep analysis showing original thinking and insight",
                    "points": 25
                },
                {
                    "level": "good",
                    "description": "Good analysis with some original thinking",
                    "points": 19
                },
                {
                    "level": "satisfactory",
                    "description": "Basic analysis but mostly summary",
                    "points": 12
                },
                {
                    "level": "poor",
                    "description": "Little to no analysis, mostly summary or description",
                    "points": 0
                }
            ]
        },
        {
            "id": "c4-mechanics",
            "name": "Writing Quality",
            "description": "Grammar, style, and organization",
            "weight": 0.25,
            "point_value": 25,
            "descriptors": [
                {
                    "level": "excellent",
                    "description": "Polished writing, clear organization, minimal errors",
                    "points": 25
                },
                {
                    "level": "good",
                    "description": "Well-written with good organization, few errors",
                    "points": 19
                },
                {
                    "level": "satisfactory",
                    "description": "Acceptable writing but organization or errors are present",
                    "points": 12
                },
                {
                    "level": "poor",
                    "description": "Poorly written, disorganized, many errors",
                    "points": 0
                }
            ]
        }
    ]
}


# Complex rubric: 6+ criteria, weighted (professional project)
COMPLEX_SCHEME_JSON = {
    "version": "1.0.0",
    "metadata": {
        "name": "Professional Project Evaluation",
        "description": "Comprehensive evaluation rubric for professional software development projects",
        "exported_at": datetime.now().isoformat(),
        "exported_by": "manager@example.com"
    },
    "criteria": [
        {
            "id": "c1-requirements",
            "name": "Requirements Analysis",
            "weight": 0.15,
            "point_value": 15,
            "descriptors": [
                {
                    "level": "excellent",
                    "description": "Complete requirements gathering with stakeholder input and documentation",
                    "points": 15
                },
                {
                    "level": "good",
                    "description": "Good requirements with minor gaps",
                    "points": 12
                },
                {
                    "level": "satisfactory",
                    "description": "Basic requirements but some missing",
                    "points": 8
                },
                {
                    "level": "poor",
                    "description": "Incomplete or unclear requirements",
                    "points": 0
                }
            ]
        },
        {
            "id": "c2-design",
            "name": "System Design",
            "weight": 0.20,
            "point_value": 20,
            "descriptors": [
                {
                    "level": "excellent",
                    "description": "Excellent architecture with scalability and maintainability",
                    "points": 20
                },
                {
                    "level": "good",
                    "description": "Good design with minor improvements needed",
                    "points": 15
                },
                {
                    "level": "satisfactory",
                    "description": "Adequate design but lacks optimization",
                    "points": 10
                },
                {
                    "level": "poor",
                    "description": "Poor design with significant issues",
                    "points": 0
                }
            ]
        },
        {
            "id": "c3-implementation",
            "name": "Code Implementation",
            "weight": 0.20,
            "point_value": 20,
            "descriptors": [
                {
                    "level": "excellent",
                    "description": "Clean, well-documented, follows best practices",
                    "points": 20
                },
                {
                    "level": "good",
                    "description": "Good code quality with minor issues",
                    "points": 15
                },
                {
                    "level": "satisfactory",
                    "description": "Functional but needs refactoring",
                    "points": 10
                },
                {
                    "level": "poor",
                    "description": "Code has significant quality issues",
                    "points": 0
                }
            ]
        },
        {
            "id": "c4-testing",
            "name": "Testing and QA",
            "weight": 0.15,
            "point_value": 15,
            "descriptors": [
                {
                    "level": "excellent",
                    "description": "Comprehensive unit and integration tests with good coverage",
                    "points": 15
                },
                {
                    "level": "good",
                    "description": "Good test coverage with minor gaps",
                    "points": 12
                },
                {
                    "level": "satisfactory",
                    "description": "Some testing but coverage incomplete",
                    "points": 8
                },
                {
                    "level": "poor",
                    "description": "Minimal or no testing",
                    "points": 0
                }
            ]
        },
        {
            "id": "c5-documentation",
            "name": "Documentation",
            "weight": 0.15,
            "point_value": 15,
            "descriptors": [
                {
                    "level": "excellent",
                    "description": "Complete documentation with API specs and user guide",
                    "points": 15
                },
                {
                    "level": "good",
                    "description": "Good documentation with minor gaps",
                    "points": 12
                },
                {
                    "level": "satisfactory",
                    "description": "Basic documentation but incomplete",
                    "points": 8
                },
                {
                    "level": "poor",
                    "description": "Minimal or missing documentation",
                    "points": 0
                }
            ]
        },
        {
            "id": "c6-delivery",
            "name": "Delivery and Timeline",
            "weight": 0.15,
            "point_value": 15,
            "descriptors": [
                {
                    "level": "excellent",
                    "description": "On-time delivery with all features and quality standards met",
                    "points": 15
                },
                {
                    "level": "good",
                    "description": "Minor delays or scope adjustments",
                    "points": 12
                },
                {
                    "level": "satisfactory",
                    "description": "Delivered late or missing non-critical features",
                    "points": 8
                },
                {
                    "level": "poor",
                    "description": "Significant delays or missing critical features",
                    "points": 0
                }
            ]
        }
    ]
}


def get_simple_scheme():
    """Return simple scheme as dict."""
    return SIMPLE_SCHEME_JSON.copy()


def get_medium_scheme():
    """Return medium scheme as dict."""
    return MEDIUM_SCHEME_JSON.copy()


def get_complex_scheme():
    """Return complex scheme as dict."""
    return COMPLEX_SCHEME_JSON.copy()


def get_all_schemes():
    """Return all test schemes."""
    return [
        get_simple_scheme(),
        get_medium_scheme(),
        get_complex_scheme()
    ]
