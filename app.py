"""CyberShield SMB Flask application entry point."""

import os
from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape

from flask import Flask, redirect, render_template, request, send_file, session, url_for

from ai.assistant import DISCLAIMER, answer_question
from data.questions import ASSESSMENT_CATEGORIES
from engine.risk_engine import calculate_assessment
from utils.recommendations import generate_recommendations

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("CYBERSHIELD_SECRET_KEY", "change-this-for-a-unique-deployment-secret")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def _result_context():
    """Retrieve the latest result while preserving template variables expected by the UI."""
    result = session.get("assessment_result")
    if result is None:
        return None
    return {
        "score": result["score"],
        "risk": result["risk"],
        "assessment_date": result["assessment_date"],
        "category_scores": result["category_scores"],
        "recommendations": result["recommendations"],
        "summary": result["summary"],
        "total_questions": result["total_questions"],
    }


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/assessment", methods=["GET", "POST"])
def assessment():
    if request.method == "POST":
        calculation = calculate_assessment(request.form)
        calculation["recommendations"] = generate_recommendations(calculation["answers"])
        calculation["assessment_date"] = date.today().strftime("%d %B %Y")
        session["assessment_result"] = calculation
        return redirect(url_for("result"))

    return render_template("assessment.html", categories=ASSESSMENT_CATEGORIES)


@app.route("/result")
def result():
    context = _result_context()
    if context is None:
        return redirect(url_for("assessment"))
    return render_template("result.html", **context)


@app.route("/assistant", methods=["GET", "POST"])
def chatbot():
    question = ""
    answer = ""
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        answer = answer_question(question)
    return render_template("chatbot.html", question=question, answer=answer, disclaimer=DISCLAIMER)


@app.route("/download-report")
def download_report():
    """Create a concise, downloadable PDF report from the latest browser-session result."""
    context = _result_context()
    if context is None:
        return redirect(url_for("assessment"))

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        return "PDF reporting requires the ReportLab package. Run: pip install -r requirements.txt", 500

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ShieldTitle", parent=styles["Title"], textColor=colors.HexColor("#0F4C81"), alignment=TA_CENTER, fontSize=23, leading=28))
    styles.add(ParagraphStyle(name="ShieldHeading", parent=styles["Heading2"], textColor=colors.HexColor("#0F4C81"), spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="ShieldBody", parent=styles["BodyText"], leading=16, textColor=colors.HexColor("#243447")))
    styles.add(ParagraphStyle(name="ShieldSmall", parent=styles["BodyText"], fontSize=8.5, leading=11, textColor=colors.HexColor("#526477")))

    story = [
        Paragraph("CyberShield SMB", styles["ShieldTitle"]),
        Paragraph("Cybersecurity Self-Assessment Report", styles["ShieldBody"]),
        Spacer(1, 6 * mm),
        Paragraph(f"Assessment date: {escape(context['assessment_date'])}", styles["ShieldBody"]),
        Spacer(1, 4 * mm),
    ]
    score_table = Table(
        [["Overall security score", "Risk level", "Recommended actions"], [f"{context['score']} / 100", context["risk"], str(len(context["recommendations"]))]],
        colWidths=[58 * mm, 48 * mm, 58 * mm],
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F4F7FB")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#0F4C81")),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, 1), 15),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9E2EF")),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.extend([score_table, Paragraph("Executive summary", styles["ShieldHeading"]), Paragraph(escape(context["summary"]["headline"]), styles["ShieldBody"]), Paragraph(escape(context["summary"]["detail"]), styles["ShieldBody"])])

    story.append(Paragraph("Category performance", styles["ShieldHeading"]))
    category_rows = [["Category", "Score", "Safeguards in place"]]
    for category in context["category_scores"]:
        category_rows.append([category["name"], f"{category['score']}%", f"{category['protected']} of {category['total']}"])
    category_table = Table(category_rows, colWidths=[78 * mm, 35 * mm, 51 * mm])
    category_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7F0FA")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0F4C81")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D9E2EF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(category_table)

    story.append(Paragraph("Prioritised action plan", styles["ShieldHeading"]))
    if context["recommendations"]:
        for item in context["recommendations"]:
            story.append(Paragraph(f"<b>{escape(item['priority'])} priority — {escape(item['category'])}</b><br/>{escape(item['description'])}", styles["ShieldBody"]))
            story.append(Spacer(1, 2.5 * mm))
    else:
        story.append(Paragraph("Excellent work — all assessment safeguards were marked as in place. Review your controls regularly to keep them effective.", styles["ShieldBody"]))

    story.extend([Spacer(1, 5 * mm), Paragraph(escape(DISCLAIMER), styles["ShieldSmall"])])
    document.build(story)
    buffer.seek(0)
    safe_date = context["assessment_date"].replace(" ", "-").lower()
    return send_file(buffer, as_attachment=True, download_name=f"cybershield-smb-report-{safe_date}.pdf", mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True)
