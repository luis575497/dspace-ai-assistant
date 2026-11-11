import os

from flask import Flask
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

    from app.routes import bp
    app.register_blueprint(bp)
    return app
