"""Scoring for sector questions (CyberShield SMB 2.0, Sprint 2).

The sector score is the percentage of that sector's questions answered Yes. It is reported
next to the core score and is never added to or blended with it, so the core score stays
comparable across attempts and with the validated 20-question instrument.
"""

from data.sectors import FRAMEWORKS, get_sector

_PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2}
_PRIORITY_ICONS = {
    "Critical": "bi-exclamation-octagon-fill",
    "High": "bi-exclamation-triangle-fill",
    "Medium": "bi-info-circle-fill",
}


def describe_sources(question):
    """Sources for one question with the framework's display name filled in."""
    return [
        {
            "framework": FRAMEWORKS[source["framework"]]["short"],
            "ref": source["ref"],
            "note": source["note"],
            "fit": source["fit"],
        }
        for source in question["sources"]
    ]


def calculate_sector(sector_id, raw_answers):
    """Return the separate sector score, per-question results and sector recommendations."""
    sector = get_sector(sector_id)
    if sector is None:
        return None

    answers = {
        question["id"]: str(raw_answers.get(question["id"], "no")).lower() == "yes"
        for question in sector["questions"]
    }
    protected = sum(answers.values())
    total = len(sector["questions"])
    category_label = f"{sector['name']} questions"

    recommendations = [
        {
            "priority": question["priority"],
            "priority_icon": _PRIORITY_ICONS[question["priority"]],
            "title": question["question"],
            "description": question["recommendation"],
            "category": category_label,
            "question_id": question["id"],
            "reason": question["reason"],
            "sector": True,
        }
        for question in sector["questions"]
        if not answers[question["id"]]
    ]
    recommendations.sort(key=lambda item: _PRIORITY_ORDER[item["priority"]])

    return {
        "id": sector["id"],
        "name": sector["name"],
        "icon": sector["icon"],
        "score": round((protected / total) * 100),
        "protected": protected,
        "total": total,
        "answers": answers,
        "questions": [
            {
                "question": question["question"],
                "reason": question["reason"],
                "in_place": answers[question["id"]],
                "sources": describe_sources(question),
            }
            for question in sector["questions"]
        ],
        "recommendations": recommendations,
    }


def sector_history_row(sector_result):
    """Compact row stored beside the core category scores so no schema change is needed."""
    return {
        "id": f"sector:{sector_result['id']}",
        "name": f"{sector_result['name']} questions",
        "short_name": sector_result["name"],
        "icon": sector_result["icon"],
        "score": sector_result["score"],
        "protected": sector_result["protected"],
        "total": sector_result["total"],
        "sector": True,
    }
