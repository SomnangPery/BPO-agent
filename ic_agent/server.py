import os
from flask import Flask, jsonify, render_template
from ic_agent.config import WEB_SECRET_KEY, IS_PRODUCTION


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.secret_key = WEB_SECRET_KEY
    
    # Production security settings
    if IS_PRODUCTION:
        app.config.update(
            SESSION_COOKIE_SECURE=True,
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="Lax",
            PERMANENT_SESSION_LIFETIME=3600,
        )

    @app.route("/")
    def index():
        return render_template("staff_chatbot.html")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
