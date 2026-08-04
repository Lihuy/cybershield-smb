"""Prioritised recommendations generated from unanswered safeguards."""

from data.questions import ASSESSMENT_CATEGORIES

_PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2}
_PRIORITY_ICONS = {
    "Critical": "bi-exclamation-octagon-fill",
    "High": "bi-exclamation-triangle-fill",
    "Medium": "bi-info-circle-fill",
}


def generate_recommendations(answers):
    """Return an ordered, concrete action list for safeguards not yet in place."""
    items = []
    for category in ASSESSMENT_CATEGORIES:
        for question in category["questions"]:
            if not answers.get(question["id"], False):
                priority = question["priority"]
                items.append(
                    {
                        "priority": priority,
                        "priority_icon": _PRIORITY_ICONS[priority],
                        "title": question["question"],
                        "description": question["recommendation"],
                        "category": category["name"],
                        "question_id": question["id"],
                    }
                )
    return sorted(items, key=lambda item: (_PRIORITY_ORDER[item["priority"]], item["category"]))
