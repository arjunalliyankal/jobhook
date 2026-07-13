from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from .models import UserModel
from ..extensions import mongo
import bcrypt
from bson import ObjectId

auth_bp = Blueprint("auth", __name__)
users = UserModel()


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    required = ["name", "email", "password"]
    if not all(field in data for field in required):
        return jsonify({"error": "Missing required fields"}), 400

    if data.get("password") != data.get("confirm_password"):
        return jsonify({"error": "Passwords do not match"}), 400

    if users.find_by_email(data["email"]):
        return jsonify({"error": "Email already registered"}), 409

    user_id = users.create(
        name=data["name"],
        email=data["email"],
        password=data["password"],
        target_role=data.get("target_role", "")
    )

    access_token = create_access_token(identity=str(user_id))
    refresh_token = create_refresh_token(identity=str(user_id))

    return jsonify({
        "message": "Registration successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": str(user_id)
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user = users.find_by_email(data.get("email"))

    if not user or not bcrypt.checkpw(
        data["password"].encode(), user["password_hash"].encode()
    ):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=str(user["_id"]))
    refresh_token = create_refresh_token(identity=str(user["_id"]))

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "target_role": user.get("profile", {}).get("target_role", "")
        }
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    # Verify user still exists in DB before issuing a new token
    user = users.find_by_id(identity)
    if not user:
        return jsonify({"error": "User account no longer exists"}), 401
    access_token = create_access_token(identity=identity)
    return jsonify({"access_token": access_token}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = users.find_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user["_id"] = str(user["_id"])
    user.pop("password_hash", None)
    return jsonify(user), 200
@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if "profile" in data:
        users.update_profile(user_id, data["profile"])
    
    if "name" in data:
        mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"name": data["name"]}}
        )
        
    return jsonify({"message": "Profile updated successfully"}), 200
