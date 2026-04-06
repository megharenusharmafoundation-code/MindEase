from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required

from routes.utils import current_user_context, error_response, get_supabase_auth_client


auth_bp = Blueprint("auth", __name__)


def build_auth_payload(user) -> dict:
    return {
        "id": getattr(user, "id", ""),
        "email": getattr(user, "email", ""),
    }


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return error_response("Email and password are required", 400)

    supabase = get_supabase_auth_client()
    if supabase is None:
        return error_response("Supabase auth client is not configured", 500)

    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        response_error = getattr(response, "error", None)
        if response_error:
            return error_response(str(response_error), 400)

        user = getattr(response, "user", None)
        session = getattr(response, "session", None)
        if user is not None and session is not None:
            app_token = create_access_token(
                identity=getattr(user, "id", ""),
                additional_claims={"email": getattr(user, "email", "")}
            )
            return jsonify({
                "message": "Registration successful",
                "access_token": app_token,
                "user": build_auth_payload(user),
            }), 201

        return jsonify({"message": "Registration successful. Please log in."}), 201
    except Exception as exc:
        return error_response(str(exc), 400)


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return error_response("Email and password are required", 400)

    supabase = get_supabase_auth_client()
    if supabase is None:
        return error_response("Supabase auth client is not configured", 500)

    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        session = getattr(response, "session", None)
        user = getattr(response, "user", None)
        if session is None or user is None:
            return error_response("Invalid credentials", 401)

        app_token = create_access_token(
            identity=getattr(user, "id", ""),
            additional_claims={"email": getattr(user, "email", "")}
        )
        return jsonify({
            "access_token": app_token,
            "user": build_auth_payload(user),
        }), 200
    except Exception as exc:
        return error_response(str(exc) or "Invalid credentials", 401)


@auth_bp.get("/me")
@jwt_required()
def me():
    user = current_user_context()
    if not user["id"]:
        return error_response("Invalid session", 401)
    return jsonify({"user": {"id": user["id"], "email": user["email"]}}), 200
