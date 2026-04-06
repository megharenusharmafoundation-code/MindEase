from __future__ import annotations

from typing import Any

import httpx
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from routes.utils import as_text, error_response


ai_chat_bp = Blueprint("ai_chat", __name__)

HUGGINGFACE_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
WELLNESS_SYSTEM_PROMPT = (
    "You are MindEase AI, a calm and supportive wellness assistant. "
    "Give simple, encouraging, practical guidance about stress relief, sleep, motivation, "
    "mindfulness, routines, and general wellbeing. "
    "Do not provide medical diagnosis, emergency assessment, or treatment plans. "
    "If the user asks for medical advice, gently suggest speaking with a qualified professional. "
    "Keep responses warm, clear, and concise."
)


def get_huggingface_settings() -> tuple[str, str]:
    api_key = (current_app.config.get("HUGGINGFACE_API_KEY") or "").strip()
    model = (current_app.config.get("HUGGINGFACE_MODEL") or "").strip()

    if not api_key:
        raise RuntimeError("Hugging Face API key is not configured.")
    if not model:
        raise RuntimeError("Hugging Face model is not configured.")

    return api_key, model


def extract_reply_text(payload: dict[str, Any]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None

    message = choices[0].get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        text = content.strip()
        return text or None

    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_value = str(item.get("text") or "").strip()
                if text_value:
                    text_parts.append(text_value)
        joined = "\n".join(text_parts).strip()
        return joined or None

    return None


def build_chat_payload(user_message: str, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": WELLNESS_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 300,
        "temperature": 0.7,
    }


def call_huggingface_chat(user_message: str) -> str:
    api_key, model = get_huggingface_settings()
    payload = build_chat_payload(user_message, model)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = client.post(HUGGINGFACE_CHAT_URL, headers=headers, json=payload)

        if response.status_code >= 400:
            try:
                error_payload = response.json()
            except Exception:
                error_payload = {}
            error_message = (
                error_payload.get("error")
                or error_payload.get("message")
                or "The wellness assistant is unavailable right now."
            )
            raise RuntimeError(str(error_message))

        data = response.json()
        reply = extract_reply_text(data)
        if not reply:
            raise RuntimeError("The wellness assistant returned an empty reply.")
        return reply
    except httpx.TimeoutException as exc:
        raise RuntimeError("The wellness assistant took too long to respond. Please try again.") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError("Could not reach the wellness assistant right now. Please try again.") from exc


@ai_chat_bp.post("/chatbot")
@jwt_required()
def chatbot_reply():
    payload = request.get_json(silent=True) or {}
    user_message = as_text(payload.get("message"))

    if not user_message:
        return error_response("Please enter a message before sending.", 400)

    try:
        reply = call_huggingface_chat(user_message)
        return jsonify({"reply": reply}), 200
    except RuntimeError as exc:
        return error_response(str(exc), 503)
    except Exception as exc:
        current_app.logger.exception("Unexpected chatbot error: %s", exc)
        return error_response("Something went wrong while contacting the wellness assistant.", 500)
