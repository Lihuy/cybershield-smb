# 🛡️ CyberShield SMB

**An AI-powered cybersecurity companion for Australian small businesses**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://cybershield-smb.onrender.com)

### 🌐 [**Try it live → cybershield-smb.onrender.com**](https://cybershield-smb.onrender.com)

> Hosted on Render's free tier

---

## 📖 About

CyberShield SMB is a web-based cybersecurity self-assessment tool built for Australian small and medium businesses (SMBs). It helps business owners understand their cybersecurity posture, see where their biggest gaps are, and get plain-English next steps — no technical background required.

Business owners work through a 20-question assessment and get:

- A security score and risk level (Low / Medium / High / Critical) across six categories
- A prioritised action plan, ordered Critical → High → Medium
- An AI cybersecurity assistant that answers follow-up questions in plain English
- A downloadable PDF report of their results

**🎯 Why CyberShield SMB?**

- **Plain English, not jargon** — written for business owners, not IT staff
- **AI-powered guidance** — the assistant explains _why_ each recommendation matters, in context
- **Guest or registered use** — guests can start immediately with no sign-up; registered users can save assessment history and review score trends
- **Transparent scoring** — every score is a simple, explainable rule (no black-box ML)

---

## ✨ Features

### 🧩 Core Assessment

- **20 questions across 6 categories**: Identity & Access, Device Security, Network Security, Email Security, Backup & Recovery, and Employee Awareness (4/4/3/3/3/3 questions respectively)
- Each question carries a Critical / High / Medium priority weighting and a plain-English explanation

### 📊 Results Dashboard

- **Overall score** out of 100, with a LOW/MEDIUM/HIGH/CRITICAL risk band (thresholds at 80/60/40)
- **Category performance bars** plus a **Chart.js radar chart** comparing all six categories at a glance
- **Executive summary** highlighting your strongest and weakest areas
- **Prioritised action plan**, sorted Critical → High → Medium

### 🤖 AI-Powered Assistant

- **Two-tier design**: a transparent rule-based assistant (`ai/assistant.py`) that always works offline, backed by a full OpenAI GPT-4o-mini integration (`ai/openai_assistant.py`) when the API is available
- **Topic-restricted**: a GPT-4o-mini classifier checks every question is actually about cybersecurity before answering
- **OpenAI Moderation API** screens messages before they reach the model
- **Inline "Ask AI"** on every recommendation, explaining what it means and why it matters for your business — each answer is cached client-side so re-opening a recommendation doesn't re-call the API
- **Automatic fallback**: if the OpenAI API fails, responses fall back to the rule-based assistant rather than erroring out

### 📄 Reporting

- **Downloadable PDF report** (built with ReportLab) summarising your score, category breakdown, and action plan

### 🔒 Privacy

- **Guest results stay session-based** — the original assessment remains available without creating an account
- **Account history stores aggregate results** — registered accounts store the email, assessment date, overall score, risk tier, category scores and recommendations; raw question answers are not written to the database
- **Account deletion** — users can delete their account and its saved assessment history from the history page
- **Password handling** — passwords are hashed; registration requires at least 15 characters and checks a partial hash against Have I Been Pwned using its k-anonymity range API
- **Tailored assessment (2.0)** — four intake questions suggest one of four business types (retail, hospitality, trades, professional services) using transparent point rules, with a confidence value and the reasons shown; the user confirms, changes or skips the suggestion. A short, predefined question set for that type is added to the unchanged 20 core questions and scored separately. Low-confidence results ask the user to choose or continue with the core questions only
- **Privacy notice** — a plain-English notice at `/privacy` explains what is stored; the accepted notice version is recorded at registration
- **AI spend controls** — the assistant endpoint is limited per visitor and per day; once a limit is reached it answers from the offline rule-based assistant

---

## 🛠️ Tech Stack

| Layer               | Technology                                                      |
| :------------------ | :-------------------------------------------------------------- |
| **Web framework**   | Flask 3.x + Jinja2 templates                                    |
| **Frontend**        | Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Google Fonts (Poppins) |
| **AI / LLM**        | OpenAI API (GPT-4o-mini) + OpenAI Moderation API                |
| **Risk scoring**    | Pure Python, rule-based (equal-weighted categories) — no ML     |
| **PDF generation**  | ReportLab                                                       |
| **Charts**          | Chart.js (radar chart)                                          |
| **Persistence**     | Flask session for guests; SQLAlchemy with SQLite locally and PostgreSQL by `DATABASE_URL` for registered history |

