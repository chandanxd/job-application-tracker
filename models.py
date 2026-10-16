from datetime import UTC, date, datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

db = SQLAlchemy()


class JobApplication(db.Model):
    """Model representing a job application."""

    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Applied")
    application_date: Mapped[date] = mapped_column(
        Date, nullable=False, default=date.today
    )
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    job_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<JobApplication {self.company_name} - {self.role}>"

    def to_dict(self) -> dict:
        """Convert the application to a dictionary."""
        return {
            "id": self.id,
            "company_name": self.company_name,
            "role": self.role,
            "status": self.status,
            "application_date": (
                self.application_date.strftime("%Y-%m-%d")
                if self.application_date
                else None
            ),
            "follow_up_date": (
                self.follow_up_date.strftime("%Y-%m-%d")
                if self.follow_up_date
                else None
            ),
            "job_description": self.job_description,
            "notes": self.notes,
            "match_score": self.match_score,
        }

    @property
    def needs_follow_up_soon(self) -> bool:
        """Check if follow-up is due within three days."""
        if self.follow_up_date is None:
            return False

        days_until = (self.follow_up_date - date.today()).days
        return 0 <= days_until <= 3
