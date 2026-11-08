"""Authentication and business membership authorization helpers."""

from functools import wraps

from flask import g, jsonify

from app.services.auth_service import current_auth_session, membership_for_user


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        auth_session = current_auth_session()
        if auth_session is None:
            return jsonify(
                {"error": {"code": "authentication_required", "message": "Sign in is required."}}
            ), 401
        g.current_user = auth_session.user
        return view(*args, **kwargs)

    return wrapped


def require_business_role(*allowed_roles):
    """Require active membership in the route's `business_id`."""
    def decorate(view):
        @wraps(view)
        @require_auth
        def wrapped(*args, **kwargs):
            user = g.current_user
            membership = membership_for_user(user, kwargs.get("business_id"))
            if membership is None:
                return jsonify(
                    {"error": {"code": "business_access_denied", "message": "Business access is not available."}}
                ), 404
            if allowed_roles and membership.role not in allowed_roles:
                return jsonify(
                    {"error": {"code": "permission_denied", "message": "You do not have permission for this action."}}
                ), 403
            g.current_membership = membership
            return view(*args, **kwargs)

        return wrapped

    return decorate


def require_system_role(*allowed_roles):
    """Require an authenticated user to hold an allowed platform-level role."""
    def decorate(view):
        @wraps(view)
        @require_auth
        def wrapped(*args, **kwargs):
            if g.current_user.system_role not in allowed_roles:
                return jsonify(
                    {"error": {"code": "permission_denied", "message": "You do not have permission for this action."}}
                ), 403
            return view(*args, **kwargs)

        return wrapped

    return decorate
