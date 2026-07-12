from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .scorer import calculate_ats_score
from .skill_gap import analyze_skill_gap
from ..resume.models import ResumeModel
from ..auth.models import UserModel
from ..ai.groq_client import GroqClient

ats_bp = Blueprint("ats", __name__)
resume_model = ResumeModel()
user_model = UserModel()
groq = GroqClient()


@ats_bp.route("/score", methods=["POST"])
@jwt_required()
def score():
    user_id = get_jwt_identity()
    data = request.get_json()

    resume_id = data.get("resume_id")
    jd_text = data.get("job_description", "")

    if not resume_id or not jd_text:
        return jsonify({"error": "resume_id and job_description are required"}), 400

    resume = resume_model.get_by_id(resume_id)
    if not resume:
        return jsonify({"error": "Resume not found"}), 404

    # ATS Score
    ats_result = calculate_ats_score(resume["raw_text"], jd_text)

    # Skill Gap
    target_skills = data.get("target_skills", [])
    resume_skills = resume.get("parsed", {}).get("skills", [])
    gap_result = analyze_skill_gap(resume_skills, jd_text, target_skills)

    # AI improvement suggestions
    parsed_exp = resume.get("parsed", {}).get("experience", [])
    suggestions = groq.get_resume_suggestions(
        resume_text=resume["raw_text"],
        jd_text=jd_text,
        missing_keywords=ats_result["missing_keywords"],
        score=ats_result["score"],
        parsed_experience=parsed_exp
    )

    # --- AUTOMATIC PROFILE UPDATE ---
    user_doc = user_model.find_by_id(user_id)
    if user_doc and "profile" in user_doc:
        profile = user_doc["profile"]
        
        # 1. Update summary if revised
        if suggestions.get("revised_summary"):
            profile["summary"] = suggestions["revised_summary"]
            
        # 2. Update experience if revised
        if suggestions.get("revised_experience") and isinstance(suggestions["revised_experience"], list):
            profile["experience"] = suggestions["revised_experience"]
            
        # 3. Add missing keywords to skills list
        current_skills = profile.get("skills", [])
        for kw in ats_result.get("missing_keywords", []):
            if kw not in current_skills:
                current_skills.append(kw)
        profile["skills"] = current_skills
        
        user_model.update_profile(user_id, profile)
        
        # Sync back to the active resume document too so next time we calculate ATS or view it, it's fresh
        resume_model.collection.update_one(
            {"_id": resume["_id"]},
            {"$set": {
                "parsed.summary": profile.get("summary", ""),
                "parsed.experience": profile.get("experience", []),
                "parsed.skills": profile.get("skills", [])
            }}
        )
    # ---------------------------------

    # Save ATS history to resume
    resume_model.add_ats_score(resume_id, {
        "job_description": jd_text[:500],
        "score": ats_result["score"],
        "matched_keywords": ats_result["matched_keywords"],
        "missing_keywords": ats_result["missing_keywords"]
    })

    return jsonify({
        "ats": ats_result,
        "skill_gap": gap_result,
        "suggestions": suggestions
    }), 200
