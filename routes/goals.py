from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from routes.utils import as_bool, as_text, current_user_context, error_response, require_supabase_admin


goals_bp = Blueprint("goals", __name__)

# The Goals page always shows these same wellness goals.
PREDEFINED_GOALS = [
    "Sleep at least 7\u20138 hours",
    "Drink 2\u20133 liters of water",
    "Walk at least 5000 steps",
    "Limit sugary foods",
    "Practice mindfulness (5\u201310 min)",
]

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def get_today_iso() -> str:
    return date.today().isoformat()


def get_week_start_iso() -> str:
    today = date.today()
    return (today - timedelta(days=today.weekday())).isoformat()


def serialize_daily_goal(goal_name: str, is_completed: bool, goal_date: str) -> dict:
    return {
        "goal_name": goal_name,
        "is_completed": bool(is_completed),
        "goal_date": goal_date,
    }


def serialize_weekly_goal(day_name: str, goal_name: str, is_completed: bool, week_start_date: str) -> dict:
    return {
        "day_name": day_name,
        "goal_name": goal_name,
        "is_completed": bool(is_completed),
        "week_start_date": week_start_date,
    }


def validate_goal_name(goal_name: str | None) -> str:
    normalized = (goal_name or "").strip()
    if normalized not in PREDEFINED_GOALS:
        raise ValueError("Please choose a valid predefined goal")
    return normalized


def validate_day_name(day_name: str | None) -> str:
    normalized = (day_name or "").strip().title()
    if normalized not in WEEKDAYS:
        raise ValueError("Please choose a valid weekday")
    return normalized


def build_daily_goals(status_by_goal: dict[str, bool], goal_date: str) -> list[dict]:
    return [
        serialize_daily_goal(goal_name, status_by_goal.get(goal_name, False), goal_date)
        for goal_name in PREDEFINED_GOALS
    ]


def build_weekly_goals(status_by_day_and_goal: dict[tuple[str, str], bool], week_start_date: str) -> dict[str, list[dict]]:
    grouped_goals: dict[str, list[dict]] = {}
    for day_name in WEEKDAYS:
        grouped_goals[day_name] = [
            serialize_weekly_goal(
                day_name,
                goal_name,
                status_by_day_and_goal.get((day_name, goal_name), False),
                week_start_date,
            )
            for goal_name in PREDEFINED_GOALS
        ]
    return grouped_goals


@goals_bp.get("/goals")
@jwt_required()
def get_goals():
    user = current_user_context()
    if not user["id"]:
        return error_response("Invalid session", 401)

    today = get_today_iso()
    week_start_date = get_week_start_iso()

    try:
        supabase = require_supabase_admin()

        daily_response = (
            supabase.table("daily_goal_status")
            .select("goal_name, is_completed")
            .eq("user_id", user["id"])
            .eq("goal_date", today)
            .execute()
        )
        weekly_response = (
            supabase.table("weekly_goal_status")
            .select("day_name, goal_name, is_completed")
            .eq("user_id", user["id"])
            .eq("week_start_date", week_start_date)
            .execute()
        )

        daily_status_by_goal = {
            row["goal_name"]: bool(row.get("is_completed"))
            for row in (daily_response.data or [])
            if row.get("goal_name") in PREDEFINED_GOALS
        }
        weekly_status_by_day_and_goal = {
            (row["day_name"], row["goal_name"]): bool(row.get("is_completed"))
            for row in (weekly_response.data or [])
            if row.get("day_name") in WEEKDAYS and row.get("goal_name") in PREDEFINED_GOALS
        }

        return jsonify(
            {
                "today": today,
                "week_start_date": week_start_date,
                "daily_goals": build_daily_goals(daily_status_by_goal, today),
                "weekly_goals": build_weekly_goals(weekly_status_by_day_and_goal, week_start_date),
                "predefined_goals": PREDEFINED_GOALS,
                "weekdays": WEEKDAYS,
            }
        ), 200
    except Exception as exc:
        return error_response(str(exc), 500)


@goals_bp.put("/goals/daily-status")
@jwt_required()
def save_daily_goal_status():
    payload = request.get_json(silent=True) or {}
    user = current_user_context()
    if not user["id"]:
        return error_response("Invalid session", 401)

    try:
        goal_name = validate_goal_name(as_text(payload.get("goal_name")))
        is_completed = as_bool(payload.get("is_completed"))
        if is_completed is None:
            raise ValueError("Completion state is required")

        goal_date = get_today_iso()
        record = {
            "user_id": user["id"],
            "goal_name": goal_name,
            "is_completed": is_completed,
            "goal_date": goal_date,
        }

        supabase = require_supabase_admin()
        response = (
            supabase.table("daily_goal_status")
            .upsert(record, on_conflict="user_id,goal_name,goal_date")
            .execute()
        )
        saved = response.data[0] if response.data else record

        return jsonify(
            {
                "status": serialize_daily_goal(
                    saved.get("goal_name", goal_name),
                    bool(saved.get("is_completed", is_completed)),
                    str(saved.get("goal_date", goal_date)),
                )
            }
        ), 200
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception as exc:
        return error_response(str(exc), 500)


@goals_bp.put("/goals/weekly-status")
@jwt_required()
def save_weekly_goal_status():
    payload = request.get_json(silent=True) or {}
    user = current_user_context()
    if not user["id"]:
        return error_response("Invalid session", 401)

    try:
        day_name = validate_day_name(as_text(payload.get("day_name")))
        goal_name = validate_goal_name(as_text(payload.get("goal_name")))
        is_completed = as_bool(payload.get("is_completed"))
        if is_completed is None:
            raise ValueError("Completion state is required")

        week_start_date = get_week_start_iso()
        record = {
            "user_id": user["id"],
            "day_name": day_name,
            "goal_name": goal_name,
            "is_completed": is_completed,
            "week_start_date": week_start_date,
        }

        supabase = require_supabase_admin()
        response = (
            supabase.table("weekly_goal_status")
            .upsert(record, on_conflict="user_id,day_name,goal_name,week_start_date")
            .execute()
        )
        saved = response.data[0] if response.data else record

        return jsonify(
            {
                "status": serialize_weekly_goal(
                    saved.get("day_name", day_name),
                    saved.get("goal_name", goal_name),
                    bool(saved.get("is_completed", is_completed)),
                    str(saved.get("week_start_date", week_start_date)),
                )
            }
        ), 200
    except ValueError as exc:
        return error_response(str(exc), 400)
    except Exception as exc:
        return error_response(str(exc), 500)
