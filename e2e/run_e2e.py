"""CyberShield SMB 2.0: automatic browser end-to-end tests.

One command starts the app, opens a real browser and uses the site the way an owner would:
guest assessment, PDF report, assistant, registering, score history, logging in and out,
the tailored assessment in every suggestion state, the sources page, security checks,
account deletion and phone-width layout. Every step checks what appears on screen against
the scoring rules in the code, takes a screenshot, and is written to an HTML report.

Setup (once):
    pip install -r requirements-dev.txt
    python -m playwright install chromium

Run (from the project folder):
    python e2e/run_e2e.py                   watch it in a visible Chromium window, then open the report
    python e2e/run_e2e.py --browsers all    Chromium, Firefox and WebKit (Safari's engine) in parallel
    python e2e/run_e2e.py --browsers chrome  use the Google Chrome already on this computer (no download)
    python e2e/run_e2e.py --demo            slow, with captions and highlights, for watching or presenting
    python e2e/run_e2e.py --demo --step     as --demo, but waits for Enter before each step
    python e2e/run_e2e.py --headless        no visible browser (faster; used for automatic runs)
    python e2e/run_e2e.py --live-ai         also call GPT-4o-mini for real (uses your .env key)

For Firefox and WebKit, install them once: python -m playwright install firefox webkit
When several browsers are chosen, each one runs in its own process against its own copy of the
app and its own empty database, so the runs cannot affect each other.

The report is written to e2e/report/index.html. The exit code is 0 only if every step passed.
Your own database is never used: each run starts with an empty temporary database.
"""

import argparse
import html
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
import webbrowser
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from data.questions import all_questions  # noqa: E402
from data.sectors import get_sector  # noqa: E402
from engine.classifier import classify_business  # noqa: E402
from engine.risk_engine import calculate_assessment  # noqa: E402
from engine.sector_engine import calculate_sector  # noqa: E402
from utils.recommendations import generate_recommendations  # noqa: E402

sys.path.insert(0, HERE)
from server import BREACHED_PASSWORD  # noqa: E402

EMAIL = "owner.e2e@example.com"
PASSWORD = "correct horse battery staple 42"
QUESTIONS = all_questions()

# Fixed answer patterns so the expected results can be worked out from the scoring rules.
MIXED = {q["id"]: ("yes" if i % 3 != 0 else "no") for i, q in enumerate(QUESTIONS)}           # 13 of 20 Yes
SECOND = {q["id"]: ("yes" if i % 4 != 0 else "no") for i, q in enumerate(QUESTIONS)}          # 15 of 20 Yes
ALL_YES = {q["id"]: "yes" for q in QUESTIONS}
RETAIL = {"activity": "sell", "workplace": "shop", "payment": "counter", "information": "cards"}
HOSPITALITY = {"activity": "food", "workplace": "venue", "payment": "counter", "information": "cards"}
SPLIT = {"activity": "sell", "workplace": "office", "payment": "invoice", "information": "records"}
UNSURE = {"activity": "other", "workplace": "mixed", "payment": "mixed", "information": "unsure"}


class StepFailed(Exception):
    pass


class Step:
    def __init__(self, number, group, title, purpose, func, needs_live_ai=False):
        self.number, self.group, self.title, self.purpose = number, group, title, purpose
        self.func, self.needs_live_ai = func, needs_live_ai
        self.checks, self.status, self.error, self.screenshot, self.seconds = [], "not run", "", None, 0.0


STEPS = []


def step(group, title, purpose, needs_live_ai=False):
    def register(func):
        STEPS.append(Step(len(STEPS) + 1, group, title, purpose, func, needs_live_ai))
        return func
    return register


class Context:
    """What each step can use: the browser page, the site address and a check() helper."""

    def __init__(self, page, base, current, live_ai, demo=None):
        self.page, self.base, self.current, self.live_ai = page, base, current, live_ai
        self.demo = demo  # None, or the DemoMode that shows captions and pauses
        self.console_errors = []
        self.remember = {}

    def check(self, condition, description, detail=""):
        self.current.checks.append((bool(condition), description, detail))
        if self.demo:
            self.demo.show(self.current)
            self.demo.pause(self.demo.check_pause)
        if not condition:
            raise StepFailed(description + (f" ({detail})" if detail else ""))

    def go(self, path):
        response = self.page.goto(self.base + path)
        self.page.wait_for_load_state("networkidle")
        return response

    def text(self, selector="body"):
        return self.page.inner_text(selector)

    def answer_core(self, answers):
        for question in QUESTIONS:
            self.page.click(f'label[for="{question["id"]}-{answers[question["id"]]}"]')

    def answer(self, answers):
        for question_id, value in answers.items():
            self.page.click(f'label[for="{question_id}-{value}"]')

    def submit_and_wait(self, selector):
        with self.page.expect_navigation():
            self.page.click(selector)
        self.page.wait_for_load_state("networkidle")

    def intake(self, answers, description=""):
        self.go("/tailored")
        for question_id, option_id in answers.items():
            self.page.check(f"#{question_id}-{option_id}")
        self.page.fill("#description", description)
        self.submit_and_wait(".assessment-submit-card button[type=submit]")

    def logged_in(self):
        return self.page.locator("form[action='/logout']").count() > 0


# ----------------------------------------------------------------------------------------
# A. Pages and navigation
# ----------------------------------------------------------------------------------------

@step("Pages", "Home page opens with the main navigation",
      "A visitor can reach every feature from the home page without an account.")
def home_page(ctx):
    response = ctx.go("/")
    ctx.check(response.status == 200, "Home page returns HTTP 200")
    nav = ctx.text("nav")
    for label in ("Start assessment", "Tailored assessment", "Ask AI", "Log in", "Create account"):
        ctx.check(label in nav, f'Navigation shows "{label}"')


@step("Pages", "Privacy notice shows the current version",
      "Registration asks for consent to a specific, versioned privacy notice (v1.1).")
def privacy_page(ctx):
    ctx.go("/privacy")
    body = ctx.text()
    ctx.check("1.1" in body, "Privacy notice shows version 1.1")
    ctx.check("tailored assessment" in body.lower(), "Notice explains what the tailored assessment stores")


# ----------------------------------------------------------------------------------------
# B. Guest assessment (the unchanged v1.0 instrument)
# ----------------------------------------------------------------------------------------

@step("Guest assessment", "Unanswered questions are caught before submitting",
      "The owner cannot get a score from a half-finished questionnaire.")
