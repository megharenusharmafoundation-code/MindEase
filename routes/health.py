from typing import Any, Callable

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from routes.utils import (
    as_float,
    as_int,
    as_text,
    current_user_context,
    error_response,
    get_today_date,
    get_week_start_date,
    get_weekday_name,
    require_supabase_admin,
)


health_bp = Blueprint("health", __name__)


STATIC_PROFILE_FIELD_PARSERS = {
    "age": as_int,
    "gender": as_text,
    "height": as_float,
    "weight": as_float,
    "diagnosed_bp": as_text,
    "diagnosed_diabetes": as_text,
    "thyroid_disorder": as_text,
    "heart_cholesterol": as_text,
    "chronic_illness": as_text,
    "family_bp": as_text,
    "family_diabetes": as_text,
    "family_heart_disease": as_text,
}

STATIC_PROFILE_FIELDS = tuple(STATIC_PROFILE_FIELD_PARSERS.keys())


PROFILE_FIELD_PARSERS = {
    **STATIC_PROFILE_FIELD_PARSERS,
    "screen_time": as_float,
    "sleep_duration": as_float,
    "feel_rested": as_text,
    "water_intake": as_float,
    "tea_coffee": as_int,
    "energy_drinks": as_text,
    "sugar_items": as_int,
    "soft_drinks": as_text,
    "junk_food": as_text,
    "alcohol": as_text,
    "smoking": as_text,
    "exercise_days": as_int,
    "exercise_duration": as_int,
    "activity_type": as_text,
    "stress_frequency": as_text,
    "social_interactions": as_int,
    "emotional_support": as_text,
}


