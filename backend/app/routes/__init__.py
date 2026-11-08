"""API route blueprints."""

from flask import Blueprint

from app.routes.auth import auth
from app.routes.health import health

api = Blueprint("api", __name__)
api.register_blueprint(health)
api.register_blueprint(auth, url_prefix="/auth")
