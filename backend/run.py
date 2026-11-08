"""Local development entry point for the Flask application."""

import os

from app import create_app

app = create_app()


if __name__ == "__main__":
    if app.config["APP_ENV"] in {"production", "prod"}:
        raise RuntimeError("Use a production WSGI server; run.py is for local development.")
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5000")),
        debug=(
            os.environ.get("FLASK_DEBUG", "0") == "1"
            and app.config["APP_ENV"] not in {"production", "prod"}
        ),
    )
