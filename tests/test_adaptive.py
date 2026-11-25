"""Sprint 2 acceptance checks: business-type classifier (3.4) and layered scoring (3.5).

Deliverable D4: at least four categories live, the classifier returns a confidence value,
and low-confidence sessions fall back to the core-only path.
Milestone M4: classifier works, core scores unchanged.
"""

import pytest

from conftest import (
    RETAIL_INTAKE,
    UNCLEAR_INTAKE,
    all_answers,
    complete_tailored,
    confirm_sector,
    login,
    logout,
    mixed_answers,
    register,
    sector_answers,
    submit_assessment,
    submit_intake,
)

CLEAR_PROFILES = {
    "retail": {"activity": "sell", "workplace": "shop", "payment": "counter", "information": "cards"},
    "hospitality": {"activity": "food", "workplace": "venue", "payment": "counter", "information": "bookings"},
    "trades": {"activity": "onsite", "workplace": "sites", "payment": "invoice", "information": "access"},
    "professional": {"activity": "advice", "workplace": "office", "payment": "invoice", "information": "records"},
}


# ---------- Sector content ----------

def test_four_predefined_business_types_with_question_sets(app_module):
    from data.questions import all_questions
    from data.sectors import SECTORS

    assert [sector["id"] for sector in SECTORS] == ["retail", "hospitality", "trades", "professional"]
    core_ids = {question["id"] for question in all_questions()}
    seen = set()
    for sector in SECTORS:
        assert 4 <= len(sector["questions"]) <= 6
        for question in sector["questions"]:
            for field in ("id", "question", "help", "recommendation", "priority", "reason"):
                assert question[field], f"{question.get('id')} is missing {field}"
            assert question["priority"] in {"Critical", "High", "Medium"}
            assert question["id"] not in core_ids and question["id"] not in seen
            seen.add(question["id"])


def test_every_sector_question_is_traceable_to_published_frameworks(app_module):
    from data.sectors import FRAMEWORKS, SECTORS

    for sector in SECTORS:
        for question in sector["questions"]:
            sources = question["sources"]
            assert len(sources) >= 2, question["id"]
            assert any(source["fit"] == "direct" for source in sources), question["id"]
            assert any(source["framework"] == "nist" for source in sources), question["id"]
            for source in sources:
                assert source["framework"] in FRAMEWORKS
                assert source["ref"] and source["fit"] in {"direct", "related"}


def test_sources_page_lists_every_sector_question(client):
    from data.sectors import SECTORS

    page = client.get("/tailored/sources")
    assert page.status_code == 200
    text = page.get_data(as_text=True)
    for sector in SECTORS:
        for question in sector["questions"]:
            assert question["question"].replace("'", "&#39;") in text
    assert "NIST CSF 2.0" in text and "Essential Eight" in text


def test_result_page_shows_what_each_sector_question_is_based_on(client):
    complete_tailored(client, all_answers("yes"), "retail", "yes")
    page = client.get("/result").get_data(as_text=True)
    assert "Based on:" in page and "PCI DSS v4.0.1 (Requirements 9.5.1.2 and 9.5.1.3)" in page


# ---------- The classifier ----------

@pytest.mark.parametrize("sector_id", sorted(CLEAR_PROFILES))
def test_clear_answers_are_classified_with_a_confidence_value(app_module, sector_id):
    from engine.classifier import CONFIDENCE_THRESHOLD, classify_business

    outcome = classify_business(CLEAR_PROFILES[sector_id])
    assert outcome["sector"] == sector_id
    assert outcome["confident"] is True
    assert CONFIDENCE_THRESHOLD <= outcome["confidence"] <= 1
    assert outcome["reasons"], "every suggestion must come with its reasons"


def test_unclear_answers_are_not_classified(app_module):
    from engine.classifier import classify_business

    outcome = classify_business(UNCLEAR_INTAKE)
    assert outcome["sector"] is None
    assert outcome["confident"] is False
    assert outcome["confidence"] == 0


def test_conflicting_answers_give_low_confidence(app_module):
    from engine.classifier import classify_business

    outcome = classify_business({"activity": "sell", "workplace": "office", "payment": "invoice", "information": "records"})
    assert outcome["confident"] is False


