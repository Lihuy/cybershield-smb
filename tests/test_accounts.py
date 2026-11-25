"""Sprint 1 acceptance checks: accounts (3.1), guest-to-account upgrade (3.2) and score history (3.3)."""

from conftest import (
    STRONG_PASSWORD,
    all_answers,
    csrf_for,
    login,
    logout,
    mixed_answers,
    register,
    submit_assessment,
)


def _history(test_client):
    return test_client.get("/api/assessment-history").get_json()["assessments"]


# ---------- Registration rules ----------

def test_registration_creates_a_hashed_account_with_a_consent_record(app_module, client):
    response = register(client)
    assert response.status_code == 302
    with app_module.app.app_context():
        user = app_module.db.session.query(app_module.User).one()
        assert user.email == "owner@example.com"
        assert user.password_hash.startswith("scrypt:")
        assert STRONG_PASSWORD not in user.password_hash
        consent = app_module.db.session.query(app_module.PrivacyConsent).one()
        assert consent.user_id == user.id
        assert consent.notice_version == app_module.PRIVACY_NOTICE_VERSION


def test_registration_requires_privacy_consent(app_module, client):
    assert register(client, consent=False).status_code == 400
    with app_module.app.app_context():
        assert app_module.db.session.query(app_module.User).count() == 0


def test_registration_rejects_passwords_shorter_than_15_characters(client):
    assert register(client, password="short-pass-14c").status_code == 400


def test_registration_rejects_breached_passwords(app_module, client, monkeypatch):
    monkeypatch.setattr(app_module, "_password_is_breached", lambda password: True)
    response = register(client)
    assert response.status_code == 400
    assert "known data breaches" in response.get_data(as_text=True)


def test_registration_fails_closed_when_the_breach_check_is_unreachable(app_module, client, monkeypatch):
    monkeypatch.setattr(app_module, "_password_is_breached", lambda password: None)
    assert register(client).status_code == 503


def test_duplicate_email_is_rejected(client, second_client):
    assert register(client).status_code == 302
    assert register(second_client).status_code == 409


def test_forms_without_a_csrf_token_are_rejected(client):
    response = client.post("/register", data={"email": "a@example.com", "password": STRONG_PASSWORD, "privacy_consent": "yes"})
    assert response.status_code == 400
    assert client.post("/login", data={"email": "a@example.com", "password": STRONG_PASSWORD}).status_code == 400
    assert client.post("/logout").status_code == 400


# ---------- Login ----------

def test_login_with_a_wrong_password_fails_without_revealing_which_part_was_wrong(client, second_client):
    register(client)
    wrong_password = login(second_client, password="this is the wrong password!")
    unknown_email = login(second_client, email="nobody@example.com")
    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert "Email or password is incorrect." in wrong_password.get_data(as_text=True)
    assert "Email or password is incorrect." in unknown_email.get_data(as_text=True)


def test_repeated_failed_logins_are_rate_limited(client, second_client):
    register(client)
    statuses = [login(second_client, password="this is the wrong password!").status_code for _ in range(6)]
    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429


# ---------- Guest-to-account upgrade (3.2.2) ----------

def test_guest_result_is_imported_once_when_the_guest_registers(client):
    submit_assessment(client, mixed_answers())
    response = register(client)
    assert response.headers["Location"].endswith("/result")
    entries = _history(client)
    assert len(entries) == 1

    # Reloading pages or logging in again must not duplicate the imported record.
    client.get("/result")
    logout(client)
    login(client)
    assert len(_history(client)) == 1


def test_result_page_confirms_the_save_for_signed_in_users(client):
    submit_assessment(client, mixed_answers())
    register(client)
    text = client.get("/result").get_data(as_text=True)
    assert "Saved to your score history" in text
    assert "Want to keep this result?" not in text


# ---------- Score history (3.3) and Deliverable D3 ----------

def test_signed_in_assessments_are_saved_and_survive_logout_and_login(client):
    """Mirrors the manual walkthrough: guest attempt, register, second attempt, fresh login."""
    submit_assessment(client, all_answers("no"))
    register(client)
    submit_assessment(client, all_answers("yes"))
    logout(client)
    assert client.get("/api/assessment-history").status_code == 401
    login(client)

    entries = _history(client)
    assert [entry["score"] for entry in entries] == [0, 100]
    assert [entry["risk_tier"] for entry in entries] == ["CRITICAL", "LOW"]

    page = client.get("/history").get_data(as_text=True)
    assert "2 saved assessments" in page
    assert "scoreHistoryChart" in page


def test_result_page_shows_the_change_since_the_previous_attempt(client):
    register(client)
    submit_assessment(client, all_answers("no"))
    submit_assessment(client, all_answers("yes"))
    text = client.get("/result").get_data(as_text=True)
    assert "Up 100 points" in text


def test_raw_answers_are_never_written_to_the_database(app_module, client):
    register(client)
    submit_assessment(client, mixed_answers())
    with app_module.app.app_context():
        history = app_module.db.session.query(app_module.AssessmentHistory).one()
        stored = str(history.category_scores) + str(history.recommendations)
        assert "answers" not in stored


def test_one_user_cannot_see_another_users_history(client, second_client):
    register(client, email="first@example.com")
    submit_assessment(client, all_answers("yes"))

    register(second_client, email="second@example.com")
    assert _history(second_client) == []
    submit_assessment(second_client, all_answers("no"))

    assert [entry["score"] for entry in _history(client)] == [100]
    assert [entry["score"] for entry in _history(second_client)] == [0]


# ---------- Account deletion ----------

def test_account_deletion_needs_the_password_and_removes_everything(app_module, client):
    register(client)
    submit_assessment(client, mixed_answers())
    token = csrf_for(client, "/history")

    wrong = client.post("/account/delete", data={"csrf_token": token, "password": "not the right password"})
    assert wrong.status_code == 400

    done = client.post("/account/delete", data={"csrf_token": token, "password": STRONG_PASSWORD})
    assert done.status_code == 302
    with app_module.app.app_context():
        database = app_module.db.session
        assert database.query(app_module.User).count() == 0
        assert database.query(app_module.AssessmentSession).count() == 0
        assert database.query(app_module.AssessmentHistory).count() == 0
        assert database.query(app_module.PrivacyConsent).count() == 0
    assert client.get("/history").status_code == 302
