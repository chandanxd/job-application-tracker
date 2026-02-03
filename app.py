import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from datetime import datetime, timedelta, timezone
from models import db, JobApplication
from forms import JobApplicationForm, SearchFilterForm
import csv
from io import StringIO, BytesIO

app = Flask(__name__)

# Configuration
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-secret-key-change-in-production"
)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///jobs.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Fix for Heroku postgres:// -> postgresql:// issue
if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
    app.config["SQLALCHEMY_DATABASE_URI"] = app.config[
        "SQLALCHEMY_DATABASE_URI"
    ].replace("postgres://", "postgresql://", 1)

# Initialize database
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()


@app.route("/")
def index():
    """Dashboard showing all job applications with filtering/search"""
    form = SearchFilterForm(request.args, meta={"csrf": False})

    # Start with all jobs
    query = JobApplication.query

    # Apply search filter
    search_query = request.args.get("search_query", "").strip()
    if search_query:
        query = query.filter(
            db.or_(
                JobApplication.company_name.ilike(f"%{search_query}%"),
                JobApplication.role.ilike(f"%{search_query}%"),
            )
        )

    # Apply status filter
    status_filter = request.args.get("status_filter", "")
    if status_filter:
        query = query.filter(JobApplication.status == status_filter)

    # Apply sorting
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

    # Get jobs needing follow-up soon
    today = datetime.now(timezone.utc).date()
    three_days_from_now = today + timedelta(days=3)
    follow_up_jobs = JobApplication.query.filter(
        JobApplication.follow_up_date.between(today, three_days_from_now)
    ).all()

    return render_template(
        "index.html", jobs=jobs, form=form, follow_up_jobs=follow_up_jobs
    )


@app.route("/add", methods=["GET", "POST"])
def add_job():
    """Add a new job application"""
    form = JobApplicationForm()

    if form.validate_on_submit():
        job = JobApplication(
            company_name=form.company_name.data,  # type: ignore
            role=form.role.data,  # type: ignore
            status=form.status.data,  # type: ignore
            application_date=form.application_date.data,  # type: ignore
            follow_up_date=form.follow_up_date.data,  # type: ignore
            job_description=form.job_description.data,  # type: ignore
            notes=form.notes.data,  # type: ignore
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
    """Edit an existing job application"""
    job = JobApplication.query.get_or_404(job_id)
    form = JobApplicationForm(obj=job)

    if form.validate_on_submit():
        job.company_name = form.company_name.data
        job.role = form.role.data
        job.status = form.status.data
        job.application_date = form.application_date.data
        job.follow_up_date = form.follow_up_date.data
        job.job_description = form.job_description.data
        job.notes = form.notes.data

        db.session.commit()

        flash(
            f"Successfully updated application for {job.role} at {job.company_name}!",
            "success",
        )
        return redirect(url_for("index"))

    return render_template("edit_job.html", form=form, job=job)


@app.route("/delete/<int:job_id>", methods=["POST"])
def delete_job(job_id):
    """Delete a job application"""
    job = JobApplication.query.get_or_404(job_id)
    company = job.company_name
    role = job.role

    db.session.delete(job)
    db.session.commit()

    flash(f"Deleted application for {role} at {company}.", "info")
    return redirect(url_for("index"))


@app.route("/stats")
def stats():
    """Statistics dashboard"""
    # Total applications
    total_apps = JobApplication.query.count()

    # Status breakdown
    status_counts = (
        db.session.query(JobApplication.status, db.func.count(JobApplication.id))
        .group_by(JobApplication.status)
        .all()
    )

    # Convert to dictionary for easier use in template
    status_data = {status: count for status, count in status_counts}

    # Applications over time (by month)
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
    """Export all job applications to CSV"""
    jobs = JobApplication.query.all()

    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Write header
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

    # Write data
    for job in jobs:
        writer.writerow(
            [
                job.company_name,
                job.role,
                job.status,
                job.application_date.strftime("%Y-%m-%d"),
                job.follow_up_date.strftime("%Y-%m-%d") if job.follow_up_date else "",
                job.notes or "",
                job.match_score or "",
            ]
        )

    # Convert to bytes for download
    output.seek(0)
    byte_output = BytesIO()
    byte_output.write(output.getvalue().encode("utf-8"))
    byte_output.seek(0)

    return send_file(
        byte_output,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f'job_applications_{datetime.now().strftime("%Y%m%d")}.csv',
    )


if __name__ == "__main__":
    app.run(debug=True)
