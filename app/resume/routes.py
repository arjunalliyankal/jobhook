from flask import Blueprint, request, jsonify, current_app, send_from_directory, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from .parser import extract_resume_text, extract_email, extract_phone
from .models import ResumeModel
from ..ai.groq_client import GroqClient
from ..auth.models import UserModel
import os
import uuid
import io

resume_bp = Blueprint("resume", __name__)
resume_model = ResumeModel()
user_model = UserModel()
groq = GroqClient()

ALLOWED = {"pdf", "docx", "doc"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED


@resume_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_resume():
    user_id = get_jwt_identity()

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use PDF or DOCX"}), 400

    filename = secure_filename(file.filename)
    extension = os.path.splitext(filename)[1]
    storage_name = f"{uuid.uuid4()}{extension}"

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "resumes")
    upload_path = os.path.join(upload_dir, storage_name)
    file.save(upload_path)

    # Extract text
    raw_text = extract_resume_text(upload_path)

    # AI-assisted parsing: ask Groq to return structured JSON
    parsed = groq.parse_resume(raw_text)

    resume_id = resume_model.create(
        user_id=user_id,
        file_name=filename,
        storage_name=storage_name,
        raw_text=raw_text,
        parsed=parsed
    )

    # Update User Profile with parsed data
    user = user_model.find_by_id(user_id)
    if user:
        current_profile = user.get("profile", {})
        
        # Update flat fields unconditionally with parsed data
        for field in ["phone", "linkedin", "summary", "location", "email", "portfolio"]:
            if parsed.get(field):
                current_profile[field] = parsed[field]
        
        # Overwrite skills list with parsed skills
        if parsed.get("skills"):
            current_profile["skills_list"] = [{"name": s, "level": ""} for s in parsed["skills"]]
            
        # Overwrite array fields unconditionally with parsed data
        for list_field in ["experience", "education", "projects", "internships", "certificates", "miscellaneous"]:
            if parsed.get(list_field) is not None:
                current_profile[list_field] = parsed[list_field]
        
        user_model.update_profile(user_id, current_profile)
        
        # Update user name if provided in parsed resume
        if parsed.get("name"):
            from ..extensions import mongo
            from bson import ObjectId
            mongo.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"name": parsed["name"]}}
            )

    return jsonify({
        "message": "Resume uploaded and profile updated successfully",
        "resume_id": str(resume_id),
        "storage_name": storage_name,
        "parsed": parsed
    }), 201


@resume_bp.route("/view/<filename>", methods=["GET"])
def view_resume(filename):
    """Serve the resume file."""
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "resumes")
    return send_from_directory(upload_dir, filename)


@resume_bp.route("/", methods=["GET"])
@jwt_required()
def get_resumes():
    user_id = get_jwt_identity()
    resumes = resume_model.get_by_user(user_id)
    return jsonify(resumes), 200


@resume_bp.route("/<resume_id>", methods=["DELETE"])
@jwt_required()
def delete_resume(resume_id):
    user_id = get_jwt_identity()
    resume_model.delete(resume_id, user_id)
    return jsonify({"message": "Resume deleted"}), 200


@resume_bp.route("/<resume_id>/set_active", methods=["POST"])
@jwt_required()
def set_active_resume(resume_id):
    """Update User Profile with parsed data from an existing resume."""
    from ..extensions import mongo
    from bson import ObjectId
    user_id = get_jwt_identity()
    user = user_model.find_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    resume = next((r for r in resume_model.get_by_user(user_id) if str(r.get("_id")) == resume_id), None)
    if not resume:
        return jsonify({"error": "Resume not found"}), 404
        
    parsed = resume.get("parsed", {})
    current_profile = user.get("profile", {})
    
    # Update flat fields unconditionally with parsed data
    for field in ["phone", "linkedin", "summary", "location", "email", "portfolio"]:
        if parsed.get(field):
            current_profile[field] = parsed[field]
    
    # Overwrite skills list with parsed skills
    if parsed.get("skills"):
        current_profile["skills_list"] = [{"name": s, "level": ""} for s in parsed["skills"]]
        
    # Overwrite array fields unconditionally with parsed data
    for list_field in ["experience", "education", "projects", "internships", "certificates", "miscellaneous"]:
        if parsed.get(list_field) is not None:
            current_profile[list_field] = parsed[list_field]
    
    user_model.update_profile(user_id, current_profile)
    
    update_data = {"$set": {"active_resume_id": ObjectId(resume_id)}}
    if parsed.get("name"):
        update_data["$set"]["name"] = parsed["name"]
        
    mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        update_data
    )

    return jsonify({"message": "Profile updated from resume"}), 200