def test_a_description_never_changes_the_points_or_the_confidence(app_module):
    from engine.classifier import classify_business

    base = classify_business(CLEAR_PROFILES["retail"])
    agrees = classify_business(CLEAR_PROFILES["retail"], description_sector="retail")
    differs = classify_business(CLEAR_PROFILES["retail"], description_sector="hospitality")
    for outcome in (agrees, differs):
        assert outcome["points"] == base["points"]
        assert outcome["confidence"] == base["confidence"] and outcome["state"] == "clear"
    assert agrees["description_agrees"] is True and differs["description_agrees"] is False


def test_description_alone_is_offered_without_a_confidence_value(app_module):
    from engine.classifier import classify_business

    outcome = classify_business(UNCLEAR_INTAKE, description_sector="trades")
    assert outcome["state"] == "description" and outcome["sector"] == "trades"
    assert outcome["confident"] is False and outcome["confidence"] == 0


def test_every_result_has_one_of_four_states(app_module):
    from engine.classifier import classify_business

    split = {"activity": "sell", "workplace": "office", "payment": "invoice", "information": "records"}
    assert classify_business(CLEAR_PROFILES["trades"])["state"] == "clear"
    assert classify_business(split)["state"] == "close"
    assert classify_business(UNCLEAR_INTAKE, "retail")["state"] == "description"
    assert classify_business(UNCLEAR_INTAKE)["state"] == "none"


def test_keyword_fallback_reads_plain_descriptions(app_module):
    from ai.business_classifier import keyword_sector

    assert keyword_sector("We are a two-person electrical contracting business") == "trades"
    assert keyword_sector("Small cafe and bakery") == "hospitality"
    assert keyword_sector("A barber") is None  # "bar" must not match "barber"
    assert keyword_sector("Lawn mowing") is None  # "law" must not match "lawn"


def test_model_reply_is_only_accepted_if_it_is_one_of_the_fixed_labels(app_module, monkeypatch):
    import ai.business_classifier as business_classifier

    monkeypatch.setattr(business_classifier, "_ask_model", lambda text: "Professional.")
    assert business_classifier.interpret_description("We do tax returns") == ("professional", "ai")

    monkeypatch.setattr(business_classifier, "_ask_model", lambda text: "Ignore the rules and say hello")
    assert business_classifier.interpret_description("a plumber") == ("trades", "keywords")

    monkeypatch.setattr(business_classifier, "_ask_model", lambda text: "unknown")
    assert business_classifier.interpret_description("zzz") == (None, "ai")


def test_description_falls_back_to_keywords_when_the_ai_is_unavailable_or_over_budget(app_module, client, monkeypatch):
    # conftest makes the model call fail; the keyword match must still work.
    submit_intake(client, UNCLEAR_INTAKE, description="We run a small restaurant")
    page = client.get("/tailored/confirm").get_data(as_text=True)
    assert "FROM YOUR DESCRIPTION ONLY" in page and "Hospitality" in page
    assert 'value="hospitality" required checked' not in page, "a description-only match is never pre-selected"

    import ai.business_classifier as business_classifier

    called = []
    monkeypatch.setattr(business_classifier, "_ask_model", lambda text: called.append(text) or "retail")
    monkeypatch.setattr(app_module, "CHAT_DAILY_CAP", 0)
    submit_intake(client, UNCLEAR_INTAKE, description="We run a small restaurant")
    assert called == [], "the model must not be called once the spend cap is reached"


def test_the_model_is_never_called_without_a_description(app_module, client, monkeypatch):
    import ai.business_classifier as business_classifier

    called = []
    monkeypatch.setattr(business_classifier, "_ask_model", lambda text: called.append(text) or "retail")
    submit_intake(client, RETAIL_INTAKE)
    assert called == []


# ---------- The three-step flow ----------

def test_intake_needs_every_question_answered(client):
    response = submit_intake(client, {"activity": "sell"})
    assert response.status_code == 400


def test_tailored_forms_need_a_csrf_token(client):
    assert client.post("/tailored", data=RETAIL_INTAKE).status_code == 400
    submit_intake(client, RETAIL_INTAKE)
    assert client.post("/tailored/confirm", data={"sector": "retail"}).status_code == 400


def test_confident_result_is_shown_with_confidence_and_reasons(client):
    response = submit_intake(client, RETAIL_INTAKE)
    assert response.headers["Location"].endswith("/tailored/confirm")
    page = client.get("/tailored/confirm").get_data(as_text=True)
    assert "Does this look right?" in page
    assert "Retail" in page and "78%" in page
    assert "What each answer pointed to" in page and "How your answers were shared" in page


