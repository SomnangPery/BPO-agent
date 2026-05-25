import os
from flask import Flask, jsonify, render_template
from ic_agent.config import WEB_SECRET_KEY


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.secret_key = WEB_SECRET_KEY or os.urandom(24)

    @app.route("/")
    def index():
        return render_template("staff_chatbot.html")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
