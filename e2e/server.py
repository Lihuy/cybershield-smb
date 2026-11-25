"""Start CyberShield SMB for the end-to-end tests. Started automatically by run_e2e.py.

The app runs exactly as normal, with three differences so the tests are repeatable and safe:
- It uses a brand-new temporary SQLite database, so your real database is never touched.
- The breach check (Have I Been Pwned) is replaced: only the password in BREACHED_PASSWORD
  counts as breached. This lets the tests check both outcomes without the internet.
- Unless --live-ai is given, OpenAI is not called. The assistant uses its offline rule-based
  answers, and business descriptions are read by a small keyword stand-in. With --live-ai the
  real GPT-4o-mini calls are made with the key in your .env file (a few cents at most).
"""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BREACHED_PASSWORD = "e2e breached password 2026"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--live-ai", action="store_true")
    args = parser.parse_args()

    os.environ["DATABASE_URL"] = f"sqlite:///{args.db}"
    os.environ["CYBERSHIELD_SECRET_KEY"] = "e2e-only-secret-key-0123456789abcdef"
    os.environ["CYBERSHIELD_COOKIE_SECURE"] = "false"
    os.environ["CYBERSHIELD_TRUST_PROXY"] = "false"
    os.environ["FLASK_DEBUG"] = "false"
    if not args.live_ai:
        # Set before the app loads, so the key in .env is never used in offline mode.
        os.environ["OPENAI_API_KEY"] = "offline-e2e-not-used"

    sys.path.insert(0, ROOT)
    os.chdir(ROOT)
    import app as cybershield

    cybershield._password_is_breached = lambda password: password == BREACHED_PASSWORD

    if not args.live_ai:
        from ai.assistant import answer_question
        import ai.business_classifier as business_classifier

        def offline_assistant(message, risk_context=None):
            return answer_question(message.replace("[ASK_AI]", "").strip())

        def offline_labeller(description):
            # Stand-in for GPT-4o-mini: the app's own keyword match, plus two words it does not know.
            label = business_classifier.keyword_sector(description)
            if label:
                return label
            text = description.lower()
            for word, label in (("korean", "hospitality"), ("cuisine", "hospitality"), ("plumb", "trades")):
                if word in text:
                    return label
            return "unknown"

        cybershield.get_openai_response = offline_assistant
        business_classifier._ask_model = offline_labeller

    cybershield.app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