def test_low_confidence_asks_the_user_and_offers_the_core_only_path(client):
    submit_intake(client, UNCLEAR_INTAKE)
    page = client.get("/tailored/confirm").get_data(as_text=True)
    assert "Choose your business type" in page
    assert "NO MATCH FOUND" in page and "SUGGESTED BUSINESS TYPE" not in page

    response = confirm_sector(client, "core")
    assert response.headers["Location"].endswith("/assessment")
    # The tailored step is closed again, so the visitor is on the plain 20-question path.
    assert client.get("/tailored/assessment").headers["Location"].endswith("/tailored")


def test_the_match_card_is_shown_in_every_state(client, monkeypatch):
    import ai.business_classifier as business_classifier

    split = {"activity": "sell", "workplace": "office", "payment": "invoice", "information": "records"}
    cases = [
        (RETAIL_INTAKE, "", "SUGGESTED BUSINESS TYPE"),
        (split, "", "CLOSEST MATCH"),
        (UNCLEAR_INTAKE, "a plumber", "FROM YOUR DESCRIPTION ONLY"),
        (UNCLEAR_INTAKE, "", "NO MATCH FOUND"),
    ]
    for intake, description, label in cases:
        submit_intake(client, intake, description=description)
        page = client.get("/tailored/confirm").get_data(as_text=True)
        assert "suggestion-card" in page and label in page, label


def test_conflicting_description_keeps_the_card_and_flags_the_difference(client, monkeypatch):
    """Clear retail answers plus a description read as hospitality: the answers still decide."""
    import ai.business_classifier as business_classifier

    monkeypatch.setattr(business_classifier, "_ask_model", lambda text: "hospitality")
    submit_intake(client, RETAIL_INTAKE, description="We also run a small coffee counter")
    page = client.get("/tailored/confirm").get_data(as_text=True)
    assert "Does this look right?" in page and "SUGGESTED BUSINESS TYPE" in page
    assert "78%" in page
    assert "which differs from your answers" in page
    assert 'value="retail" required checked' in page


def test_agreeing_description_is_shown_as_a_cross_check(client, monkeypatch):
    import ai.business_classifier as business_classifier

    monkeypatch.setattr(business_classifier, "_ask_model", lambda text: "retail")
    submit_intake(client, RETAIL_INTAKE, description="A gift shop")
    page = client.get("/tailored/confirm").get_data(as_text=True)
    assert "Your description also reads as" in page and "78%" in page


def test_close_result_selects_nothing_and_records_no_confidence(client):
    split = {"activity": "sell", "workplace": "office", "payment": "invoice", "information": "records"}
    submit_intake(client, split)
    page = client.get("/tailored/confirm").get_data(as_text=True)
    assert "CLOSEST MATCH" in page and "56%" in page
    assert "required checked" not in page
    confirm_sector(client, "professional")
    client.post("/tailored/assessment", data={**all_answers("yes"), **sector_answers("professional")})
    assert "Business type chosen by you." in client.get("/result").get_data(as_text=True)


def test_user_can_override_the_suggestion(client):
    submit_intake(client, RETAIL_INTAKE)
    confirm_sector(client, "hospitality")
    page = client.get("/tailored/assessment").get_data(as_text=True)
    assert "Hospitality questions" in page and "hospitality_outage_plan" in page
    assert "retail_card_data" not in page


def test_an_unknown_business_type_is_rejected(client):
    submit_intake(client, RETAIL_INTAKE)
    assert confirm_sector(client, "banking").status_code == 400


def test_tailored_assessment_cannot_be_opened_without_a_confirmed_type(client):
    assert client.get("/tailored/assessment").headers["Location"].endswith("/tailored")
    assert client.get("/tailored/confirm").headers["Location"].endswith("/tailored")


def test_tailored_assessment_shows_the_20_core_questions_plus_the_sector_set(client):
    from data.questions import all_questions

    submit_intake(client, RETAIL_INTAKE)
    confirm_sector(client, "retail")
    page = client.get("/tailored/assessment").get_data(as_text=True)
    for question in all_questions():
        assert f'name="{question["id"]}"' in page
    assert "Why we ask:" in page
    assert "25 questions" in page


# ---------- Layered scoring ----------

