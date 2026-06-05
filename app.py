from flask import Flask, render_template, request, redirect, session, send_from_directory, send_file
from werkzeug.utils import secure_filename
from db import engine, Base, SessionLocal
from models import User, Reports
from werkzeug.security import generate_password_hash, check_password_hash
from ai import analyze_resume
from datetime import timedelta
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import PyPDF2
import docx
import json
from dotenv import load_dotenv
import os


load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.secret_key = os.getenv("SECRET_KEY")
app.permanent_session_lifetime = timedelta(days=30)

try:
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully")
except Exception as e:
    print("❌ Error:", e)


# HOME
@app.route("/")
def home():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")


# SIGNUP

@app.route("/signup", methods=["GET", "POST"])
def signup():
    db = SessionLocal()

    if request.method == "POST":

        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Password Match Check
        if password != confirm_password:
            return "Passwords do not match"

        # Check Existing User
        existing_user = db.query(User).filter_by(
            email=email
        ).first()

        if existing_user:
            return "User already exists"

        # Create User
        user = User(
            name=name,
            email=email,
            password=generate_password_hash(password)
            )

        db.add(user)
        db.commit()

        return redirect("/login")

    return render_template("signup.html")



# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():

    db = SessionLocal()

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = db.query(User).filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):
            session.permanent = True

            session["user"] = user.name
            session["email"] = user.email

            return redirect("/dashboard")

        return "Invalid credentials"

    return render_template("login.html")


# DASHBOARD
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if "user" not in session:
        return redirect("/login")

    result = None

    if request.method == "POST":

        user_goal = request.form.get("role")
        resume_text = request.form.get("resume")

        file = request.files.get("file")
        file_name = "Pasted Resume"
        file_path = None

        # PDF Upload
        if file and file.filename != "":

            file_name = secure_filename(file.filename)

            file_path = os.path.join(
                UPLOAD_FOLDER,
                file_name
            )

            file.save(file_path)

            if file.filename.endswith(".pdf"):
                try:
                    pdf_reader = PyPDF2.PdfReader(file_path)

                    text = ""

                    for page in pdf_reader.pages:
                        text += page.extract_text() or ""

                    resume_text = text

                except Exception as e:
                    result = {
                        "error": f"PDF Error: {str(e)}"
                    }

            elif file.filename.endswith(".docx"):
                try:
                    doc = docx.Document(file_path)

                    text = ""

                    for para in doc.paragraphs:
                        text += para.text + "\n"

                    resume_text = text

                except Exception as e:
                    result = {
                        "error": f"DOCX Error: {str(e)}"
                    }

        if resume_text and user_goal:
            try:

                result = analyze_resume(
                    resume_text,
                    user_goal
                )

                # SAVE REPORT
                db = SessionLocal()

                user = db.query(User).filter_by(
                    email=session["email"]
                ).first()

                report = Reports(
                    user_id=user.id,
                    file_name=file_name,
                    file_path=file_path,
                    resume_text=resume_text,
                    result=json.dumps(result)
                )

                db.add(report)
                db.commit()

            except Exception as e:
                result = {
                    "error": f"AI Error: {str(e)}"
                }

        return render_template(
            "dashboard.html",
            user=session["user"],
            result=result
        )

    return render_template(
        "dashboard.html",
        user=session["user"],
        result=result
    )


# HISTORY
@app.route("/history")
def history():

    if "user" not in session:
        return redirect("/login")

    db = SessionLocal()

    search = request.args.get(
        "search",
        ""
    )

    user = db.query(User).filter_by(
        email=session["email"]
    ).first()

    reports_query = db.query(Reports).filter_by(
        user_id=user.id
    )

    if search:

        reports_query = reports_query.filter(
            Reports.file_name.ilike(
                f"%{search}%"
            )
        )

    reports = reports_query.all()

    parsed_reports = []

    for r in reports:

        try:
            result_data = json.loads(r.result)
        except:
            result_data = {}

        parsed_reports.append({
            "id": r.id,
            "file_name": r.file_name,
            "score": result_data.get("resume_score", 0)
        })

    return render_template(
        "history.html",
        reports=parsed_reports,
        search=search
    )

@app.route("/delete-report/<int:report_id>")
def delete_report(report_id):

    if "user" not in session:
        return redirect("/login")

    db = SessionLocal()

    user = db.query(User).filter_by(
        email=session["email"]
    ).first()

    report = db.query(Reports).filter_by(
        id=report_id,
        user_id=user.id
    ).first()

    if report:
        db.delete(report)
        db.commit()

    return redirect("/history")

@app.route("/report/<int:report_id>")
def report_details(report_id):

    if "user" not in session:
        return redirect("/login")

    db = SessionLocal()

    user = db.query(User).filter_by(
        email=session["email"]
    ).first()

    report = db.query(Reports).filter_by(
        id=report_id,
        user_id=user.id
    ).first()

    if not report:
        return redirect("/history")

    result_data = json.loads(report.result)

    return render_template(
        "report_details.html",
        report=report,
        result=result_data
    )

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )

@app.route("/download-report/<int:report_id>")
def download_report(report_id):

    if "user" not in session:
        return redirect("/login")

    db = SessionLocal()

    user = db.query(User).filter_by(
        email=session["email"]
    ).first()

    report = db.query(Reports).filter_by(
        id=report_id,
        user_id=user.id
    ).first()

    if not report:
        return redirect("/history")

    result = json.loads(report.result)

    pdf_buffer = BytesIO()

    doc = SimpleDocTemplate(pdf_buffer)

    styles = getSampleStyleSheet()

    content = []

    content.append(
        Paragraph(
            f"Resume Analysis Report - {report.file_name}",
            styles["Title"]
        )
    )

    content.append(Spacer(1, 20))

    content.append(
        Paragraph(
            f"Resume Score: {result.get('resume_score', 0)}/100",
            styles["Heading2"]
        )
    )

    content.append(
        Paragraph(
            f"ATS Score: {result.get('ats_score', 0)}/100",
            styles["Heading2"]
        )
    )

    content.append(Spacer(1, 10))

    sections = [
        ("Strengths", result.get("strengths", [])),
        ("Weaknesses", result.get("weaknesses", [])),
        ("Skills", result.get("skills", [])),
        ("Missing Skills", result.get("missing_skills", [])),
        ("Roadmap", result.get("roadmap", [])),
        ("Interview Questions", result.get("interview_questions", []))
    ]

    for title, items in sections:

        content.append(
            Paragraph(title, styles["Heading2"])
        )

        for item in items:
            content.append(
                Paragraph(f"• {item}", styles["BodyText"])
            )

        content.append(Spacer(1, 10))

    doc.build(content)

    pdf_buffer.seek(0)

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"{report.file_name}_analysis.pdf",
        mimetype="application/pdf"
    )

# LOGOUT
@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("email", None)
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)