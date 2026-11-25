"""Transparent, rule-based business-type classifier (CyberShield SMB 2.0, Sprint 2).

How it works, in full:
1. Each intake answer awards points to one or more of the fixed business types.
2. Confidence is the share of all awarded points held by the leading type.
3. The result is "clear" only if the leading type has enough points, a large enough
   share, and no tie. Otherwise it is "close" and the owner is asked to choose.
4. An optional free-text description is read into one of the fixed type labels by a
   language model (or an offline keyword match). That label awards no points. It is shown
   next to the result as a cross-check that either agrees or differs. Only when the
   answers give no points at all is the label offered as a starting point, without a
   confidence value, and the owner still chooses.

There is no trained model, nothing is learned from users, and the language model can
never change the suggested type or its confidence.
"""

from data.sectors import INTAKE_QUESTIONS, SECTOR_IDS, get_sector

CONFIDENCE_THRESHOLD = 0.6
MIN_LEADING_POINTS = 3


def _find_option(question, option_id):
    for option in question["options"]:
        if option["id"] == option_id:
            return option
    return None


def classify_business(intake_answers, description_sector=None):
    """Return the suggested business type, a confidence value and the reasons behind it.

    ``intake_answers`` maps intake question ids to the chosen option id.
    ``description_sector`` is an optional sector id read from the owner's own description.

    ``state`` is one of:
      "clear"        the answers point clearly to one type
      "close"        the answers gave points, but no type clearly leads
      "description"  the answers gave no points; only the description suggests a type
      "none"         nothing to go on
    """
    points = {sector_id: 0 for sector_id in SECTOR_IDS}
    reasons = []

    for question in INTAKE_QUESTIONS:
        option = _find_option(question, intake_answers.get(question["id"]))
        if option is None or not option["points"]:
            continue
        for sector_id, value in option["points"].items():
            points[sector_id] += value
        reasons.append({
            "label": question["short"],
            "answer": option["label"],
            "points_to": [get_sector(sector_id)["name"] for sector_id in option["points"]],
        })

    if description_sector not in points:
        description_sector = None

    total = sum(points.values())
    if total == 0:
        return {
            "state": "description" if description_sector else "none",
            "sector": description_sector,
            "confidence": 0.0,
            "confident": False,
            "points": points,
            "reasons": reasons,
            "description_sector": description_sector,
            "description_agrees": None,
        }

    ranked = sorted(SECTOR_IDS, key=lambda sector_id: -points[sector_id])
    leader, runner_up = ranked[0], ranked[1]
    confidence = round(points[leader] / total, 2)
    confident = (
        points[leader] >= MIN_LEADING_POINTS
        and confidence >= CONFIDENCE_THRESHOLD
        and points[leader] > points[runner_up]
    )
    return {
        "state": "clear" if confident else "close",
        "sector": leader,
        "confidence": confidence,
        "confident": confident,
        "points": points,
        "reasons": reasons,
        "description_sector": description_sector,
        "description_agrees": None if description_sector is None else description_sector == leader,
    }
