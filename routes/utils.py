from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from flask import current_app, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity
from supabase import Client


WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def error_response(message: str, status_code: int = 400):
    return jsonify({"error": message}), status_code


def get_supabase_auth_client() -> Client | None:
    return current_app.extensions.get("supabase_auth")


def get_supabase_admin_client() -> Client | None:
    return current_app.extensions.get("supabase_admin")


def require_supabase_admin() -> Client:
    client = get_supabase_admin_client()
    if client is None:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is missing in .env")
    return client


def current_user_context() -> dict[str, str]:
    user_id = get_jwt_identity()
    claims = get_jwt()
    return {
        "id": str(user_id or ""),
        "email": str(claims.get("email") or ""),
    }


def as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return None

    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    return None


def get_today_date() -> date:
    return date.today()


def get_week_start_date(target_date: date | None = None) -> date:
    day = target_date or get_today_date()
    return day - timedelta(days=day.weekday())


def get_weekday_name(target_date: date | None = None) -> str:
    day = target_date or get_today_date()
    return WEEKDAY_NAMES[day.weekday()]