def incomplete_assessment(ctx):
    ctx.go("/assessment")
    ctx.check(ctx.page.locator(".answer-input").count() == 40, "All 20 questions are shown, each with Yes and No")
    ctx.page.click(f'label[for="{QUESTIONS[0]["id"]}-yes"]')
    ctx.page.click("#submitAssessment")
    ctx.check(ctx.page.is_visible("#formError"), "An error message appears instead of a result")
    ctx.check(ctx.page.url.endswith("/assessment"), "The page stays on the questionnaire")


@step("Guest assessment", "All safeguards in place gives 100 and Low risk",
      "Checks the top end of the scoring rules and the empty action plan.")
def all_yes(ctx):
    ctx.go("/assessment")
    ctx.answer_core(ALL_YES)
    ctx.submit_and_wait("#submitAssessment")
    body = ctx.text()
    ctx.check("/result" in ctx.page.url, "Submitting opens the results page")
    ctx.check(ctx.page.inner_text(".kpi-primary strong").startswith("100"), "Overall score shows 100/100")
    ctx.check("LOW" in ctx.page.inner_text(".risk-badge").upper(), "Risk badge shows LOW")
    ctx.check("no gaps were reported" in body, "The action plan says no gaps were reported")


@step("Guest assessment", "Mixed answers produce the score the rules predict",
      "The score on screen must equal the scoring engine: each category is the % answered Yes, "
      "the overall score is the mean of the six categories, and the risk tier follows 80/60/40.")
def mixed_answers(ctx):
    expected = calculate_assessment(MIXED)
    expected_recommendations = generate_recommendations(expected["answers"])
    ctx.remember["first_score"] = expected["score"]
    ctx.go("/assessment")
    ctx.answer_core(MIXED)
    ctx.submit_and_wait("#submitAssessment")
    shown = ctx.page.inner_text(".kpi-primary strong")
    ctx.check(shown.startswith(str(expected["score"])), f"Overall score shows {expected['score']}/100",
              f"screen shows {shown!r}")
    ctx.check(expected["risk"] in ctx.page.inner_text(".risk-badge").upper(), f"Risk badge shows {expected['risk']}")
    for category in expected["category_scores"]:
        ctx.check(f"{category['score']}%" in ctx.text(), f"{category['name']} shows {category['score']}%")
    cards = ctx.page.locator(".recommendations-section .recommendation-card").count()
    ctx.check(cards == len(expected_recommendations),
              f"{len(expected_recommendations)} recommendations, one per safeguard answered No", f"found {cards}")
    first = ctx.page.locator(".recommendations-section .recommendation-card .priority-pill").first.inner_text()
    ctx.check(first.startswith("Critical"), "Critical items are listed first", first)
    based_on = ctx.page.locator(".recommendations-section .source-line").count()
    ctx.check(based_on == cards, "Every recommendation shows the frameworks it is based on")


@step("Guest assessment", "The PDF report downloads",
      "Owners can keep their result without an account.")
def pdf_report(ctx):
    response = ctx.page.request.get(ctx.base + "/download-report")
    ctx.check(response.status == 200, "Download returns HTTP 200")
    ctx.check("application/pdf" in response.headers.get("content-type", ""), "File is a PDF")
    ctx.check(response.body()[:4] == b"%PDF", "File content starts with the PDF signature")
    ctx.check(len(response.body()) > 3000, f"PDF has content ({len(response.body()):,} bytes)")


@step("Guest assessment", "\"Ask AI\" explains a recommendation",
      "The button under a recommendation asks the assistant about that exact item.")
def ask_ai(ctx):
    ctx.go("/result")
    ctx.page.locator(".recommendations-section .ask-ai-btn").first.click()
    box = ctx.page.locator(".recommendations-section .ai-response-container").first
    box.wait_for(state="visible", timeout=30000)
    ctx.page.wait_for_function(
        "el => el.innerText.trim().length > 40 && !/thinking|loading/i.test(el.innerText)",
        arg=box.element_handle(), timeout=30000)
    ctx.check(len(box.inner_text().strip()) > 40 and "went wrong" not in box.inner_text(),
              "An explanation appears under the recommendation", box.inner_text()[:80])
    box.scroll_into_view_if_needed()


# ----------------------------------------------------------------------------------------
# C. Assistant
# ----------------------------------------------------------------------------------------

def _ask(ctx, question):
    before = ctx.page.locator(".chat-messages .message").count()
    ctx.page.fill("#user-input", question)
    ctx.page.click("button:has-text('Send')")
    ctx.page.wait_for_function(
        "n => document.querySelectorAll('.chat-messages .message').length >= n + 2 && !document.querySelector('.typing-indicator')",
        arg=before, timeout=30000)
    return ctx.page.locator(".chat-messages .message").last.inner_text()


@step("Assistant", "The assistant answers a cybersecurity question",
      "Owners can ask plain-English questions about the safeguards.")
def assistant_answers(ctx):
    ctx.go("/assistant")
    reply = _ask(ctx, "What is MFA?")
    ctx.check("authentication" in reply.lower(), "Reply explains multi-factor authentication", reply[:80])
    if not ctx.live_ai:
        ctx.check(True, "Offline run: the rule-based assistant answered (GPT-4o-mini not called)")


@step("Assistant", "Off-topic questions are refused",
      "Guardrail: the assistant only discusses cybersecurity. Needs --live-ai because the topic "
      "check is done by GPT-4o-mini.", needs_live_ai=True)
def assistant_refuses(ctx):
    ctx.go("/assistant")
    reply = _ask(ctx, "Can you give me a good lasagne recipe?")
    ctx.check("only answer questions" in reply or "not able to help" in reply, "The assistant declines", reply[:80])


# ----------------------------------------------------------------------------------------
# D. Accounts and score history
# ----------------------------------------------------------------------------------------

def _register(ctx, email, password, consent=True):
    ctx.go("/register")
    ctx.page.fill("#email", email)
    ctx.page.fill("#password", password)
    if consent:
        ctx.page.check("#privacy_consent")
    ctx.submit_and_wait(".auth-form button[type=submit]")


def _login(ctx, email, password):
    ctx.go("/login")
    ctx.page.fill("#email", email)
    ctx.page.fill("#password", password)
    ctx.submit_and_wait(".auth-form button[type=submit]")


def _logout(ctx):
    if ctx.logged_in():
        ctx.submit_and_wait("form[action='/logout'] button")


