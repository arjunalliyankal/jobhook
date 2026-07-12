from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import ApplicationModel
from ..extensions import mongo
from bson import ObjectId

tracker_bp = Blueprint("tracker", __name__)
app_model = ApplicationModel()


@tracker_bp.route("/applications", methods=["GET"])
@jwt_required()
def get_applications():
    user_id = get_jwt_identity()
    apps = app_model.get_by_user(user_id)
    
    for app in apps:
        if app.get("job_id"):
            try:
                job = mongo.db.jobs.find_one({"_id": ObjectId(app["job_id"])})
                if not job:
                    # Try scraped_jobs collection
                    job = mongo.db.scraped_jobs.find_one({"_id": ObjectId(app["job_id"])})
                if job:
                    job["_id"] = str(job["_id"])
                    app["job"] = job
            except Exception:
                pass
    
    return jsonify(apps), 200


@tracker_bp.route("/applications", methods=["POST"])
@jwt_required()
def create_application():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    app_id = app_model.create(
        user_id=user_id,
        job_id=data.get("job_id"),
        resume_id=data.get("resume_id"),
        cover_letter_id=data.get("cover_letter_id"),
        ats_score=data.get("ats_score", 0),
        notes=data.get("notes", "")
    )
    
    return jsonify({"message": "Application saved", "application_id": app_id}), 201


@tracker_bp.route("/applications/<app_id>/status", methods=["PATCH"])
@jwt_required()
def update_status(app_id):
    data = request.get_json()
    status = data.get("status")
    
    if not status:
        return jsonify({"error": "Status is required"}), 400
        
    app_model.update_status(app_id, status)
    return jsonify({"message": "Status updated successfully"}), 200


@tracker_bp.route("/applications/<app_id>", methods=["DELETE"])
@jwt_required()
def delete_application(app_id):
    user_id = get_jwt_identity()
    app_model.delete(app_id, user_id)
    return jsonify({"message": "Application deleted"}), 200