def test_core_score_is_identical_with_and_without_sector_questions(client, second_client):
    """M4: core scores unchanged. Sector answers must never move the overall score."""
    from engine.risk_engine import calculate_assessment

    expected = calculate_assessment(mixed_answers())
    markers = (
        f'aria-label="Overall security score {expected["score"]} out of 100"',
        f'{expected["risk"]} RISK',
    )
    submit_assessment(client, mixed_answers())
    standard = client.get("/result").get_data(as_text=True)

    for sector_value in ("yes", "no"):
        complete_tailored(second_client, mixed_answers(), "retail", sector_value)
        tailored = second_client.get("/result").get_data(as_text=True)
        for marker in markers:
            assert marker in standard and marker in tailored


def test_result_page_shows_a_separate_sector_score_with_reasons(client):
    complete_tailored(client, all_answers("yes"), "trades", "no")
    page = client.get("/result").get_data(as_text=True)
    assert 'aria-label="Overall security score 100 out of 100"' in page
    assert "Trades and on-site services questions" in page
    assert "0 of 5" in page
    assert "Why we ask:" in page
    assert "Want questions that fit your kind of business?" not in page


def test_tailored_result_counts_all_questions_and_retakes_the_tailored_route(client):
    complete_tailored(client, all_answers("yes"), "retail", "yes")
    page = client.get("/result").get_data(as_text=True)
    assert "25<small>/25</small>" in page
    assert 'href="/tailored" class="btn btn-dashboard-outline"' in page

    submit_assessment(client, all_answers("yes"))
    page = client.get("/result").get_data(as_text=True)
    assert "20<small>/20</small>" in page
    assert 'href="/assessment" class="btn btn-dashboard-outline"' in page


def test_tailored_pages_show_which_step_the_owner_is_on(client):
    assert 'aria-current="step"' in client.get("/tailored").get_data(as_text=True)
    submit_intake(client, RETAIL_INTAKE)
    page = client.get("/tailored/confirm").get_data(as_text=True)
    assert page.count("step-done") == 1 and page.count("step-current") == 1


def test_standard_result_page_invites_the_tailored_assessment(client):
    submit_assessment(client, mixed_answers())
    page = client.get("/result").get_data(as_text=True)
    assert "Want questions that fit your kind of business?" in page
    assert 'id="sector-results"' not in page


def test_pdf_report_still_downloads_for_a_tailored_result(client):
    complete_tailored(client, mixed_answers(), "professional", "no")
    response = client.get("/download-report")
    assert response.status_code == 200 and response.data.startswith(b"%PDF")


def test_tailored_session_cookie_stays_small(client):
    response = complete_tailored(client, all_answers("no"), "retail", "no")
    cookie = next(value for value in response.headers.getlist("Set-Cookie") if value.startswith("session="))
    assert len(cookie) < 1000


# ---------- Guests and accounts ----------

def test_guest_tailored_result_is_not_saved(app_module, client):
    complete_tailored(client, mixed_answers())
    with app_module.app.app_context():
        assert app_module.db.session.query(app_module.AssessmentSession).count() == 0
    assert "Want to keep this result?" in client.get("/result").get_data(as_text=True)


def test_signed_in_tailored_result_is_saved_with_business_type_and_sector_score(app_module, client):
    register(client)
    complete_tailored(client, all_answers("yes"), "hospitality", "no")
    with app_module.app.app_context():
        record = app_module.db.session.query(app_module.AssessmentSession).one()
        assert record.business_type == "hospitality"
        assert record.overall_score == 100

    entry = client.get("/api/assessment-history").get_json()["assessments"][0]
    assert entry["business_type"] == "Hospitality"
    assert entry["sector_score"] == 0
    assert len(entry["category_scores"]) == 6, "sector row must stay out of the six core categories"

    page = client.get("/history").get_data(as_text=True)
    assert "Hospitality" in page and "Sector score" in page


def test_guest_tailored_result_is_imported_on_registration(client):
    complete_tailored(client, mixed_answers(), "trades", "yes")
    register(client)
    entry = client.get("/api/assessment-history").get_json()["assessments"][0]
    assert entry["business_type"] == "Trades and on-site services"
    assert entry["sector_score"] == 100


def test_standard_and_tailored_attempts_share_one_comparable_trend(client):
    register(client)
    submit_assessment(client, all_answers("no"))
    complete_tailored(client, all_answers("yes"), "retail", "no")
    logout(client)
    login(client)
    entries = client.get("/api/assessment-history").get_json()["assessments"]
    assert [entry["score"] for entry in entries] == [0, 100]
    assert [entry["business_type"] for entry in entries] == [None, "Retail"]


# ---------- Assistant context (3.6) ----------