@step("Accounts", "Short passwords are refused",
      "Passwords must be at least 15 characters (NIST SP 800-63B guidance).")
def short_password(ctx):
    ctx.go("/register")
    ctx.page.fill("#email", EMAIL)
    ctx.page.evaluate("document.getElementById('password').removeAttribute('minlength')")
    ctx.page.fill("#password", "short-pass")
    ctx.page.check("#privacy_consent")
    ctx.submit_and_wait(".auth-form button[type=submit]")
    ctx.check("at least 15 characters" in ctx.text(), "Server refuses it: \"at least 15 characters\"")
    ctx.check(not ctx.logged_in(), "No account is created")


@step("Accounts", "Passwords found in data breaches are refused",
      "The breach check (Have I Been Pwned, k-anonymity) blocks known-leaked passwords.")
def breached_password(ctx):
    _register(ctx, EMAIL, BREACHED_PASSWORD)
    ctx.check("known data breaches" in ctx.text(), "Server refuses it: \"appeared in known data breaches\"")
    ctx.check(not ctx.logged_in(), "No account is created")


@step("Accounts", "Registering requires privacy consent",
      "Consent is checked by the server, not only by the browser.")
def consent_required(ctx):
    ctx.go("/register")
    ctx.page.fill("#email", EMAIL)
    ctx.page.fill("#password", PASSWORD)
    ctx.page.evaluate("document.getElementById('privacy_consent').removeAttribute('required')")
    ctx.submit_and_wait(".auth-form button[type=submit]")
    ctx.check("accept the privacy notice" in ctx.text(), "Server refuses it without consent")
    ctx.check(not ctx.logged_in(), "No account is created")


@step("Accounts", "Registering saves the guest result to history",
      "A result taken as a guest is saved only when the owner creates an account or logs in.")
def register_saves(ctx):
    _register(ctx, EMAIL, PASSWORD)
    ctx.check(ctx.logged_in(), "The new account is signed in")
    ctx.check("Saved to your score history" in ctx.text(), "Result page confirms it was saved")
    ctx.go("/history")
    rows = ctx.page.locator(".history-table tbody tr").count()
    ctx.check(rows >= 1, "History lists the saved attempt")
    ctx.check(f"{ctx.remember['first_score']}/100" in ctx.text(".history-table"),
              f"History shows the earlier guest score of {ctx.remember['first_score']}/100")


@step("Accounts", "A second assessment shows progress since the first",
      "Signed-in owners see the change in score and a trend line.")
def second_attempt(ctx):
    expected = calculate_assessment(SECOND)
    delta = expected["score"] - ctx.remember["first_score"]
    ctx.go("/assessment")
    ctx.answer_core(SECOND)
    ctx.submit_and_wait("#submitAssessment")
    banner = ctx.text(".account-banner")
    word = "Up" if delta > 0 else "Down" if delta < 0 else "No change"
    ctx.check(word in banner and (delta == 0 or f"{abs(delta)} points" in banner),
              f"Banner shows the change: {word} {abs(delta)} points", banner[:120])
    ctx.go("/history")
    ctx.check(ctx.page.locator(".history-table tbody tr").count() == 2, "History now lists 2 attempts")
    ctx.check(ctx.page.locator("#scoreHistoryChart").count() == 1, "The trend chart is drawn")


@step("Accounts", "Logging out ends the session",
      "After logging out, history is no longer reachable.")
def logout(ctx):
    _logout(ctx)
    ctx.check(not ctx.logged_in(), "Navigation shows Log in again")
    ctx.go("/history")
    ctx.check("/login" in ctx.page.url, "Opening history sends the visitor to the login page")


@step("Accounts", "A wrong password is refused",
      "The message does not reveal whether the email has an account.")
def wrong_password(ctx):
    _login(ctx, EMAIL, "not the right password at all")
    ctx.check("Email or password is incorrect" in ctx.text(), "Shows \"Email or password is incorrect\"")
    ctx.check(not ctx.logged_in(), "Not signed in")


@step("Accounts", "Logging in brings back the saved history",
      "History is stored in the database, not in the browser.")
def login_again(ctx):
    _login(ctx, EMAIL, PASSWORD)
    ctx.check(ctx.logged_in(), "Signed in")
    ctx.go("/history")
    ctx.check(ctx.page.locator(".history-table tbody tr").count() == 2, "Both earlier attempts are listed")


# ----------------------------------------------------------------------------------------
# E. Tailored assessment (Sprint 2)
# ----------------------------------------------------------------------------------------

def _expected_card(intake, description_sector=None):
    outcome = classify_business(intake, description_sector)
    return outcome, f"{round(outcome['confidence'] * 100)}%"


@step("Tailored assessment", "All four business questions must be answered",
      "The suggestion is only made from a complete set of answers.")
def intake_validation(ctx):
    ctx.go("/tailored")
    ctx.page.check("#activity-sell")
    ctx.page.evaluate("document.querySelectorAll('input[type=radio]').forEach(i => i.removeAttribute('required'))")
    ctx.submit_and_wait(".assessment-submit-card button[type=submit]")
    ctx.check("answer all four questions" in ctx.text(), "Server asks for all four answers")


@step("Tailored assessment", "Clear answers: suggested type with its confidence",
      "Confidence is the share of points from the four answers that went to the leading type.")
def clear_card(ctx):
    outcome, percent = _expected_card(RETAIL)
    ctx.intake(RETAIL)
    card = ctx.text(".suggestion-card")
    ctx.check(outcome["state"] == "clear", "Rules predict a clear result for these answers")
    ctx.check("SUGGESTED BUSINESS TYPE" in card.upper() and "Retail" in card, "Card suggests Retail")
    ctx.check(percent in card, f"Card shows {percent} confidence, as the rules predict")
    ctx.check(ctx.page.is_checked("#sector-retail"), "Retail is pre-selected; the owner can still change it")


@step("Tailored assessment", "A description that agrees is shown as a cross-check",
      "The description never changes the points or the percentage.")
def description_agrees(ctx):
    outcome, percent = _expected_card(HOSPITALITY, "hospitality")
    ctx.intake(HOSPITALITY, "We serve Korean cuisine to customers")
    card = ctx.text(".suggestion-card")
    ctx.check(percent in card, f"Confidence is still {percent}")
    ctx.check("also reads as" in card, "Card says the description also reads as Hospitality")


