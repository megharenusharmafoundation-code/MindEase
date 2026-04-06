from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import jwt_required

from routes.utils import WEEKDAY_NAMES, current_user_context, error_response, get_today_date, get_week_start_date, get_weekday_name, require_supabase_admin


reports_bp = Blueprint("reports", __name__)


@reports_bp.get("/reports/weekly")
@jwt_required()
def weekly_reports():
    user = current_user_context()
    if not user["id"]:
        return error_response("Invalid session", 401)

    try:
        supabase = require_supabase_admin()
        start_date = (date.today() - timedelta(days=6)).isoformat()
        response = (
            supabase.table("daily_logs")
            .select("*")
            .eq("user_id", user["id"])
            .gte("log_date", start_date)
            .order("log_date")
            .execute()
        )
        return jsonify({"logs": response.data or []}), 200
    except Exception as exc:
        return error_response(str(exc), 400)


@reports_bp.get("/stress/weekly")
@jwt_required()
def weekly_stress_entries():
    user = current_user_context()
    if not user["id"]:
        return error_response("Invalid session", 401)

    today = get_today_date()
    week_start_date = get_week_start_date(today).isoformat()

    try:
        supabase = require_supabase_admin()
        response = (
            supabase.table("weekly_stress")
            .select("stress_score, recorded_date, day_name, week_start_date")
            .eq("user_id", user["id"])
            .eq("week_start_date", week_start_date)
            .order("recorded_date")
            .execute()
        )

        scores_by_day = {
            row["day_name"]: row["stress_score"]
            for row in (response.data or [])
            if row.get("day_name") in WEEKDAY_NAMES
        }
        values = [scores_by_day.get(day_name) for day_name in WEEKDAY_NAMES]

        return jsonify({
            "labels": WEEKDAY_NAMES,
            "values": values,
            "today_day": get_weekday_name(today),
            "week_start_date": week_start_date,
            "entries": response.data or [],
        }), 200
    except Exception as exc:
        current_app.logger.warning("weekly_stress fetch failed, falling back to stress_entries: %s", exc)

        try:
            supabase = require_supabase_admin()
            start_timestamp = datetime.combine(
                get_week_start_date(today),
                datetime.min.time(),
                tzinfo=timezone.utc,
            ).isoformat()
            fallback_response = (
                supabase.table("stress_entries")
                .select("stress_level, created_at")
                .eq("user_id", user["id"])
                .gte("created_at", start_timestamp)
                .order("created_at")
                .execute()
            )

            scores_by_day: dict[str, int] = {}
            for row in (fallback_response.data or []):
                created_at = row.get("created_at")
                stress_level = row.get("stress_level")
                if not created_at or stress_level is None:
                    continue

                recorded_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                day_name = WEEKDAY_NAMES[recorded_at.weekday()]
                scores_by_day[day_name] = int(stress_level)

            values = [scores_by_day.get(day_name) for day_name in WEEKDAY_NAMES]
            return jsonify({
                "labels": WEEKDAY_NAMES,
                "values": values,
                "today_day": get_weekday_name(today),
                "week_start_date": week_start_date,
                "entries": fallback_response.data or [],
            }), 200
        except Exception as fallback_exc:
            return error_response(str(fallback_exc), 400)
