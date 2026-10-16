from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Optional


class JobApplicationForm(FlaskForm):
    """Form for creating/editing job applications."""

    company_name = StringField(
        "Company Name",
        validators=[DataRequired()],
        render_kw={"placeholder": "e.g., Google"},
    )

    role = StringField(
        "Role",
        validators=[DataRequired()],
        render_kw={"placeholder": "e.g., Software Engineer"},
    )

    status = SelectField(
        "Status",
        choices=[
            ("Applied", "Applied"),
            ("Interview", "Interview"),
            ("Offer", "Offer"),
            ("Rejected", "Rejected"),
        ],
        validators=[DataRequired()],
    )

    application_date = DateField(
        "Application Date",
        format="%Y-%m-%d",
        default=date.today,
        validators=[DataRequired()],
    )

    follow_up_date = DateField(
        "Follow-up Date", format="%Y-%m-%d", validators=[Optional()]
    )

    job_description = TextAreaField(
        "Job Description (Optional)",
        render_kw={"rows": 6, "placeholder": "Paste the job description here"},
    )

    resume_text = TextAreaField(
        "Your Resume (Optional)",
        render_kw={"rows": 8, "placeholder": "Paste your resume text for matching..."},
    )

    notes = TextAreaField(
        "Notes (Optional)",
        render_kw={
            "rows": 4,
            "placeholder": "Add any notes about the application here",
        },
    )

    submit = SubmitField("Save Application")


class SearchFilterForm(FlaskForm):
    """Form for filtering and searching job applications."""

    search_query = StringField(
        "Search", render_kw={"placeholder": "Search a company or role"}
    )

    status_filter = SelectField(
        "Filter by Status",
        choices=[
            ("", "All Statuses"),
            ("Applied", "Applied"),
            ("Interview", "Interview"),
            ("Offer", "Offer"),
            ("Rejected", "Rejected"),
        ],
    )

    sort_by = SelectField(
        "Sort by",
        choices=[
            ("application_date_desc", "Application Date (Newest)"),
            ("application_date_asc", "Application Date (Oldest)"),
            ("company_name_asc", "Company Name (A-Z)"),
            ("company_name_desc", "Company Name (Z-A)"),
        ],
    )