@step("Tailored assessment", "A description that disagrees is flagged, not obeyed",
      "Free text is the least reliable input, so it cannot override the answers.")
def description_differs(ctx):
    outcome, percent = _expected_card(RETAIL, "hospitality")
    ctx.intake(RETAIL, "We also run a small coffee bar and restaurant")
    card = ctx.text(".suggestion-card")
    ctx.check(percent in card and "Retail" in card, f"Card still suggests Retail at {percent}")
    ctx.check("differs from your answers" in card, "Card warns that the description differs")


@step("Tailored assessment", "Split answers: closest match, nothing pre-selected",
      "Below 60% (or a tie) the owner chooses; the tool does not guess for them.")
def close_card(ctx):
    outcome, percent = _expected_card(SPLIT)
    ctx.intake(SPLIT)
    card = ctx.text(".suggestion-card")
    ctx.check(outcome["state"] == "close", "Rules predict a close result for these answers")
    ctx.check("CLOSEST MATCH" in card.upper() and percent in card, f"Card shows Closest match at {percent}")
    ctx.check(ctx.page.locator("input[name=sector]:checked").count() == 0, "No business type is pre-selected")


@step("Tailored assessment", "Description only: Low confidence and the reasoning",
      "When all four answers are \"Not sure\", no percentage is invented; the card shows how the "
      "description was read and which words support it.")
def description_only(ctx):
    ctx.intake(UNSURE, "We run a small restaurant and coffee bar")
    card = ctx.text(".suggestion-card")
    ctx.check("FROM YOUR DESCRIPTION ONLY" in card.upper() and "Hospitality" in card, "Card offers Hospitality from the description")
    ctx.check("Low" in ctx.page.inner_text(".confidence-chip"), "Confidence chip says Low, not a percentage")
    ctx.check("restaurant" in card and "coffee" in card, "Card lists the words that support it")
    ctx.check(ctx.page.locator("input[name=sector]:checked").count() == 0, "Nothing is pre-selected")


@step("Tailored assessment", "Nothing to go on: no match, standard questions offered",
      "The card is always shown but never fakes a suggestion.")
def no_match(ctx):
    ctx.intake(UNSURE)
    card = ctx.text(".suggestion-card")
    ctx.check("NO MATCH FOUND" in card.upper(), "Card says no match was found")
    ctx.check("None" in ctx.page.inner_text(".confidence-chip"), "Confidence chip says None")
    ctx.check(ctx.page.locator("#sector-core").count() == 1, "\"None of these fit\" leads to the standard questions")


@step("Tailored assessment", "Full tailored run: core and sector scores kept separate",
      "Sector questions add a separate score; the core score is unchanged, so it stays comparable "
      "with the validated 20-question instrument.")
def tailored_run(ctx):
    sector = get_sector("retail")
    sector_answers = {q["id"]: ("yes" if i < 3 else "no") for i, q in enumerate(sector["questions"])}
    core = calculate_assessment(MIXED)
    expected_sector = calculate_sector("retail", sector_answers)
    ctx.intake(RETAIL)
    ctx.submit_and_wait("form[action='/tailored/confirm'] button[type=submit]")
    ctx.check("/tailored/assessment" in ctx.page.url, "Confirming Retail opens the tailored questions")
    ctx.answer_core(MIXED)
    ctx.answer(sector_answers)
    ctx.submit_and_wait("#submitAssessment")
    ctx.check(ctx.page.inner_text(".kpi-primary strong").startswith(str(core["score"])),
              f"Core score is {core['score']}/100, the same as the guest run with the same answers")
    body = ctx.text()
    ctx.check(f"{expected_sector['score']}%" in body and "Retail questions" in body,
              f"Retail questions show a separate {expected_sector['score']}%")
    ctx.check("25" in ctx.page.locator(".kpi-card").nth(1).inner_text(), "Questions reviewed counts 20 core + 5 sector")
    ctx.check("Based on:" in ctx.text(".sector-checklist"), "Each sector question shows its framework sources")
    ctx.go("/history")
    table = ctx.text(".history-table")
    ctx.check("Retail" in table and f"{expected_sector['score']}%" in table, "History records the business type and sector score")


@step("Tailored assessment", "Sources page traces every question to a framework",
      "Answers the panel question \"where do the questions come from?\" for all 40 questions.")
def sources_page(ctx):
    ctx.go("/tailored/sources")
    body = ctx.text()
    ctx.check("The 20 core questions" in body, "Core questions are listed")
    ctx.check(ctx.page.locator(".function-tag").count() >= 20, "Each core question shows its NIST CSF 2.0 function")
    for framework in ("NIST CSF 2.0", "Essential Eight", "ACSC small business guide", "PCI DSS v4.0.1", "Privacy Act 1988"):
        ctx.check(framework in body, f"{framework} is cited")
    ctx.page.click(".sources-jump a:has-text('Hospitality')")
    ctx.check(ctx.page.url.endswith("#sector-2"), "Jump links move to each business type")


# ----------------------------------------------------------------------------------------
# F. Security
# ----------------------------------------------------------------------------------------

@step("Security", "Forms without a CSRF token are rejected",
      "Stops other websites from submitting forms on the owner's behalf.")
def csrf(ctx):
    response = ctx.page.request.post(ctx.base + "/login", form={"email": EMAIL, "password": PASSWORD})
    ctx.check(response.status == 400, "Login without a token returns HTTP 400", f"got {response.status}")
    response = ctx.page.request.post(ctx.base + "/account/delete", form={"password": PASSWORD})
    ctx.check(response.status == 400, "Account deletion without a token returns HTTP 400", f"got {response.status}")


@step("Security", "Repeated wrong passwords are slowed down",
      "After 5 failed sign-ins for one email within 15 minutes, further attempts are blocked.")
def rate_limit(ctx):
    _logout(ctx)
    target = "limit.e2e@example.com"
    for attempt in range(5):
        _login(ctx, target, f"wrong password number {attempt}")
    ctx.check("Email or password is incorrect" in ctx.text(), "The first 5 attempts are simply refused")
    _login(ctx, target, "wrong password number 6")
    ctx.check("Too many sign-in attempts" in ctx.text(), "The 6th attempt is blocked for 15 minutes")


@step("Security", "Account deletion needs the password and removes everything",
      "Owners can delete their account and history themselves (Privacy Act, APP 11.2).")
