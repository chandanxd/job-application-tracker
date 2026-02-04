from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class JobApplication(db.Model):
    """Model representing a job application"""

    __tablename__ = "job_applications"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Applied")
    application_date = db.Column(
        db.Date, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    follow_up_date = db.Column(db.Date, nullable=True)
    job_description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    resume_text = db.Column(db.Text, nullable=True)
    match_score = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f"<JobApplication {self.company_name} - {self.role}>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization (useful for CSV export)"""
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
    def needs_follow_up_soon(self):
        """Check if follow-up is due within 3 days"""
        if not self.follow_up_date:
            return False
        days_until = (self.follow_up_date - datetime.utcnow().date()).days
        return 0 <= days_until <= 3