@resume_bp.route("/download", methods=["POST"])
@jwt_required()
def download_resume_pdf():
    """Generate and return a PDF of the provided parsed resume data."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
    except ImportError:
        return jsonify({"error": "PDF generation not available. Install reportlab."}), 500

    data = request.get_json(silent=True) or {}
    p = data.get("parsed", {})

    # --- Build PDF in memory ---
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )

    PRIMARY = colors.black
    TEXT_MAIN = colors.black
    TEXT_MUTED = colors.black
    BORDER = colors.lightgrey

    styles = getSampleStyleSheet()

    name_style = ParagraphStyle("Name", fontSize=18, fontName="Helvetica-Bold",
                                 textColor=TEXT_MAIN, alignment=TA_CENTER, spaceAfter=8)
    contact_style = ParagraphStyle("Contact", fontSize=9, fontName="Helvetica",
                                    textColor=TEXT_MUTED, alignment=TA_CENTER, spaceBefore=4, spaceAfter=8)
    section_h_style = ParagraphStyle("SectionH", fontSize=8, fontName="Helvetica-Bold",
                                      textColor=PRIMARY, spaceBefore=14, spaceAfter=6,
                                      textTransform="uppercase", letterSpacing=1.2)
    entry_title_style = ParagraphStyle("EntryTitle", fontSize=10, fontName="Helvetica-Bold",
                                        textColor=TEXT_MAIN, spaceBefore=6, spaceAfter=2)
    entry_meta_style = ParagraphStyle("EntryMeta", fontSize=9, fontName="Helvetica",
                                       textColor=TEXT_MUTED, spaceAfter=3)
    body_style = ParagraphStyle("Body", fontSize=9, fontName="Helvetica",
                                  textColor=TEXT_MUTED, spaceAfter=3, leading=13)
    skill_badge_style = ParagraphStyle("SkillBadge", fontSize=9, fontName="Helvetica",
                                        textColor=TEXT_MUTED, spaceAfter=8, leading=14)

    story = []

    # Header
    name = p.get("name") or "Your Name"
    story.append(Paragraph(name, name_style))

    contact_parts = [x for x in [p.get("email"), p.get("phone"), p.get("location")] if x]
    links = []
    if p.get("linkedin"):
        li = p["linkedin"].replace("https://", "").replace("www.", "")
        links.append(f'<a href="{p["linkedin"]}" color="black">{li}</a>')
    
    contact_str = " | ".join(contact_parts)
    if links:
        contact_str += " | " + " | ".join(links)
    
    if contact_str:
        story.append(Paragraph(contact_str, contact_style))

    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=6))

    # --- REORDERED SECTIONS ---

    # 0. Summary
    if p.get("summary"):
        story.append(Paragraph("Professional Summary", section_h_style))
        story.append(Paragraph(p["summary"], body_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=4))

    # 1. Education
    education = p.get("education") or []
    if education:
        story.append(Paragraph("Education", section_h_style))
        for ed in education:
            degree = ed.get("degree", "")
            field = ed.get("field", "")
            school = ed.get("school", "")
            year = ed.get("year", "")
            deg_text = f"{degree}{' in ' + field if field else ''}"
            story.append(Paragraph(deg_text, entry_title_style))
            story.append(Paragraph(f"{school}{' (' + year + ')' if year else ''}", entry_meta_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=4))

    # 2. Experience
    experience = p.get("experience") or []
    if experience:
        story.append(Paragraph("Experience", section_h_style))
        for ex in experience:
            title = ex.get("title", "")
            company = ex.get("company", "")
            start = ex.get("start", "")
            end = ex.get("end", "Present")
            story.append(Paragraph(f"{title} <font color='#94a3b8'>at {company}</font>", entry_title_style))
            story.append(Paragraph(f"{start} — {end}", entry_meta_style))
            bullets = ex.get("bullets") or []
            if bullets:
                items = [ListItem(Paragraph(b, body_style), leftIndent=12, bulletColor=PRIMARY) for b in bullets]
                story.append(ListFlowable(items, bulletType="bullet", start="•", leftIndent=6))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=4))

    # 3. Internships
    internships = p.get("internships") or []
    if internships:
        story.append(Paragraph("Internships", section_h_style))
        for i in internships:
            title = i.get("title", "")
            company = i.get("company", "")
            start = i.get("start", "")
            end = i.get("end", "")
            story.append(Paragraph(f"{title} <font color='#94a3b8'>at {company}</font>", entry_title_style))
            if start or end:
                story.append(Paragraph(f"{start} — {end}", entry_meta_style))
            bullets = i.get("bullets") or []
            if bullets:
                items = [ListItem(Paragraph(b, body_style), leftIndent=12, bulletColor=PRIMARY) for b in bullets]
                story.append(ListFlowable(items, bulletType="bullet", start="•", leftIndent=6))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=4))

    # 4. Projects
    projects = p.get("projects") or []
    if projects:
        story.append(Paragraph("Projects", section_h_style))
        for prj in projects:
            story.append(Paragraph(prj.get("name", ""), entry_title_style))
            tech = prj.get("tech") or []
            if tech:
                story.append(Paragraph(f"<font color='black'>{', '.join(tech)}</font>", entry_meta_style))
            if prj.get("description"):
                story.append(Paragraph(prj["description"], body_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=4))

    # 5. Skills
    skills_list = p.get("skills_list") or []
    if skills_list:
        skills_str = "  ·  ".join([f"{s.get('name', '')}{' (' + s.get('level', '') + ')' if s.get('level') else ''}" for s in skills_list])
        story.append(Paragraph("Skills", section_h_style))
        story.append(Paragraph(skills_str, skill_badge_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=4))

    # 6. Certifications & Courses
    certificates = p.get("certificates") or []
    if certificates:
        story.append(Paragraph("Certifications & Courses", section_h_style))
        for c in certificates:
            cert_name = c.get("name", "")
            issuer = c.get("issuer", "")
            story.append(Paragraph(f"• {cert_name}{' — ' + issuer if issuer else ''}", body_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=4))

    # 7. Miscellaneous
    misc = p.get("miscellaneous") or []
    if misc:
        story.append(Paragraph("Miscellaneous", section_h_style))
        for m in misc:
            key = m.get("key", "")
            val = m.get("value", "")
            story.append(Paragraph(f"• <b>{key}</b>: {val}", body_style))

    doc.build(story)
    buf.seek(0)

    safe_name = (name or "resume").replace(" ", "_")
    response = make_response(buf.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{safe_name}_resume.pdf"'
    return response
