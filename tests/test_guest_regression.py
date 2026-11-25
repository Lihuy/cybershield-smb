"""Guest-path regression suite (Goal 3 / Deliverable D5).

These checks protect the ITW601-validated experience: the 20-question instrument,
the scoring rules, the recommendations, the PDF and the no-sign-up guest journey.
Run them at every sprint review:  pytest -v
"""

from conftest import all_answers, mixed_answers, submit_assessment

# The validated v1.0 instrument. If a question is added, removed or renamed,
# this test fails on purpose so the change is a deliberate, reviewed decision.
V1_QUESTION_IDS = [
    "mfa", "unique_passwords", "least_privilege", "account_review",
    "automatic_updates", "endpoint_protection", "screen_lock", "disk_encryption",
    "firewall", "secure_wifi", "guest_network",
    "email_mfa", "email_filtering", "payment_verification",
    "regular_backups", "offsite_backup", "restore_testing",
    "security_training", "phishing_reporting", "incident_process",
]


# ---------- The instrument ----------

def test_question_bank_is_the_validated_20_question_set(app_module):
    from data.questions import ASSESSMENT_CATEGORIES, all_questions

    assert [question["id"] for question in all_questions()] == V1_QUESTION_IDS
    assert [category["id"] for category in ASSESSMENT_CATEGORIES] == [
        "identity", "device", "network", "email", "backup", "awareness",
    ]
    assert [len(category["questions"]) for category in ASSESSMENT_CATEGORIES] == [4, 4, 3, 3, 3, 3]


def test_every_question_has_the_fields_the_ui_needs(app_module):
    from data.questions import all_questions

    for question in all_questions():
        for field in ("id", "question", "help", "recommendation", "priority"):
            assert question[field], f"{question.get('id')} is missing {field}"
        assert question["priority"] in {"Critical", "High", "Medium"}


# ---------- The scoring engine ----------

def test_all_yes_scores_100_and_low_risk(app_module):
    from engine.risk_engine import calculate_assessment

    result = calculate_assessment(all_answers("yes"))
    assert result["score"] == 100
    assert result["risk"] == "LOW"
    assert result["total_questions"] == 20


def test_all_no_scores_0_and_critical_risk(app_module):
    from engine.risk_engine import calculate_assessment

    result = calculate_assessment(all_answers("no"))
    assert result["score"] == 0
    assert result["risk"] == "CRITICAL"


def test_missing_answers_count_as_no(app_module):
    from engine.risk_engine import calculate_assessment

    assert calculate_assessment({})["score"] == 0


def test_risk_tier_boundaries(app_module):
    from engine.risk_engine import risk_level

    assert risk_level(100) == "LOW"
    assert risk_level(80) == "LOW"
    assert risk_level(79) == "MEDIUM"
    assert risk_level(60) == "MEDIUM"
    assert risk_level(59) == "HIGH"
    assert risk_level(40) == "HIGH"
    assert risk_level(39) == "CRITICAL"
    assert risk_level(0) == "CRITICAL"


def test_categories_are_weighted_equally(app_module):
    """A perfect 4-question category and a perfect 3-question category are worth the same."""
    from engine.risk_engine import calculate_assessment

    identity_only = {qid: "yes" for qid in V1_QUESTION_IDS[0:4]}
    network_only = {qid: "yes" for qid in V1_QUESTION_IDS[8:11]}
    assert calculate_assessment(identity_only)["score"] == 17
    assert calculate_assessment(network_only)["score"] == 17


# ---------- Recommendations ----------

def test_recommendations_cover_every_no_answer_in_priority_order(app_module):
    from engine.risk_engine import calculate_assessment
    from utils.recommendations import generate_recommendations

    answers = calculate_assessment(all_answers("no"))["answers"]
    items = generate_recommendations(answers)
    assert len(items) == 20
    order = {"Critical": 0, "High": 1, "Medium": 2}
    ranks = [order[item["priority"]] for item in items]
    assert ranks == sorted(ranks)


def test_no_recommendations_when_everything_is_in_place(app_module):
    from engine.risk_engine import calculate_assessment
    from utils.recommendations import generate_recommendations

    answers = calculate_assessment(all_answers("yes"))["answers"]
    assert generate_recommendations(answers) == []


# ---------- The guest journey in the browser ----------

def test_public_pages_load_without_an_account(client):
    for path in ("/", "/assessment", "/assistant", "/privacy", "/login", "/register"):
        assert client.get(path).status_code == 200, path


def test_assessment_page_shows_all_20_questions(client):
    page = client.get("/assessment").get_data(as_text=True)
    for question_id in V1_QUESTION_IDS:
        assert f'name="{question_id}"' in page


