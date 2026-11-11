import os
import hmac
import json
from pathlib import Path

from flask import Flask, Response, request
from dotenv import load_dotenv


def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-only-change-me")
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH_MB", "30")) * 1024 * 1024
    app.config["AI_PROVIDER"] = os.getenv("AI_PROVIDER", "demo")
    app.config["OLLAMA_BASE_URL"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    app.config["OLLAMA_MODEL"] = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    app.config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    app.config["OPENAI_MODEL"] = os.getenv("OPENAI_MODEL")
    app.config["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")
    app.config["ANTHROPIC_MODEL"] = os.getenv("ANTHROPIC_MODEL")
    app.config["DSPACE_REST_URL"] = os.getenv("DSPACE_REST_URL", "").rstrip("/")
    app.config["DSPACE_EMAIL"] = os.getenv("DSPACE_EMAIL")
    app.config["DSPACE_PASSWORD"] = os.getenv("DSPACE_PASSWORD")
    app.config["DSPACE_CONFIG_PATH"] = str(Path(app.instance_path) / "dspace_config.json")
    app.config["APP_ACCESS_USER"] = os.getenv("APP_ACCESS_USER", "")
    app.config["APP_ACCESS_PASSWORD"] = os.getenv("APP_ACCESS_PASSWORD", "")

    def refresh_dspace_settings():
        try:
            with open(app.config["DSPACE_CONFIG_PATH"], encoding="utf-8") as settings_file:
                settings = json.load(settings_file)
            app.config["DSPACE_REST_URL"] = settings.get("url", "").rstrip("/")
            app.config["DSPACE_EMAIL"] = settings.get("email") or None
            app.config["DSPACE_PASSWORD"] = settings.get("password") or None
        except (OSError, ValueError):
            pass

    refresh_dspace_settings()

    @app.before_request
    def protect_application():
        refresh_dspace_settings()
        expected_user = app.config["APP_ACCESS_USER"]
        expected_password = app.config["APP_ACCESS_PASSWORD"]
        if not expected_user or not expected_password:
            if request.remote_addr in {"127.0.0.1", "::1"}:
                return None
            return Response("Access credentials are not configured.", status=503)
        credentials = request.authorization
        valid_user = credentials and hmac.compare_digest(credentials.username or "", expected_user)
        valid_password = credentials and hmac.compare_digest(credentials.password or "", expected_password)
        if valid_user and valid_password:
            return None
        return Response(
            "Authentication required.",
            status=401,
            headers={"WWW-Authenticate": 'Basic realm="DSpace Assistant"'},
        )

    from app.routes import bp
    app.register_blueprint(bp)
    return app