def normalize_payload(payload: dict[str, Any], field_parsers: dict[str, Callable[[Any], Any]]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, parser in field_parsers.items():
        if key not in payload:
            continue
        data[key] = parser(payload.get(key))
    return data


def serialize_profile_fields(record: dict[str, Any] | None, field_names: tuple[str, ...]) -> dict[str, Any]:
    data = {field_name: "" for field_name in field_names}
    if not record:
        return data

    for field_name in field_names:
        value = record.get(field_name)
        data[field_name] = "" if value is None else value
    return data


def upsert_weekly_stress_record(supabase, user_id: str, stress_score: int):
    today = get_today_date()
    week_start_date = get_week_start_date(today)
    record = {
        "user_id": user_id,
        "stress_score": stress_score,
        "recorded_date": today.isoformat(),
        "day_name": get_weekday_name(today),
        "week_start_date": week_start_date.isoformat(),
    }

    # Store one stress score per user and real current date.
    return (
        supabase.table("weekly_stress")
        .upsert(record, on_conflict="user_id,recorded_date")
        .execute()
    )


def sync_weekly_stress_record(supabase, user_id: str, stress_score: int) -> None:
    try:
        upsert_weekly_stress_record(supabase, user_id, stress_score)
    except Exception as exc:
        # Keep the existing stress save flow working even if the new weekly_stress
        # table has not been created yet or is temporarily unavailable.
        current_app.logger.warning("weekly_stress sync skipped: %s", exc)


@health_bp.get("/user-profile-static")
@jwt_required()
def get_user_profile_static():
    user = current_user_context()
    if not user["id"]:
        return error_response("Invalid session", 401)

    try:
        supabase = require_supabase_admin()
        response = (
            supabase.table("user_profile_static")
            .select(",".join(STATIC_PROFILE_FIELDS))
            .eq("user_id", user["id"])
            .maybe_single()
            .execute()
        )
        return jsonify({"profile": serialize_profile_fields(response.data, STATIC_PROFILE_FIELDS)}), 200
    except Exception as exc:
        return error_response(str(exc), 500)


@health_bp.post("/user-profile-static")
@jwt_required()
def save_user_profile_static():
    payload = request.get_json(silent=True) or {}
    user = current_user_context()
    if not user["id"]:
        return error_response("Invalid session", 401)

    try:
        supabase = require_supabase_admin()
        profile_record = normalize_payload(payload, STATIC_PROFILE_FIELD_PARSERS)
        profile_record["user_id"] = user["id"]

        response = (
            supabase.table("user_profile_static")
            .upsert(profile_record, on_conflict="user_id")
            .execute()
        )
        saved = response.data[0] if response.data else profile_record
        return jsonify({"profile": serialize_profile_fields(saved, STATIC_PROFILE_FIELDS)}), 200
    except Exception as exc:
        return error_response(str(exc), 400)


@health_bp.get("/health-profile")
@jwt_required()
def get_health_profile():
    user = current_user_context()
    if not user["id"]:
        return error_response("Invalid session", 401)

    try:
        supabase = require_supabase_admin()
        response = (
            supabase.table("health_profiles")
            .select("*")
            .eq("user_id", user["id"])
            .maybe_single()
            .execute()
        )
        return jsonify({"profile": response.data}), 200
    except Exception as exc:
        return error_response(str(exc), 500)


@health_bp.post("/health-profile")
@jwt_required()
def save_health_profile():
    payload = request.get_json(silent=True) or {}
    user = current_user_context()
    if not user["id"]:
        return error_response("Invalid session", 401)

    try:
        supabase = require_supabase_admin()
        profile_record = normalize_payload(payload, PROFILE_FIELD_PARSERS)
        profile_record["user_id"] = user["id"]
        profile_record["user_email"] = user["email"]

        response = (
            supabase.table("health_profiles")
            .upsert(profile_record, on_conflict="user_id")
            .execute()
        )
        saved = response.data[0] if response.data else profile_record
        return jsonify({"profile": saved}), 200
    except Exception as exc:
        return error_response(str(exc), 400)


@health_bp.post("/daily-log")
@jwt_required()
def save_daily_log():
    payload = request.get_json(silent=True) or {}
    user = current_user_context()
    if not user["id"]:
        return error_response("Invalid session", 401)

    try:
        supabase = require_supabase_admin()
        stress_score = as_int(payload.get("stress_score"))

        log_record = {
            "user_id": user["id"],
            "log_date": as_text(payload.get("log_date")),
            "stress_score": stress_score,
            "sleep_hours": as_float(payload.get("sleep_hours")),
            "water_intake_l": as_float(payload.get("water_intake_l")),
            "bmi": as_float(payload.get("bmi")),
            "exercise_days": as_int(payload.get("exercise_days")),
        }

        profile_update = {
            "user_id": user["id"],
            "user_email": user["email"],
            "stress_score": stress_score,
            "stress_level": as_text(payload.get("stress_level")),
            "bp_risk": as_text(payload.get("bp_risk")),
            "diabetes_risk": as_text(payload.get("diabetes_risk")),
        }

        daily_log_response = (
            supabase.table("daily_logs")
            .upsert(log_record, on_conflict="user_id,log_date")
            .execute()
        )
        (
            supabase.table("health_profiles")
            .upsert(profile_update, on_conflict="user_id")
            .execute()
        )
        if stress_score is not None:
            sync_weekly_stress_record(supabase, user["id"], stress_score)

        saved = daily_log_response.data[0] if daily_log_response.data else log_record
        return jsonify({"daily_log": saved}), 200
    except Exception as exc:
        return error_response(str(exc), 400)


@health_bp.post("/stress-entries")
@jwt_required()
def save_stress_entry():
    payload = request.get_json(silent=True) or {}
    user = current_user_context()
    if not user["id"]:
        return error_response("Invalid session", 401)

    stress_level = as_int(payload.get("stress_level"))
    if stress_level is None:
        return error_response("Stress level is required", 400)
    if stress_level < 0 or stress_level > 100:
        return error_response("Stress level must be between 0 and 100", 400)

    try:
        supabase = require_supabase_admin()
        response = (
            supabase.table("stress_entries")
            .insert({
                "user_id": user["id"],
                "stress_level": stress_level,
            })
            .execute()
        )
        sync_weekly_stress_record(supabase, user["id"], stress_level)
        saved = response.data[0] if response.data else {"stress_level": stress_level}
        return jsonify({"entry": saved}), 201
    except Exception as exc:
        return error_response(str(exc), 400)
