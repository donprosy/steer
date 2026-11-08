"""Service health endpoint."""

from flask import Blueprint, jsonify

health = Blueprint("health", __name__)


@health.get("/health")
def get_health():
    """Return basic process health without exposing configuration."""
    return jsonify({"status": "healthy", "service": "don-prosy-business-manager"})