> **⚠️ Tech stack note:** the original Assessment 1/2 proposal specified **Streamlit + FastAPI**, with **scikit-learn** for risk scoring. During development the team moved to a **Flask monolith with pure-Python rule-based scoring** for faster iteration and simpler deployment. The AI assistant, questionnaire structure (20 questions / 6 categories), and prioritised-recommendations approach all remained as originally planned.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- An [OpenAI API key](https://platform.openai.com/api-keys)
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Lihuy/cybershield-smb.git
cd cybershield-smb

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # macOS/Linux
# or
venv\Scripts\activate              # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your environment variables
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### Running the App

```bash
python app.py
```

Visit `http://127.0.0.1:5000` in your browser.

> **Just want to see it working?** A live instance is already deployed at **<https://cybershield-smb.onrender.com>** — no setup or API key required.

---

## 📁 Project Structure

```
cybershield-smb/
├── ai/
│   ├── assistant.py           # Rule-based fallback assistant (works offline)
│   ├── openai_assistant.py    # OpenAI GPT-4o-mini integration, topic filter + moderation
│   └── business_classifier.py # Labels an optional business description (AI, with keyword fallback)
├── data/
│   ├── questions.py           # 20 core questions across 6 categories (unchanged since 1.0)
│   └── sectors.py             # Business types, intake questions, sector question sets (draft content)
├── database.py                # SQLAlchemy models (users, assessments, history, consent, rate limits)
├── engine/
│   ├── risk_engine.py         # Rule-based scoring: category scores, risk level, summary
│   ├── classifier.py          # Rule-based business-type classifier with confidence value
│   └── sector_engine.py       # Separate sector score and sector recommendations
├── static/
│   ├── css/
│   │   ├── style.css          # Core styles
│   │   └── account.css        # 2.0 additions: account banner, history, privacy page
│   └── images/
│       ├── cybershield-logo.svg
│       └── lock.svg
├── templates/
│   ├── base.html               # Shared layout, nav, Bootstrap/Chart.js includes
│   ├── home.html
│   ├── assessment.html
│   ├── result.html             # Dashboard: score, radar chart, action plan, Ask AI, save banner
│   ├── chatbot.html
│   ├── auth.html               # Register and log in (2.0)
│   ├── history.html            # Score history, trend chart, account deletion (2.0)
│   ├── privacy.html            # Privacy notice (2.0)
│   └── tailored_*.html         # Tailored assessment: intake, confirm, questions (2.0)
├── tests/                      # pytest suite: guest regression, accounts, assistant, tailored assessment
├── e2e/                        # Browser end-to-end tests: run_e2e.py drives every feature and writes a report
├── .github/workflows/tests.yml # Runs both test suites on every push to GitHub
├── utils/
│   └── recommendations.py     # Builds the prioritised action plan from unanswered items
├── .env.example
├── app.py                      # Flask application entry point and routes
├── render.yaml                 # Render deployment settings
├── requirements.txt
├── requirements-dev.txt        # Adds pytest and Playwright
└── README.md
```

---

## 🧪 Usage Guide

### 1. Take the assessment

Click **"Start assessment"**, answer the 20 Yes/No questions, and submit.

### 2. Review your dashboard

See your overall score, risk level, the radar chart comparing all six categories, and your prioritised action plan.

### 3. Ask the AI assistant

Use **"Ask AI"** in the navigation for open-ended cybersecurity questions, or click **"Ask AI"** on any individual recommendation on your results page for a contextual explanation.

### 4. Download your report

Click **"Download PDF"** on the results page to save or share a summary report.

### 5. Try the tailored assessment (optional)

Choose **Tailored assessment** in the navigation. Answer four questions about your business, check the suggested business type and the reasons for it, then answer the 20 core questions plus a short set for that type. The results page shows your usual overall score and a separate score for the sector questions. The standard assessment is unchanged and remains the default.

Each sector question is traced to published frameworks (NIST CSF 2.0, ASD Essential Eight, the ACSC Small Business Cyber Security Guide, PCI DSS and OAIC guidance). The mapping is in `data/sectors.py` and is shown to users at `/tailored/sources` and on the results page.

The 20 core questions carry the same kind of mapping in `data/questions.py`: a plain-English reason, the NIST CSF 2.0 function, and at least two sources (always a NIST CSF 2.0 subcategory, plus the Essential Eight strategy where one fits and the ACSC guide section). The mapping is for traceability only and does not change the questions, their wording or the scoring.

> The sector questions and their framework references are draft content awaiting team review. The header of `data/sectors.py` records how far each reference has been checked.

### 6. Save your progress (optional)

Create an account from the results page to save the result. Every assessment you submit while signed in is added to **Score history**, which shows the trend, the change since the previous attempt and each attempt's category breakdown. You can delete the account and its history from the same page.

---

## ✅ Running the Tests

There are two automatic test suites. Install both once:

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium firefox webkit
```

### 1. Unit and integration tests (pytest, about 10 seconds)

```bash
pytest -v
```

These call the app directly, without a browser. They use a temporary database and never call OpenAI or Have I Been Pwned. There are four files:

- `tests/test_guest_regression.py` — the guest-path regression suite (20-question instrument, scoring rules, tier boundaries, recommendations, PDF, no-sign-up journey). Run it at every sprint review.
- `tests/test_accounts.py` — registration rules, login throttling, guest-to-account import, score history, user isolation and account deletion.
- `tests/test_chat.py` — assistant input handling, spend cap and fallback.
- `tests/test_adaptive.py` — business-type classifier, confidence and low-confidence fallback, the three-step tailored flow, separate sector scoring and proof that the core score does not change.

### 2. Browser end-to-end tests (about 1–2 minutes)

```bash
python e2e/run_e2e.py
```

This starts the app on a spare port with an empty temporary database, opens Chromium, and uses the site the way an owner would: guest assessment, PDF, Ask AI, assistant, registering (including refused passwords), score history, logging out and in, the tailored assessment in all four suggestion states, the sources page, CSRF and rate-limit checks, account deletion and phone-width layout. Expected scores and confidence values are worked out from the app's own scoring rules and compared with what is on screen. Each step and check is printed as it runs, and an HTML report with a screenshot of every step opens at the end (`e2e/report/index.html`).

| Option | Effect |
| :----- | :----- |
| `--browsers all` | Runs the journey in Chromium (Chrome, Edge), Firefox and WebKit (Safari's engine) at the same time, each with its own copy of the app and database. The report then opens on a comparison table with a column per browser. You can also list some, e.g. `--browsers chromium,webkit` |
| `--browsers chrome` | Uses the Google Chrome already installed on your computer instead of Playwright's own Chromium, so nothing needs downloading. Useful on older macOS versions that Playwright's downloads no longer support |
| `--headless` | No visible browser; faster |
| `--demo` | Presentation pace (about 7 minutes): a caption box shows the current step, why it matters and each check as it passes; the element about to be clicked or typed into is outlined. Captions are hidden in the report screenshots |
| `--demo --step` | As `--demo`, but waits for Enter before each step, so you can talk through it (single browser only) |
| `--slow 400` | Just slows each action by the given milliseconds, without captions |
| `--live-ai` | Calls GPT-4o-mini for real with the key in `.env` (adds the off-topic refusal check) |
| `--no-open` | Do not open the report at the end |

Your own database is never touched, and by default no OpenAI or breach-check requests are made. The exit code is 0 only when every step passes.

### Automatic runs on GitHub

`.github/workflows/tests.yml` runs both suites on every push and pull request, with the browser journey in all three engines. The end-to-end report is attached to each run as a downloadable artifact.

### Account and history routes

| Route | Purpose |
| :---- | :------ |
| `/register`, `/login`, `POST /logout` | Account forms (CSRF protected) |
| `/history` | Score history page (signed-in users) |
| `POST /account/delete` | Delete account and saved history (password required) |
| `/privacy` | Privacy notice |
| `/tailored/sources` | Framework sources for every sector question |
| `/tailored`, `/tailored/confirm`, `/tailored/assessment` | Tailored assessment: intake, confirm business type, core plus sector questions |
| `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/me` | JSON equivalents of the account forms |
| `/api/assessment-history` | Saved assessments as JSON (signed-in users) |

---

## 🔑 Environment Variables

Create a `.env` file in the project root (copy `.env.example` as a starting point):

```env
# Required: your OpenAI API key
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Flask session secret (set a strong secret for any deployment)
CYBERSHIELD_SECRET_KEY=your-secret-key-here

# Optional: database URL; defaults to instance/cybershield.sqlite
# Example: postgresql://user:password@host:5432/database
DATABASE_URL=

# Set true when serving the app over HTTPS (Render deployment sets this)
CYBERSHIELD_COOKIE_SECURE=false

# Set true only when the app runs behind one trusted proxy (Render sets this),
# so rate limits see each visitor's real IP address
CYBERSHIELD_TRUST_PROXY=false

# Optional assistant limits: requests per visitor per 15 minutes, and per day overall
CYBERSHIELD_CHAT_LIMIT=20
CYBERSHIELD_AI_DAILY_CAP=300
```

> **Deploying on Render:** set `DATABASE_URL` to a hosted PostgreSQL database in the Render dashboard. Without it the app uses a SQLite file on Render's temporary disk, and accounts and history are lost on redeploy or restart.

On first app startup, SQLAlchemy creates the required tables. The history page is available after logging in at `/history`.

---

## 🤝 Team

| Member                     | Role                              |
| :------------------------- | :-------------------------------- |
| **Kamaljeet Kaur**         | Research Lead                     |
| **Lihuy Tang**             | Solutions Lead                    |
| **Isha Chandrakant Gohil** | Planning & User-Focus Contributor |

---

## 📝 Licence

This project was built for educational purposes as part of the ITW601 and ITA602 Work Integrated Learning capstone subjects at Torrens University Australia. No open-source licence (e.g. MIT) has been applied yet.

---

## 🙏 Acknowledgements

- **Australian Cyber Security Centre (ACSC)** — Essential Eight framework, which the questionnaire draws on
- **OpenAI** — GPT-4o-mini and Moderation APIs
- **Torrens University Australia** — for the capstone opportunity

---

**⚠️ Disclaimer:** CyberShield SMB provides general educational information only. It does not replace professional cybersecurity advice, a formal security audit, or incident-response support.
