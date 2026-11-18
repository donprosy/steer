import csv
from datetime import datetime
from io import StringIO

from app import db
from app.models import Business, BusinessMembership, Customer, Expense, User
from app.services.auth_service import create_session, utc_now


def create_business_session(app, client, role="owner"):
    with app.app_context():
        user = User(
            email=f"{role}-{id(client)}@example.test",
            display_name="Test member",
            password_hash="unused",
            email_verified_at=utc_now(),
        )
        business = Business(name="Test business")
        db.session.add_all([
            user,
            business,
            BusinessMembership(business=business, user=user, role=role, status="active"),
        ])
        db.session.flush()
        _, token = create_session(user)
        business_id = business.id
        db.session.commit()
    client.set_cookie("dpbm_auth", token)
    return business_id


def test_business_profile_is_scoped_validated_and_owner_managed(app, client, csrf_headers):
    business_id = create_business_session(app, client)
    base_url = f"/api/v1/businesses/{business_id}"

    profile = client.get(base_url)
    assert profile.status_code == 200
    assert profile.get_json()["business"]["currency"] == "NGN"

    updated = client.patch(
        base_url,
        headers=csrf_headers,
        json={
            "name": "Northstar Store",
            "industry": "Retail",
            "contact_email": "STORE@example.com",
            "phone": "+234 801 234 5678",
            "address": "Lagos",
        },
    )
    assert updated.status_code == 200
    assert updated.get_json()["business"]["name"] == "Northstar Store"
    assert updated.get_json()["business"]["contact_email"] == "store@example.com"
    assert updated.get_json()["business"]["currency"] == "NGN"

    invalid_currency = client.patch(
        base_url, headers=csrf_headers, json={"currency": "USD"}
    )
    assert invalid_currency.status_code == 400
    assert client.get("/api/v1/businesses/not-a-member").status_code == 404


def test_business_profile_requires_owner_for_updates(app, client, csrf_headers):
    business_id = create_business_session(app, client, role="manager")
    response = client.patch(
        f"/api/v1/businesses/{business_id}",
        headers=csrf_headers,
        json={"name": "Unauthorized edit"},
    )
    assert response.status_code == 403


def test_custom_date_reports_include_the_end_date_and_validate_ranges(app, client, csrf_headers):
    business_id = create_business_session(app, client)
    with app.app_context():
        db.session.add(
            Expense(
                business_id=business_id,
                category="Operations",
                description="End-of-day rent",
                amount="125.00",
                payment_method="cash",
                expense_date=datetime(2026, 3, 15, 16, 30),
            )
        )
        db.session.commit()

    base_url = f"/api/v1/businesses/{business_id}/reports"
    response = client.get(
        f"{base_url}?type=expenses&range=custom&start_date=2026-03-15&end_date=2026-03-15",
        headers=csrf_headers,
    )
    assert response.status_code == 200
    assert [row["description"] for row in response.get_json()["items"]] == ["End-of-day rent"]

    invalid = client.get(
        f"{base_url}?range=custom&start_date=2026-03-16&end_date=2026-03-15",
        headers=csrf_headers,
    )
    assert invalid.status_code == 400
    assert client.get(f"{base_url}?type=unknown").status_code == 400


def test_year_range_and_profit_loss_report_are_available(app, client, csrf_headers):
    business_id = create_business_session(app, client)
    response = client.get(
        f"/api/v1/businesses/{business_id}/reports?type=profit_loss&range=this_year",
        headers=csrf_headers,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["type"] == "profit_loss"
    assert {row["metric"] for row in payload["items"]} >= {
        "Gross sales", "Refunds", "Net sales", "Cost of goods sold",
        "Gross profit", "Operating expenses", "Net profit",
    }

    dashboard = client.get(
        f"/api/v1/businesses/{business_id}/dashboard?range=this_year",
        headers=csrf_headers,
    )
    assert dashboard.status_code == 200
    assert "trend" in dashboard.get_json()


def test_customer_csv_escapes_cells_and_prevents_formula_execution(app, client, csrf_headers):
    business_id = create_business_session(app, client)
    with app.app_context():
        db.session.add(
            Customer(
                business_id=business_id,
                full_name="=HYPERLINK(\"https://example.test\")",
                phone="08012345678",
            )
        )
        db.session.commit()

    response = client.get(
        f"/api/v1/businesses/{business_id}/reports/export?type=customers",
        headers=csrf_headers,
    )
    assert response.status_code == 200
    rows = list(csv.reader(StringIO(response.get_data(as_text=True))))
    assert rows[1][1].startswith("'=")