def delete_account(ctx):
    _login(ctx, EMAIL, PASSWORD)
    ctx.go("/history")
    ctx.page.click(".account-delete summary")
    ctx.page.fill("#delete_password", "not my password at all")
    ctx.submit_and_wait(".account-delete-form button[type=submit]")
    ctx.check(ctx.page.is_visible(".account-delete .form-error"), "The error is visible without reopening the panel")
    ctx.check("Password did not match" in ctx.text(), "A wrong password does not delete the account")
    ctx.page.fill("#delete_password", PASSWORD)
    ctx.submit_and_wait(".account-delete-form button[type=submit]")
    ctx.check(not ctx.logged_in(), "After deletion the owner is signed out")
    _login(ctx, EMAIL, PASSWORD)
    ctx.check("Email or password is incorrect" in ctx.text(), "The deleted account can no longer log in")


# ----------------------------------------------------------------------------------------
# G. Layout and quality
# ----------------------------------------------------------------------------------------

@step("Layout", "Pages fit a phone screen",
      "At 390 px wide (an iPhone) no page should scroll sideways.")
def phone_layout(ctx):
    ctx.page.set_viewport_size({"width": 390, "height": 844})
    try:
        for path in ("/", "/assessment", "/tailored", "/assistant", "/login", "/register", "/privacy", "/tailored/sources", "/result"):
            ctx.go(path)
            overflow = ctx.page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            ctx.check(overflow <= 1, f"{path} fits the screen", f"{overflow}px too wide")
        ctx.intake(RETAIL)
        overflow = ctx.page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        ctx.check(overflow <= 1, "/tailored/confirm (suggestion card) fits the screen", f"{overflow}px too wide")
    finally:
        ctx.page.set_viewport_size({"width": 1280, "height": 860})


@step("Layout", "No errors in the browser console",
      "JavaScript errors would mean a broken chart, button or form somewhere in the run.")
def console_clean(ctx):
    # 4xx responses are expected: several steps submit invalid forms on purpose.
    expected = "the server responded with a status of 4"
    errors = [e for e in ctx.console_errors if "favicon" not in e and expected not in e]
    ctx.check(not errors, "No JavaScript or loading errors across all pages visited", "; ".join(errors[:3]))
    ctx.check(True, f"{len(ctx.console_errors) - len(errors)} expected HTTP 4xx responses from the refused forms were ignored")


# ----------------------------------------------------------------------------------------
# Runner and report
# ----------------------------------------------------------------------------------------

CAPTION_SCRIPT = r"""
(() => {
  const draw = () => {
    let data;
    try { data = JSON.parse(sessionStorage.getItem("e2e-caption") || "null"); } catch (e) { data = null; }
    if (!data || !document.body) return;
    let box = document.getElementById("e2e-caption");
    if (!box) {
      box = document.createElement("div");
      box.id = "e2e-caption";
      box.setAttribute("aria-hidden", "true");
      box.style.cssText = "position:fixed;left:12px;bottom:12px;z-index:2147483647;pointer-events:none;" +
        "width:min(460px,calc(100vw - 24px));box-sizing:border-box;background:rgba(15,36,62,.94);color:#fff;" +
        "border-radius:12px;padding:12px 14px;font:13px/1.4 system-ui,-apple-system,Segoe UI,sans-serif;" +
        "box-shadow:0 8px 30px rgba(0,0,0,.3)";
      document.body.appendChild(box);
    }
    const esc = s => String(s).replace(/[&<>]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;"}[c]));
    const checks = data.checks.slice(-5).map(c =>
      `<div style="color:${c.ok ? "#86efac" : "#fca5a5"}">${c.ok ? "&#10003;" : "&#10007;"} ${esc(c.text)}</div>`).join("");
    box.innerHTML = `<div style="opacity:.75;font-size:11px;letter-spacing:.05em;text-transform:uppercase">` +
      `Step ${data.number} of ${data.total} &middot; ${esc(data.group)}</div>` +
      `<div style="font-weight:700;font-size:15px;margin:2px 0 4px">${esc(data.title)}</div>` +
      `<div style="opacity:.85;margin-bottom:6px">${esc(data.purpose)}</div>${checks}`;
  };
  window.__e2eDraw = draw;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", draw); else draw();
})();
"""


class DemoMode:
    """Slows the run down for people watching: a caption box, highlighted targets and pauses."""

    def __init__(self, page, total, step_by_step, check_pause=0.9, step_pause=2.5):
        self.page, self.total, self.step_by_step = page, total, step_by_step
        self.check_pause, self.step_pause = check_pause, step_pause
        page.context.add_init_script(CAPTION_SCRIPT)
        for name in ("click", "check", "fill"):
            original = getattr(page, name)
            setattr(page, name, self._highlighting(original))

    def _highlighting(self, action):
        def run(selector, *args, **kwargs):
            try:
                self.page.locator(selector).first.evaluate(
                    "el => { el.scrollIntoView({block: 'center', behavior: 'smooth'});"
                    " const old = el.style.outline; el.style.outline = '3px solid #f59e0b'; el.style.outlineOffset = '3px';"
                    " setTimeout(() => { el.style.outline = old; }, 1200); }", timeout=2000)
                time.sleep(0.35)
            except Exception:
                pass
            return action(selector, *args, **kwargs)
        return run

    def show(self, step):
        data = {"number": step.number, "total": self.total, "group": step.group, "title": step.title,
                "purpose": step.purpose, "checks": [{"ok": ok, "text": text} for ok, text, _ in step.checks]}
        try:
            self.page.evaluate("d => { sessionStorage.setItem('e2e-caption', JSON.stringify(d)); window.__e2eDraw && window.__e2eDraw(); }", data)
        except Exception:
            pass

    def start(self, step):
        if self.step_by_step:
            input(f"\nPress Enter to run step {step.number}: {step.title} ")
        self.show(step)
        self.pause(1.5)

    def pause(self, seconds):
        time.sleep(seconds)

    def hide_for_screenshot(self, hidden):
        try:
            self.page.evaluate("h => { const b = document.getElementById('e2e-caption'); if (b) b.style.display = h ? 'none' : ''; }", hidden)
        except Exception:
            pass


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for(url, seconds=30):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.3)
    return False


BROWSERS = {"chromium": "Chromium (Chrome, Edge)", "firefox": "Firefox", "webkit": "WebKit (Safari)",
            "chrome": "Google Chrome (installed)"}
ENGINES = ["chromium", "firefox", "webkit"]  # what --browsers all means


