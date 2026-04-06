import os

import httpx
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from routes.ai_chat import ai_chat_bp
from routes.auth import auth_bp
from routes.goals import goals_bp
from routes.gratitude import gratitude_bp
from routes.health import health_bp
from routes.reports import reports_bp


load_dotenv()


def build_supabase_client(url: str, key: str) -> Client:
    return create_client(
        url,
        key,
        options=SyncClientOptions(
            httpx_client=httpx.Client(timeout=60.0)
        )
    )


def create_app() -> Flask:
    app = Flask(__name__, template_folder=".", static_folder=".", static_url_path="")

    # Flask-CORS for all routes
    CORS(app)

    @app.route("/")
    def index():
        return render_template("index.html")

    # JWT setup from .env
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "").strip()
    jwt = JWTManager(app)

    @jwt.unauthorized_loader
    def handle_missing_jwt(reason: str):
        return {"error": "Please log in again."}, 401

    @jwt.invalid_token_loader
    def handle_invalid_jwt(reason: str):
        return {"error": "Session is invalid. Please log in again."}, 401

    @jwt.expired_token_loader
    def handle_expired_jwt(jwt_header, jwt_payload):
        return {"error": "Session expired. Please log in again."}, 401

    # Supabase setup from .env
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_anon_key = (os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY", "")).strip()
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    supabase_auth: Client | None = None
    supabase_admin: Client | None = None

    if supabase_url and supabase_anon_key:
        supabase_auth = build_supabase_client(supabase_url, supabase_anon_key)

    if supabase_url and supabase_service_role_key:
        supabase_admin = build_supabase_client(supabase_url, supabase_service_role_key)

    app.extensions["jwt"] = jwt
    app.extensions["supabase"] = supabase_auth
    app.extensions["supabase_auth"] = supabase_auth
    app.extensions["supabase_admin"] = supabase_admin
    app.config["SUPABASE_URL"] = supabase_url
    app.config["SUPABASE_ANON_KEY"] = supabase_anon_key
    app.config["SUPABASE_SERVICE_ROLE_KEY"] = supabase_service_role_key
    app.config["HUGGINGFACE_API_KEY"] = os.getenv("HUGGINGFACE_API_KEY", "").strip()
    app.config["HUGGINGFACE_MODEL"] = os.getenv("HUGGINGFACE_MODEL", "deepseek-ai/DeepSeek-R1").strip()

    # Blueprint registration
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(goals_bp, url_prefix="/api")
    app.register_blueprint(gratitude_bp, url_prefix="/api")
    app.register_blueprint(reports_bp, url_prefix="/api")
    app.register_blueprint(ai_chat_bp, url_prefix="/api")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
