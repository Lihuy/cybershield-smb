# 🛡️ CyberShield SMB

**An AI-powered cybersecurity companion for Australian small businesses**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)

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
- **Session-based, no sign-up** — start the assessment immediately, nothing is stored in a database
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

- **No database** — results live only in your browser session for the duration of your visit

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
| **Session storage** | Flask server-side session (no database)                         |

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

---

## 📁 Project Structure

```
cybershield-smb/
├── ai/
│   ├── assistant.py           # Rule-based fallback assistant (works offline)
│   └── openai_assistant.py    # OpenAI GPT-4o-mini integration, topic filter + moderation
├── data/
│   └── questions.py           # 20 questions across 6 categories
├── engine/
│   └── risk_engine.py         # Rule-based scoring: category scores, risk level, summary
├── static/
│   ├── css/
│   │   └── style.css
│   └── images/
│       ├── cybershield-logo.svg
│       └── lock.svg
├── templates/
│   ├── base.html               # Shared layout, nav, Bootstrap/Chart.js includes
│   ├── home.html
│   ├── assessment.html
│   ├── result.html             # Dashboard: score, radar chart, action plan, Ask AI
│   └── chatbot.html
├── utils/
│   └── recommendations.py     # Builds the prioritised action plan from unanswered items
├── .env.example
├── app.py                      # Flask application entry point and routes
├── requirements.txt
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

---

## 🔑 Environment Variables

Create a `.env` file in the project root (copy `.env.example` as a starting point):

```env
# Required: your OpenAI API key
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: Flask session secret (a default is used if not set — change this for any real deployment)
CYBERSHIELD_SECRET_KEY=your-secret-key-here
```

---

## 🤝 Team

| Member                     | Role                              |
| :------------------------- | :-------------------------------- |
| **Kamaljeet Kaur**         | Research Lead                     |
| **Lihuy Tang**             | Solutions Lead                    |
| **Isha Chandrakant Gohil** | Planning & User-Focus Contributor |

---

## 📝 Licence

This project was built for educational purposes as part of the ITW601 — Information Technology Work Integrated Learning capstone at Torrens University Australia. No open-source licence (e.g. MIT) has been applied yet.

---

## 🙏 Acknowledgements

- **Australian Cyber Security Centre (ACSC)** — Essential Eight framework, which the questionnaire draws on
- **OpenAI** — GPT-4o-mini and Moderation APIs
- **Torrens University Australia** — for the capstone opportunity

---

**⚠️ Disclaimer:** CyberShield SMB provides general educational information only. It does not replace professional cybersecurity advice, a formal security audit, or incident-response support.
