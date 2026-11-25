"""Database setup and models for persistent CyberShield SMB records.

Set ``DATABASE_URL`` to a SQLAlchemy URL to use another database. The default
stores a local SQLite file in the project directory.
"""

import os
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


db = SQLAlchemy()


def _utc_now():
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    assessment_sessions: Mapped[list["AssessmentSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    privacy_consents: Mapped[list["PrivacyConsent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AssessmentSession(db.Model):
    __tablename__ = "assessment_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    business_type: Mapped[str | None] = mapped_column(String(120))
    overall_score: Mapped[float | None] = mapped_column(Float)
    risk_tier: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="assessment_sessions")
    history: Mapped[list["AssessmentHistory"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class AssessmentHistory(db.Model):
    __tablename__ = "assessment_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendations: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    session: Mapped[AssessmentSession] = relationship(back_populates="history")


class PrivacyConsent(db.Model):
    """Record the privacy notice version accepted when an account was created."""

    __tablename__ = "privacy_consents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notice_version: Mapped[str] = mapped_column(String(20), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="privacy_consents")


class AuthRateLimitEvent(db.Model):
    """Pseudonymous authentication attempt keys used for database-backed throttling."""

    __tablename__ = "auth_rate_limit_events"
    __table_args__ = (Index("ix_auth_rate_limit_key_time", "key_hash", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)


def init_database(app):
    """Configure the SQLAlchemy extension and create missing tables.

    Existing tables are left in place. Use a migration tool for schema changes
    once the application is deployed or has persistent user data.
    """
    default_path = os.path.join(app.instance_path, "cybershield.sqlite")
    os.makedirs(app.instance_path, exist_ok=True)
    database_url = os.environ.get("DATABASE_URL") or f"sqlite:///{default_path}"
    # Some managed Postgres providers still expose the legacy ``postgres://`` scheme.
    if database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgres://"):]
    elif database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgresql://"):]
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", database_url)
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    db.init_app(app)
    with app.app_context():
        db.create_all()