def write_results(path, steps, started, finished, live_ai, browser_version, browser):
    """Machine-readable results, used to build the cross-browser summary."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({
            "browser": browser, "version": browser_version, "live_ai": live_ai,
            "started": started.isoformat(), "seconds": (finished - started).total_seconds(),
            "steps": [{"number": s.number, "group": s.group, "title": s.title, "status": s.status,
                       "error": s.error, "checks": len(s.checks)} for s in steps],
        }, handle, indent=2)


def write_summary(path, runs, started, finished, live_ai):
    """One page comparing every step across browsers, linking to each browser's full report."""
    browsers = [run["browser"] for run in runs]
    steps = runs[0]["steps"] if runs else []
    failed = sum(1 for run in runs for s in run["steps"] if s["status"] == "failed")
    head = "".join(f'<th>{html.escape(BROWSERS[b])}<small>{html.escape(r.get("version", ""))}</small></th>'
                   for b, r in zip(browsers, runs))
    body, group = [], None
    for index, step_row in enumerate(steps):
        if step_row["group"] != group:
            group = step_row["group"]
            body.append(f'<tr class="group"><td colspan="{len(browsers) + 1}">{html.escape(group)}</td></tr>')
        cells = []
        for run in runs:
            s = run["steps"][index]
            title = html.escape(s["error"]) if s["error"] else f'{s["checks"]} checks'
            cells.append(f'<td><a class="badge {s["status"]}" title="{title}" href="{run["browser"]}/index.html#step-{s["number"]}">'
                         f'{s["status"].upper()}</a></td>')
        body.append(f'<tr><td><span class="num">{step_row["number"]}</span>{html.escape(step_row["title"])}</td>{"".join(cells)}</tr>')
    totals = "".join(
        f'<div class="tile {"fail" if any(s["status"] == "failed" for s in r["steps"]) else "pass"}"><span>{html.escape(BROWSERS[r["browser"]])}</span>'
        f'<strong>{sum(s["status"] == "passed" for s in r["steps"])}/{len(r["steps"])}</strong>'
        f'<a href="{r["browser"]}/index.html">Full report with screenshots</a></div>' for r in runs)
    verdict = "All browsers passed" if failed == 0 else f"{failed} failed step result{'s' if failed != 1 else ''}"
    mode = "Live AI" if live_ai else "Offline (no OpenAI calls)"
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CyberShield SMB cross-browser report</title><style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f5f8fc;color:#172b4d}}
header{{background:#0f4c81;color:#fff;padding:28px 32px}}header h1{{margin:0 0 6px;font-size:1.6rem}}header p{{margin:2px 0;opacity:.9}}
.summary{{display:flex;flex-wrap:wrap;gap:12px;padding:20px 32px 0}}.tile{{background:#fff;border:1px solid #dfe8f3;border-radius:12px;padding:12px 18px;min-width:180px}}
.tile strong{{display:block;font-size:1.6rem}}.tile.pass strong{{color:#1c7c4a}}.tile.fail strong{{color:#b42318}}.tile a{{font-size:.82rem;color:#0f4c81}}
main{{padding:16px 32px 40px;max-width:1100px}}.wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;background:#fff;border:1px solid #dfe8f3;border-radius:12px}}
th,td{{padding:8px 12px;border-bottom:1px solid #edf1f6;text-align:left;font-size:.9rem;vertical-align:middle}}th small{{display:block;font-weight:400;color:#73849a;font-size:.72rem}}
td:not(:first-child),th:not(:first-child){{text-align:center;width:150px}}tr.group td{{background:#f0f5fb;color:#0f4c81;font-weight:700}}
.num{{background:#e8f0fb;color:#0f4c81;border-radius:6px;padding:1px 7px;font-weight:700;font-size:.78rem;margin-right:8px}}
.badge{{display:inline-block;font-size:.7rem;font-weight:700;border-radius:6px;padding:3px 9px;text-decoration:none}}.badge.passed{{background:#edf8f1;color:#1c7c4a}}
.badge.failed{{background:#fdecea;color:#b42318}}.badge.skipped,.badge.not{{background:#fff4e0;color:#8a5a00}}
@media (max-width:800px){{main,.summary,header{{padding-left:16px;padding-right:16px}}}}
</style></head><body><header><h1>CyberShield SMB 2.0 &mdash; cross-browser end-to-end report</h1>
<p><strong>{verdict}.</strong> The same {len(steps)}-step journey ran in {len(runs)} browser engines at the same time, each against its own copy of the app and an empty database.</p>
<p>Run {started:%d %B %Y, %H:%M:%S} &middot; {(finished - started).total_seconds():.0f} seconds in total &middot; Mode: {mode}</p></header>
<div class="summary">{totals}</div><main><p>Click a result to open that step, with its checks and screenshot, in the browser's full report.</p>
<div class="wrap"><table><thead><tr><th>Step</th>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div></main></body></html>'''
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(page)


def write_report(path, steps, started, finished, live_ai, browser_version):
    passed = sum(s.status == "passed" for s in steps)
    failed = sum(s.status == "failed" for s in steps)
    skipped = sum(s.status == "skipped" for s in steps)
    checks = sum(len(s.checks) for s in steps)
    rows, group = [], None
    for s in steps:
        if s.group != group:
            group = s.group
            rows.append(f'<h2>{html.escape(group)}</h2>')
        items = "".join(
            f'<li class="{"ok" if ok else "bad"}">{"&#10003;" if ok else "&#10007;"} {html.escape(text)}'
            f'{f" <small>({html.escape(detail)})</small>" if detail and not ok else ""}</li>'
            for ok, text, detail in s.checks)
        if s.status == "skipped":
            items += f'<li class="skip">Skipped: {html.escape(s.error)}</li>'
        elif s.error and not any(not ok for ok, _, _ in s.checks):
            items += f'<li class="bad">&#10007; {html.escape(s.error)}</li>'
        shot = (f'<a href="{s.screenshot}" target="_blank"><img src="{s.screenshot}" alt="Screenshot after step {s.number}" loading="lazy"></a>'
                if s.screenshot else "")
        rows.append(f'''<section class="step {s.status}" id="step-{s.number}">
  <div class="text"><div class="head"><span class="num">{s.number}</span><h3>{html.escape(s.title)}</h3>
  <span class="badge {s.status}">{s.status.upper()}</span><span class="time">{s.seconds:.1f}s</span></div>
  <p class="why">{html.escape(s.purpose)}</p><ul>{items}</ul></div>{shot}</section>''')
    mode = "Live AI (GPT-4o-mini called)" if live_ai else "Offline (no OpenAI calls; rule-based assistant and keyword stand-in)"
    verdict = "All steps passed" if failed == 0 else f"{failed} step{'s' if failed != 1 else ''} failed"
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CyberShield SMB end-to-end report</title><style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f5f8fc;color:#172b4d}}
header{{background:#0f4c81;color:#fff;padding:28px 32px}}header h1{{margin:0 0 6px;font-size:1.6rem}}header p{{margin:2px 0;opacity:.9}}
.summary{{display:flex;flex-wrap:wrap;gap:12px;padding:20px 32px 0}}.tile{{background:#fff;border:1px solid #dfe8f3;border-radius:12px;padding:12px 18px;min-width:120px}}
.tile strong{{display:block;font-size:1.6rem}}.tile.pass strong{{color:#1c7c4a}}.tile.fail strong{{color:#b42318}}.tile.skip strong{{color:#8a5a00}}
main{{padding:8px 32px 40px;max-width:1200px}}h2{{margin:28px 0 10px;font-size:1.15rem;color:#0f4c81}}
.step{{display:grid;grid-template-columns:1fr 340px;gap:18px;background:#fff;border:1px solid #dfe8f3;border-left:5px solid #1c7c4a;border-radius:12px;padding:16px 18px;margin-bottom:12px}}
.step.failed{{border-left-color:#b42318}}.step.skipped{{border-left-color:#d29b2b}}
.head{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}.head h3{{margin:0;font-size:1rem}}
.num{{background:#e8f0fb;color:#0f4c81;border-radius:8px;padding:2px 8px;font-weight:700;font-size:.85rem}}
.badge{{font-size:.7rem;font-weight:700;border-radius:6px;padding:2px 8px}}.badge.passed{{background:#edf8f1;color:#1c7c4a}}.badge.failed{{background:#fdecea;color:#b42318}}.badge.skipped{{background:#fff4e0;color:#8a5a00}}
.time{{color:#73849a;font-size:.8rem}}.why{{color:#5d6e84;font-size:.88rem;margin:8px 0}}ul{{margin:0;padding-left:0;list-style:none;font-size:.9rem}}li{{margin:3px 0}}
li.ok{{color:#1c5b38}}li.bad{{color:#b42318;font-weight:600}}li.skip{{color:#8a5a00}}small{{font-weight:400;color:#6c7f95}}
img{{width:100%;border:1px solid #dfe8f3;border-radius:8px}}@media (max-width:800px){{.step{{grid-template-columns:1fr}}main,.summary,header{{padding-left:16px;padding-right:16px}}}}
</style></head><body><header><h1>CyberShield SMB 2.0 &mdash; end-to-end test report</h1>
<p><strong>{verdict}.</strong> {passed} of {len(steps)} steps passed, {checks} individual checks.</p>
<p>Run {started:%d %B %Y, %H:%M:%S} &middot; {(finished - started).total_seconds():.0f} seconds &middot; {html.escape(browser_version)} &middot; Mode: {html.escape(mode)}</p></header>
<div class="summary"><div class="tile pass"><span>Passed</span><strong>{passed}</strong></div><div class="tile fail"><span>Failed</span><strong>{failed}</strong></div>
<div class="tile skip"><span>Skipped</span><strong>{skipped}</strong></div><div class="tile"><span>Checks</span><strong>{checks}</strong></div></div>
<main><p>Each step was performed in a real browser against a fresh copy of the app with an empty database. Expected scores and confidence values were
calculated from the same scoring rules the app uses, then compared with what appeared on screen. Click a screenshot to enlarge it.</p>
{"".join(rows)}</main></body></html>'''
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(page)


def main():
    parser = argparse.ArgumentParser(description="Run the CyberShield SMB browser end-to-end tests.")
    parser.add_argument("--headless", action="store_true", help="do not show the browser window")
    parser.add_argument("--slow", type=int, default=None, help="milliseconds to pause between actions (default 150 when visible)")
    parser.add_argument("--live-ai", action="store_true", help="call GPT-4o-mini for real using the key in .env")
    parser.add_argument("--no-open", action="store_true", help="do not open the report when finished")
    parser.add_argument("--browsers", default="chromium",
                        help="chromium, firefox, webkit, chrome (your installed Google Chrome), a comma-separated list, or all (default chromium)")
    parser.add_argument("--demo", action="store_true",
                        help="slow presentation pace with on-screen captions and highlighted clicks")
    parser.add_argument("--step", action="store_true", help="with --demo: wait for Enter before each step")
    parser.add_argument("--report-dir", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.step:
        args.demo = True
    if args.demo and args.headless:
        print("--demo is for watching, so it ignores --headless.")
        args.headless = False

    names = list(ENGINES) if args.browsers.strip().lower() == "all" else \
        [name.strip().lower() for name in args.browsers.split(",") if name.strip()]
    unknown = [name for name in names if name not in BROWSERS]
    if unknown or not names:
        print(f"Unknown browser: {', '.join(unknown) or '(none)'}. Choose from chromium, firefox, webkit or all.")
        return 2
    if len(names) > 1:
        if args.step:
            print("--step needs a single browser (it waits for your Enter key), so it is ignored here.")
            args.step = False
        return run_in_parallel(names, args)
    return run_one(names[0], args)


def run_in_parallel(names, args):
    """Start one copy of this script per browser, show their progress, then build the summary."""
    report_dir = os.path.join(HERE, "report")
    shutil.rmtree(report_dir, ignore_errors=True)
    os.makedirs(report_dir)
    started = datetime.now()
    children = []
    print(f"Running the journey in {', '.join(BROWSERS[n] for n in names)} at the same time ...\n")
    for name in names:
        command = [sys.executable, os.path.abspath(__file__), "--browsers", name, "--no-open",
                   "--report-dir", os.path.join(report_dir, name)]
        if args.headless:
            command.append("--headless")
        if args.live_ai:
            command.append("--live-ai")
        if args.slow is not None:
            command += ["--slow", str(args.slow)]
        if args.demo:
            command.append("--demo")
        children.append((name, subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                text=True, encoding="utf-8", errors="replace", bufsize=1)))

    import threading

    lock = threading.Lock()

    def relay(name, process):
        width = max(len(n) for n in names)
        for line in process.stdout:
            line = line.rstrip()
            if line.startswith("[") or "passed," in line or "not installed" in line.lower() or "Executable doesn't exist" in line:
                with lock:
                    print(f"{name:<{width}} | {line}")

    threads = [threading.Thread(target=relay, args=child, daemon=True) for child in children]
    for thread in threads:
        thread.start()
    codes = {name: process.wait() for name, process in children}
    for thread in threads:
        thread.join(timeout=5)
    finished = datetime.now()

    runs, missing = [], []
    for name in names:
        results = os.path.join(report_dir, name, "results.json")
        if os.path.exists(results):
            with open(results, encoding="utf-8") as handle:
                runs.append(json.load(handle))
        else:
            missing.append(name)
    if runs:
        write_summary(os.path.join(report_dir, "index.html"), runs, started, finished, args.live_ai)

    print()
    for run in runs:
        statuses = [s["status"] for s in run["steps"]]
        print(f"{BROWSERS[run['browser']]:<26} {statuses.count('passed')} passed, {statuses.count('failed')} failed, "
              f"{statuses.count('skipped')} skipped  ({run['seconds']:.0f}s)")
    for name in missing:
        fix = "install Google Chrome" if name == "chrome" else f"install it with: python -m playwright install {name}"
        print(f"{BROWSERS[name]:<26} did not run; {fix}")
    print(f"Total time {(finished - started).total_seconds():.0f}s. Report: {os.path.join(report_dir, 'index.html')}")
    if runs and not args.no_open and not args.headless:
        webbrowser.open("file://" + os.path.join(report_dir, "index.html"))
    return 0 if not missing and all(code == 0 for code in codes.values()) else 1


def run_one(browser_name, args):

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Run:\n  pip install -r requirements-dev.txt\n  python -m playwright install chromium")
        return 2

    report_dir = args.report_dir or os.path.join(HERE, "report")
    shutil.rmtree(report_dir, ignore_errors=True)
    os.makedirs(os.path.join(report_dir, "screenshots"))
    work = tempfile.mkdtemp(prefix="cybershield-e2e-")
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    server_log = open(os.path.join(report_dir, "server.log"), "w")
    command = [sys.executable, os.path.join(HERE, "server.py"), "--port", str(port), "--db", os.path.join(work, "e2e.sqlite")]
    if args.live_ai:
        command.append("--live-ai")

    print(f"Starting CyberShield SMB at {base} (temporary database, {'live AI' if args.live_ai else 'offline'}) ...")
    server = subprocess.Popen(command, cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
    started = datetime.now()
    try:
        if not wait_for(base + "/"):
            print(f"The app did not start. See {os.path.join(report_dir, 'server.log')}")
            return 2
        with sync_playwright() as playwright:
            try:
                default_slow = 0 if args.headless else (500 if args.demo else 150)
                options = {"headless": args.headless, "slow_mo": args.slow if args.slow is not None else default_slow}
                if browser_name == "chrome":
                    # The Google Chrome already installed on this computer; nothing to download.
                    browser = playwright.chromium.launch(channel="chrome", **options)
                else:
                    browser = getattr(playwright, browser_name).launch(**options)
            except Exception as error:
                fix = ("install Google Chrome from google.com/chrome" if browser_name == "chrome"
                       else f"install it with: python -m playwright install {browser_name}")
                print(f"{BROWSERS[browser_name]} is not installed or could not start; {fix}\n{str(error).splitlines()[0]}")
                return 2
            version = f"{BROWSERS[browser_name].split(' (')[0]} {browser.version}"
            context = browser.new_context(viewport={"width": 1280, "height": 860}, accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(15000)
            demo = DemoMode(page, len(STEPS), args.step) if args.demo else None
            ctx = Context(page, base, None, args.live_ai, demo)
            page.on("console", lambda m: ctx.console_errors.append(f"{page.url}: {m.text}") if m.type == "error" else None)
            page.on("dialog", lambda d: d.dismiss())
            total = len(STEPS)
            print(f"Running {total} steps in {version}{' (headless)' if args.headless else ''}\n")
            for s in STEPS:
                ctx.current = s
                if demo and not (s.needs_live_ai and not args.live_ai):
                    demo.start(s)
                begin = time.time()
                if s.needs_live_ai and not args.live_ai:
                    s.status, s.error = "skipped", "needs --live-ai (the check is made by GPT-4o-mini)"
                else:
                    try:
                        s.func(ctx)
                        s.status = "passed"
                    except StepFailed as failure:
                        s.status, s.error = "failed", str(failure)
                    except Exception as failure:  # an unexpected page state is also a failure
                        s.status, s.error = "failed", f"{type(failure).__name__}: {str(failure).splitlines()[0][:200]}"
                        traceback.print_exc(file=server_log)
                    name = f"screenshots/{s.number:02d}.png"
                    if demo:
                        demo.hide_for_screenshot(True)
                    try:
                        page.screenshot(path=os.path.join(report_dir, name))
                        s.screenshot = name
                    except Exception:
                        pass
                    if demo:
                        demo.hide_for_screenshot(False)
                        demo.pause(demo.step_pause)
                s.seconds = time.time() - begin
                mark = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP"}[s.status]
                print(f"[{s.number:2d}/{total}] {mark}  {s.group}: {s.title}  ({s.seconds:.1f}s)")
                for ok, text, detail in s.checks:
                    print(f"          {'✓' if ok else '✗'} {text}{f'  <- {detail}' if detail and not ok else ''}")
                if s.status != "passed" and s.error and not any(not ok for ok, _, _ in s.checks):
                    print(f"          {'-' if s.status == 'skipped' else '✗'} {s.error}")
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
        server_log.close()
        shutil.rmtree(work, ignore_errors=True)

    finished = datetime.now()
    report = os.path.join(report_dir, "index.html")
    write_report(report, STEPS, started, finished, args.live_ai, version)
    write_results(os.path.join(report_dir, "results.json"), STEPS, started, finished, args.live_ai, version, browser_name)
    failed = [s for s in STEPS if s.status == "failed"]
    passed = sum(s.status == "passed" for s in STEPS)
    print(f"\n{passed} passed, {len(failed)} failed, {sum(s.status == 'skipped' for s in STEPS)} skipped "
          f"({sum(len(s.checks) for s in STEPS)} checks) in {(finished - started).total_seconds():.0f}s")
    print(f"Report: {report}")
    if not args.no_open and not args.headless:
        webbrowser.open("file://" + report)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
