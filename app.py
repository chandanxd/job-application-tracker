import csv
import os
from datetime import UTC, datetime, timedelta
from io import BytesIO, StringIO

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from forms import JobApplicationForm, SearchFilterForm
from models import JobApplication, db

app = Flask(__name__)

load_dotenv()

# Configuration
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///jobs.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Fix for Heroku postgres:// -> postgresql:// compatibility.
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config[
        "SQLALCHEMY_DATABASE_URI"
    ].replace("postgres://", "postgresql://", 1)

# Initialize database.
db.init_app(app)

# Create tables.
with app.app_context():
    db.create_all()


@app.route("/")
def index():
    """Display job applications with filtering and search."""
    form = SearchFilterForm(request.args, meta={"csrf": False})

    query = JobApplication.query

    # Apply search filter.
    search_query = request.args.get("search_query", "").strip()
    if search_query:
        query = query.filter(
            db.or_(
                JobApplication.company_name.ilike(f"%{search_query}%"),
                JobApplication.role.ilike(f"%{search_query}%"),
            )
        )

    # Apply status filter.
    status_filter = request.args.get("status_filter", "")
    if status_filter:
        query = query.filter(JobApplication.status == status_filter)

    # Apply sorting.
    sort_by = request.args.get("sort_by", "application_date_desc")
    if sort_by == "application_date_desc":
        query = query.order_by(JobApplication.application_date.desc())
    elif sort_by == "application_date_asc":
        query = query.order_by(JobApplication.application_date.asc())
    elif sort_by == "company_name_asc":
        query = query.order_by(JobApplication.company_name.asc())
    elif sort_by == "company_name_desc":
        query = query.order_by(JobApplication.company_name.desc())

    jobs = query.all()

    # Get applications needing follow-up within the next three days.
    today = datetime.now(UTC).date()
    three_days_from_now = today + timedelta(days=3)

    follow_up_jobs = JobApplication.query.filter(
        JobApplication.follow_up_date.between(today, three_days_from_now)
    ).all()

    return render_template(
        "index.html",
        jobs=jobs,
        form=form,
        follow_up_jobs=follow_up_jobs,
    )


@app.route("/add", methods=["GET", "POST"])
def add_job():
    """Add a new job application."""
    form = JobApplicationForm()

    if form.validate_on_submit():
        company_name = form.company_name.data
        role = form.role.data
        status = form.status.data
        application_date = form.application_date.data

        # Narrow optional WTForms data types for static analysis.
        if (
            company_name is None
            or role is None
            or status is None
            or application_date is None
        ):
            raise ValueError("Required application fields are missing.")

        job = JobApplication()
        job.company_name = company_name
        job.role = role
        job.status = status
        job.application_date = application_date
        job.follow_up_date = form.follow_up_date.data
        job.job_description = form.job_description.data
        job.resume_text = form.resume_text.data
        job.notes = form.notes.data

        # Calculate match score when both text fields are available.
        if job.resume_text and job.job_description:
            job.match_score = calculate_match_score(
                job.resume_text,
                job.job_description,
            )

        db.session.add(job)
        db.session.commit()

        flash(
            f"Successfully added application for {job.role} at {job.company_name}!",
            "success",
        )
        return redirect(url_for("index"))

    return render_template("add_job.html", form=form)


@app.route("/edit/<int:job_id>", methods=["GET", "POST"])
def edit_job(job_id):
    """Edit an existing job application."""
    job = JobApplication.query.get_or_404(job_id)
    form = JobApplicationForm(obj=job)

    if form.validate_on_submit():
        company_name = form.company_name.data
        role = form.role.data
        status = form.status.data
        application_date = form.application_date.data

        # Narrow optional WTForms data types for static analysis.
        if (
            company_name is None
            or role is None
            or status is None
            or application_date is None
        ):
            raise ValueError("Required application fields are missing.")

        job.company_name = company_name
        job.role = role
        job.status = status
        job.application_date = application_date
        job.follow_up_date = form.follow_up_date.data
        job.job_description = form.job_description.data
        job.resume_text = form.resume_text.data
        job.notes = form.notes.data

        # Recalculate or clear the match score.
        if job.resume_text and job.job_description:
            job.match_score = calculate_match_score(
                job.resume_text,
                job.job_description,
            )
        else:
            job.match_score = None

        db.session.commit()

        flash(
            f"Successfully updated application for {job.role} at {job.company_name}!",
            "success",
        )
        return redirect(url_for("index"))

    return render_template("edit_job.html", form=form, job=job)


@app.route("/delete/<int:job_id>", methods=["POST"])
def delete_job(job_id):
    """Delete a job application."""
    job = JobApplication.query.get_or_404(job_id)
    company = job.company_name
    role = job.role

    db.session.delete(job)
    db.session.commit()

    flash(f"Deleted application for {role} at {company}.", "info")
    return redirect(url_for("index"))


@app.route("/stats")
def stats():
    """Display application statistics."""
    total_apps = JobApplication.query.count()

    status_counts = (
        db.session.query(
            JobApplication.status,
            db.func.count(JobApplication.id),
        )
        .group_by(JobApplication.status)
        .all()
    )

    status_data = {status: count for status, count in status_counts}

    # SQLite-specific month grouping.
    monthly_apps = (
        db.session.query(
            db.func.strftime("%Y-%m", JobApplication.application_date).label("month"),
            db.func.count(JobApplication.id).label("count"),
        )
        .group_by("month")
        .order_by("month")
        .all()
    )

    return render_template(
        "stats.html",
        total_apps=total_apps,
        status_data=status_data,
        monthly_apps=monthly_apps,
    )


@app.route("/export")
def export_csv():
    """Export all job applications to CSV."""
    jobs = JobApplication.query.all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Company",
            "Role",
            "Status",
            "Application Date",
            "Follow-up Date",
            "Notes",
            "Match Score",
        ]
    )

    for job in jobs:
        writer.writerow(
            [
                job.company_name,
                job.role,
                job.status,
                (
                    job.application_date.strftime("%Y-%m-%d")
                    if job.application_date
                    else ""
                ),
                (job.follow_up_date.strftime("%Y-%m-%d") if job.follow_up_date else ""),
                job.notes or "",
                (job.match_score if job.match_score is not None else ""),
            ]
        )

    byte_output = BytesIO(output.getvalue().encode("utf-8"))

    return send_file(
        byte_output,
        mimetype="text/csv",
        as_attachment=True,
        download_name=(f"job_applications_{datetime.now(UTC).strftime('%Y%m%d')}.csv"),
    )


@app.errorhandler(404)
def not_found(error):
    """Render the not-found page."""
    return render_template("404.html"), 404


def calculate_match_score(
    resume_text: str | None,
    job_description: str | None,
) -> float | None:
    """Calculate resume-job description similarity as a percentage."""
    if not resume_text or not job_description:
        return None

    resume_text = resume_text.strip()
    job_description = job_description.strip()

    if not resume_text or not job_description:
        return None

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
        similarity = cosine_similarity(
            tfidf_matrix,
            dense_output=True,
        )[0, 1]

        return round(float(similarity) * 100, 2)

    except ValueError:
        app.logger.warning(
            "Could not calculate match score because the text "
            "did not produce a usable TF-IDF vocabulary."
        )
        return None


if __name__ == "__main__":
    app.run(debug=True)
