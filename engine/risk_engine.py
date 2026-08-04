"""Small, explainable scoring functions for the educational assessment."""

from data.questions import ASSESSMENT_CATEGORIES, all_questions


def risk_level(score):
    """Translate a security-posture score into an easy-to-understand risk level."""
    if score >= 80:
        return "LOW"
    if score >= 60:
        return "MEDIUM"
    if score >= 40:
        return "HIGH"
    return "CRITICAL"


def build_summary(score, risk, category_scores):
    """Create plain-English dashboard content from transparent assessment results."""
    strengths = [item for item in category_scores if item["score"] >= 75]
    weaknesses = [item for item in category_scores if item["score"] < 60]

    if risk == "LOW":
        headline = "Your core protections are in a strong position."
        detail = (
            "Your answers show good foundational security controls. Continue checking them regularly, "
            "because cyber risks and business systems change over time."
        )
    elif risk == "MEDIUM":
        headline = "Your business has useful protections, with clear gaps to close."
        detail = (
            "Focus on the highest-priority actions first. Improving a few core controls such as MFA, "
            "backups, and patching can materially reduce everyday cyber risk."
        )
    elif risk == "HIGH":
        headline = "Several important cyber protections need attention."
        detail = (
            "Your business may be more exposed to common threats such as phishing, ransomware, and account takeover. "
            "Use the action plan to improve the most important controls as soon as practical."
        )
    else:
        headline = "Your business may be exposed to common cyber threats."
        detail = (
            "Prioritise the critical actions immediately, especially MFA, backups, software updates, and email security. "
            "Consider seeking qualified professional advice for help implementing the changes."
        )

    return {
        "headline": headline,
        "detail": detail,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


def calculate_assessment(raw_answers):
    """Calculate category and overall security scores from Yes/No form answers.

    A "yes" means the stated safeguard is in place. Categories are weighted equally so a
    longer question set in one area cannot dominate the overall educational score.
    """
    normalised_answers = {
        question["id"]: str(raw_answers.get(question["id"], "no")).lower() == "yes"
        for question in all_questions()
    }

    category_scores = []
    for category in ASSESSMENT_CATEGORIES:
        questions = category["questions"]
        protected = sum(normalised_answers[question["id"]] for question in questions)
        score = round((protected / len(questions)) * 100)
        category_scores.append(
            {
                "id": category["id"],
                "name": category["name"],
                "short_name": category["short_name"],
                "icon": category["icon"],
                "score": score,
                "protected": protected,
                "total": len(questions),
            }
        )

    score = round(sum(item["score"] for item in category_scores) / len(category_scores))
    risk = risk_level(score)
    return {
        "score": score,
        "risk": risk,
        "answers": normalised_answers,
        "category_scores": category_scores,
        "total_questions": len(all_questions()),
        "summary": build_summary(score, risk, category_scores),
    }
