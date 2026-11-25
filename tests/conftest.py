"""Shared fixtures for the CyberShield SMB test suite.

Every test gets a brand-new app and an empty temporary SQLite database, and no test
ever calls the network (the breach check and OpenAI are replaced with fakes).
"""

import importlib
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRONG_PASSWORD = "correct horse battery staple 42"


@pytest.fixture()
def app_module(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.sqlite'}")
    monkeypatch.setenv("CYBERSHIELD_SECRET_KEY", "pytest-only-secret-key-0123456789abcdef")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.delenv("CYBERSHIELD_TRUST_PROXY", raising=False)
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    for name in ("app", "database"):
        sys.modules.pop(name, None)
    module = importlib.import_module("app")
    module.app.config.update(TESTING=True)
    monkeypatch.setattr(module, "_password_is_breached", lambda password: False)

    def no_network(*args, **kwargs):
        raise AssertionError("The test attempted to call OpenAI")

    monkeypatch.setattr(module, "get_openai_response", no_network)

    import ai.business_classifier as business_classifier

    monkeypatch.setattr(business_classifier, "_ask_model", no_network)
    return module


@pytest.fixture()
def client(app_module):
    return app_module.app.test_client()


@pytest.fixture()
def second_client(app_module):
    return app_module.app.test_client()


def csrf_for(test_client, path="/login"):
    """Load a page so the session has a CSRF token, then return it."""
    test_client.get(path)
    with test_client.session_transaction() as session:
        return session["_csrf_token"]


def all_answers(value="yes"):
    from data.questions import all_questions

    return {question["id"]: value for question in all_questions()}


def mixed_answers():
    """First ten questions Yes, the rest No (a 'middle' result)."""
    from data.questions import all_questions

    return {question["id"]: ("yes" if index < 10 else "no") for index, question in enumerate(all_questions())}


def submit_assessment(test_client, answers):
    return test_client.post("/assessment", data=answers)


def register(test_client, email="owner@example.com", password=STRONG_PASSWORD, consent=True):
    token = csrf_for(test_client, "/register")
    data = {"csrf_token": token, "email": email, "password": password}
    if consent:
        data["privacy_consent"] = "yes"
    return test_client.post("/register", data=data)


def login(test_client, email="owner@example.com", password=STRONG_PASSWORD):
    token = csrf_for(test_client, "/login")
    return test_client.post("/login", data={"csrf_token": token, "email": email, "password": password})


def logout(test_client):
    with test_client.session_transaction() as session:
        token = session.get("_csrf_token", "")
    return test_client.post("/logout", data={"csrf_token": token})


# ---------- Tailored (adaptive) assessment helpers ----------

RETAIL_INTAKE = {"activity": "sell", "workplace": "shop", "payment": "counter", "information": "cards"}
UNCLEAR_INTAKE = {"activity": "other", "workplace": "mixed", "payment": "mixed", "information": "unsure"}


def submit_intake(test_client, answers, description=""):
    token = csrf_for(test_client, "/tailored")
    return test_client.post("/tailored", data={"csrf_token": token, "description": description, **answers})


def confirm_sector(test_client, sector):
    token = csrf_for(test_client, "/tailored/confirm")
    return test_client.post("/tailored/confirm", data={"csrf_token": token, "sector": sector})


def sector_answers(sector_id, value="yes"):
    from data.sectors import get_sector

    return {question["id"]: value for question in get_sector(sector_id)["questions"]}


def complete_tailored(test_client, core, sector_id="retail", sector_value="yes", intake=None):
    """Run the whole tailored flow and return the final response."""
    submit_intake(test_client, intake or RETAIL_INTAKE)
    confirm_sector(test_client, sector_id)
    return test_client.post("/tailored/assessment", data={**core, **sector_answers(sector_id, sector_value)})