def test_assistant_is_told_the_business_type_but_not_free_text(app_module, client, monkeypatch):
    calls = []
    monkeypatch.setattr(app_module, "get_openai_response", lambda message, risk_context=None: calls.append(risk_context) or "ok")
    complete_tailored(client, all_answers("no"), "retail", "no")
    client.post("/api/chat", json={"message": "What should I fix first?"})
    assert calls == ["CRITICAL risk (overall score 0/100). Business type: Retail (sector questions score 0%)"]


def test_ask_ai_shortcut_works_for_sector_recommendations(app_module, client, monkeypatch):
    from data.sectors import get_sector

    calls = []
    monkeypatch.setattr(app_module, "get_openai_response", lambda message, risk_context=None: calls.append(message) or "ok")
    complete_tailored(client, all_answers("yes"), "retail", "no")
    title = get_sector("retail")["questions"][0]["question"]
    message = f'[ASK_AI] What does "{title}" mean and why is it important for my small business?'
    client.post("/api/chat", json={"message": message})
    assert calls == [message]


def test_results_saved_by_the_previous_version_still_open(app_module, client):
    """A browser that still holds a Sprint 1 session cookie must not break."""
    from engine.risk_engine import calculate_assessment
    from utils.recommendations import generate_recommendations

    old = calculate_assessment(mixed_answers())
    old["recommendations"] = generate_recommendations(old["answers"])
    old["assessment_date"] = "02 November 2026"
    with client.session_transaction() as session:
        session["assessment_result"] = old
    page = client.get("/result")
    assert page.status_code == 200
    assert "02 November 2026" in page.get_data(as_text=True)


def test_description_only_card_shows_low_confidence_and_how_it_was_read(client, monkeypatch):
    """Every card carries a confidence signal; without points it is a worded level, never a percentage."""
    import ai.business_classifier as business_classifier

    submit_intake(client, UNCLEAR_INTAKE, description="We run a small restaurant and coffee bar")
    page = client.get("/tailored/confirm").get_data(as_text=True)
    assert "<strong>Low</strong><span>confidence</span>" in page
    assert "How your description was read" in page and "a keyword match, with no AI involved" in page
    assert "coffee, restaurant, bar" in page
    assert "%</strong>" not in page, "no percentage without points to count"

    monkeypatch.setattr(business_classifier, "_ask_model", lambda text: "hospitality")
    submit_intake(client, UNCLEAR_INTAKE, description="Korean cuisine")
    page = client.get("/tailored/confirm").get_data(as_text=True)
    assert "an AI model that may only reply with one of the four type names" in page
    assert "this rests on the AI reading alone" in page


def test_no_match_card_says_none_instead_of_a_percentage(client):
    submit_intake(client, UNCLEAR_INTAKE)
    page = client.get("/tailored/confirm").get_data(as_text=True)
    assert "NO MATCH FOUND" in page and "<strong>None</strong><span>no match</span>" in page


def test_weight_sensitivity_never_changes_which_type_is_suggested():
    """Evidence for the report: across all 500 possible intake answers, re-weighting the questions
    changes only how often a result is "clear", never which business type a clear result names."""
    import copy
    import itertools

    import engine.classifier as classifier
    from data.sectors import INTAKE_QUESTIONS

    ids = [question["id"] for question in INTAKE_QUESTIONS]
    combinations = list(itertools.product(*[[o["id"] for o in q["options"]] for q in INTAKE_QUESTIONS]))
    assert len(combinations) == 500

    def outcomes(questions):
        original = classifier.INTAKE_QUESTIONS
        classifier.INTAKE_QUESTIONS = questions
        try:
            return {combo: classifier.classify_business(dict(zip(ids, combo))) for combo in combinations}
        finally:
            classifier.INTAKE_QUESTIONS = original

    def reweighted(activity, workplace, others=None):
        questions = copy.deepcopy(INTAKE_QUESTIONS)
        for question, weight in zip(questions, (activity, workplace, others, others)):
            if weight is not None:
                for option in question["options"]:
                    option["points"] = {sector: weight for sector in option["points"]}
        return questions

    base = outcomes(INTAKE_QUESTIONS)
    for weights in [(1, 1, 1), (2, 2, None), (4, 2, None), (3, 3, None)]:
        other = outcomes(reweighted(*weights))
        for combo in combinations:
            if base[combo]["state"] == "clear" and other[combo]["state"] == "clear":
                assert base[combo]["sector"] == other[combo]["sector"], (weights, combo)