def test_guest_can_complete_the_assessment_with_zero_sign_up_steps(client):
    response = submit_assessment(client, mixed_answers())
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/result")

    page = client.get("/result")
    assert page.status_code == 200
    text = page.get_data(as_text=True)
    assert "Your cybersecurity dashboard" in text
    assert "Recommended next steps" in text
    assert "Want to keep this result?" in text  # guest is invited, never forced, to register


def test_guest_result_is_not_written_to_the_database(app_module, client):
    submit_assessment(client, mixed_answers())
    with app_module.app.app_context():
        assert app_module.db.session.query(app_module.AssessmentSession).count() == 0
        assert app_module.db.session.query(app_module.User).count() == 0


def test_guest_can_download_the_pdf_report(client):
    submit_assessment(client, mixed_answers())
    response = client.get("/download-report")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.data.startswith(b"%PDF")


def test_result_and_pdf_redirect_to_the_assessment_when_there_is_no_result(client):
    for path in ("/result", "/download-report"):
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/assessment")


def test_guest_session_cookie_stays_under_the_browser_limit(client):
    """Worst case: every answer is No, so all 20 recommendations ride in the cookie."""
    response = submit_assessment(client, all_answers("no"))
    cookie = next(value for value in response.headers.getlist("Set-Cookie") if value.startswith("session="))
    assert len(cookie) < 4093


def test_history_is_closed_to_guests(client):
    page = client.get("/history")
    assert page.status_code == 302
    assert "/login" in page.headers["Location"]
    assert client.get("/api/assessment-history").status_code == 401


def test_rule_based_assistant_still_answers_offline(client):
    response = client.post("/assistant", data={"question": "What is MFA?"})
    assert response.status_code == 200
    assert "Multi-factor authentication" in response.get_data(as_text=True)


def test_core_questions_trace_to_frameworks_without_changing_v1_content():
    """Sprint 2 traceability: every core question names its sources; wording and scoring are untouched."""
    from data.questions import all_questions
    from data.sectors import FRAMEWORKS

    functions = {"GOVERN", "IDENTIFY", "PROTECT", "DETECT", "RESPOND", "RECOVER"}
    for question in all_questions():
        assert question["reason"].strip(), question["id"]
        assert question["csf_functions"] and set(question["csf_functions"]) <= functions, question["id"]
        assert len(question["sources"]) >= 2, question["id"]
        frameworks = [source["framework"] for source in question["sources"]]
        assert "nist" in frameworks, f"{question['id']} must cite a NIST CSF 2.0 subcategory"
        for source in question["sources"]:
            assert source["framework"] in FRAMEWORKS and source["fit"] in {"direct", "related"}
            assert source["ref"].strip()
            if source["framework"] == "nist":
                import re
                assert re.fullmatch(r"(GV|ID|PR|DE|RS|RC)\.[A-Z]{2}-\d{2}", source["ref"]), source["ref"]


def test_sources_page_lists_core_and_sector_questions(client):
    page = client.get("/tailored/sources").get_data(as_text=True)
    assert "The 20 core questions" in page and "Questions for each business type" in page
    assert "PR.AA-03" in page and "Regular backups" in page and "Prepare your staff: Educate employees" in page
    assert page.count('<span class="function-tag">') >= 20


def test_core_recommendations_show_what_they_are_based_on(client):
    client.post("/assessment", data=all_answers("no"))
    page = client.get("/result").get_data(as_text=True)
    assert page.count("<p class=\"source-line\">Based on: ") == 20 and "Essential Eight (Regular backups)" in page


def test_missing_pages_and_expired_forms_show_branded_error_pages(client):
    page = client.get("/no-such-page")
    assert page.status_code == 404 and "Page not found" in page.get_data(as_text=True)
    assert "Back to home" in page.get_data(as_text=True)

    expired = client.post("/login", data={"email": "a@example.com", "password": "x"})
    assert expired.status_code == 400 and "This form has expired" in expired.get_data(as_text=True)


def test_unexpected_errors_show_a_branded_500_page(client, monkeypatch):
    from app import app

    def broken():
        raise RuntimeError("simulated failure")

    monkeypatch.setitem(app.view_functions, "privacy", broken)
    monkeypatch.setitem(app.config, "PROPAGATE_EXCEPTIONS", False)
    page = client.get("/privacy")
    assert page.status_code == 500 and "Something went wrong on our side" in page.get_data(as_text=True)


def test_home_page_introduces_the_2_0_features(client):
    page = client.get("/").get_data(as_text=True)
    for text in ("Tailored Assessment", "Score History", "Traceable Questions", "v2.0"):
        assert text in page
