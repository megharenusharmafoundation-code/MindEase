from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from routes.utils import as_text, current_user_context, error_response, require_supabase_admin


gratitude_bp = Blueprint("gratitude", __name__)


@gratitude_bp.post("/gratitude")
@jwt_required()
def save_gratitude():
    payload = request.get_json(silent=True) or {}
    user = current_user_context()

    if not user["id"]:
        return error_response("Invalid session", 401)

    entry_date = as_text(payload.get("entry_date"))
    if not entry_date:
        return error_response("Entry date is required", 400)

    record = {
        "user_id": user["id"],
        "item_1": as_text(payload.get("item_1")),
        "item_2": as_text(payload.get("item_2")),
        "item_3": as_text(payload.get("item_3")),
        "item_4": as_text(payload.get("item_4")),
        "item_5": as_text(payload.get("item_5")),
        "happy_moment": as_text(payload.get("happy_moment")),
        "entry_date": entry_date,
    }

    try:
        supabase = require_supabase_admin()
        response = (
            supabase.table("gratitude_entries")
            .upsert(record, on_conflict="user_id,entry_date")
            .execute()
        )
        saved = response.data[0] if response.data else record
        return jsonify({"entry": saved}), 200
    except Exception as exc:
        return error_response(str(exc), 400)
