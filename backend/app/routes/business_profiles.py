"""Tenant-scoped business profile endpoints."""

import re

from flask import Blueprint, jsonify, request

from app import db
from app.models import Business
from app.security import require_business_role
from app.services.auth_service import AccountInputError, normalize_email

business_profiles = Blueprint("business_profiles", __name__)
PHONE_PATTERN = re.compile(r"\+?[\d\s().-]+")
PROFILE_FIELDS = {"name", "industry", "contact_email", "phone", "address"}


def error_response(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status


def serialize_business(business):
    return {
        "id": business.id,
        "name": business.name,
        "industry": business.industry,
        "contact_email": business.contact_email,
        "phone": business.phone,
        "address": business.address,
        "currency": business.currency,
        "updated_at": business.updated_at.isoformat(),
    }


def validate_profile(payload):
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Provide at least one profile field to update.")
    unknown_fields = set(payload) - PROFILE_FIELDS
    if unknown_fields:
        raise ValueError(f"Unsupported business field: {sorted(unknown_fields)[0]}.")

    data = {}
    for field, maximum in (
        ("name", 160),
        ("industry", 80),
        ("contact_email", 254),
        ("phone", 32),
        ("address", 500),
    ):
        if field not in payload:
            continue
        value = payload[field]
        if value is None and field != "name":
            data[field] = None
            continue
        if not isinstance(value, str):
            raise ValueError(f"{field.replace('_', ' ').capitalize()} must be text.")
        value = value.strip()
        if not value:
            if field == "name":
                raise ValueError("Business name is required.")
            data[field] = None
            continue
        if len(value) > maximum:
            raise ValueError(f"{field.replace('_', ' ').capitalize()} must be {maximum} characters or fewer.")
        if field == "contact_email":
            try:
                value = normalize_email(value)
            except AccountInputError as error:
                raise ValueError("Enter a valid contact email address.") from error
        if field == "phone":
            digits = sum(character.isdigit() for character in value)
            if not PHONE_PATTERN.fullmatch(value) or not 7 <= digits <= 18:
                raise ValueError("Enter a valid business phone number.")
        data[field] = value
    return data


@business_profiles.get("/<business_id>")
@require_business_role()
def get_business_profile(business_id):
    business = db.session.get(Business, business_id)
    return jsonify({"business": serialize_business(business)})


@business_profiles.patch("/<business_id>")
@require_business_role("owner")
def update_business_profile(business_id):
    try:
        data = validate_profile(request.get_json(silent=True))
    except ValueError as error:
        return error_response("validation_error", str(error), 400)

    business = db.session.get(Business, business_id)
    for field, value in data.items():
        setattr(business, field, value)
    db.session.commit()
    return jsonify({"business": serialize_business(business)})
