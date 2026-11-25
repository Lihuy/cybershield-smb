"""Show how many records CyberShield SMB has stored, without opening the website.

Usage (from the project folder, with the virtual environment active):
    python3 scripts/db_stats.py            asks for a database URL (paste the External URL from Render)
    python3 scripts/db_stats.py --local    checks your own local database (instance/cybershield.sqlite)
    python3 scripts/db_stats.py --emails   also lists account emails and sign-up dates

The URL is read without showing it on screen, so the database password is not kept in your
terminal history. The script only reads; it never changes or deletes anything.
"""

import argparse
import getpass
import os

from sqlalchemy import create_engine, inspect, text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = [
    ("users", "Accounts"),
    ("privacy_consents", "Privacy consents"),
    ("assessment_history", "Saved results"),
    ("assessment_sessions", "Assessments taken"),
    ("auth_rate_limit_events", "Sign-in attempts logged"),
]


def normalise(url):
    # Same conversion the app uses (database.py), so Render's URL works as copied.
    for old in ("postgres://", "postgresql://"):
        if url.startswith(old):
            return "postgresql+psycopg://" + url[len(old):]
    return url


def main():
    parser = argparse.ArgumentParser(description="Count the records CyberShield SMB has stored.")
    parser.add_argument("--local", action="store_true", help="use instance/cybershield.sqlite on this computer")
    parser.add_argument("--emails", action="store_true", help="also list account emails and sign-up dates")
    args = parser.parse_args()

    if args.local:
        path = os.path.join(ROOT, "instance", "cybershield.sqlite")
        if not os.path.exists(path):
            print("No local database yet. Run the app once (python3 app.py) to create it.")
            return 1
        url = "sqlite:///" + path
        where = "local database"
    else:
        url = getpass.getpass("Paste the database URL (hidden as you paste): ").strip()
        where = "remote database"
    if not url:
        print("No URL given.")
        return 1

    engine = create_engine(normalise(url))
    try:
        with engine.connect() as connection:
            existing = set(inspect(connection).get_table_names())
            print(f"\nCyberShield SMB: {where}")
            print("-" * 40)
            for table, label in TABLES:
                if table in existing:
                    count = connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f"{label:<26}{count:>8}")
                else:
                    print(f"{label:<26}{'no table':>8}")
            if "users" in existing:
                latest = connection.execute(text("SELECT MAX(created_at) FROM users")).scalar()
                print(f"{'Newest account':<26}{str(latest or '-'):>8}")
                if args.emails:
                    print("\nAccounts (email, created):")
                    for email, created in connection.execute(text("SELECT email, created_at FROM users ORDER BY created_at")):
                        print(f"  {email}  {created}")
    except Exception as error:
        print(f"Could not read the database: {str(error).splitlines()[0]}")
        print("For Render, use the External Database URL (Connect menu on cybershield-db).")
        return 1
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
