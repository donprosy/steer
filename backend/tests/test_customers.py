from app import db
from app.models import Business, BusinessMembership, Customer, User
from app.services.auth_service import create_session, utc_now


CUSTOMERS_URL = "/api/v1/businesses/{business_id}/customers"


def create_business_session(app, client, role="owner"):
    with app.app_context():
        user = User(
            email=f"{role}-{id(client)}@example.test",
            display_name="Test member",
            password_hash="unused",
            email_verified_at=utc_now(),
        )
        business = Business(name="Test business")
        membership = BusinessMembership(
            business=business, user=user, role=role, status="active"
        )
        db.session.add_all([user, business, membership])
        db.session.flush()
        _, raw_session_token = create_session(user)
        business_id = business.id
        db.session.commit()
    client.set_cookie("dpbm_auth", raw_session_token)
    return business_id


def create_customer(client, csrf_headers, business_id, **overrides):
    payload = {
        "full_name": "Ada Lovelace",
        "phone": "+234 801 234 5678",
    }
    payload.update(overrides)
    return client.post(
        CUSTOMERS_URL.format(business_id=business_id),
        headers=csrf_headers,
        json=payload,
    )


def test_customer_create_profile_update_search_and_delete(
    app, client, csrf_headers
):
    business_id = create_business_session(app, client)
    created = create_customer(
        client,
        csrf_headers,
        business_id,
        email="ADA@example.com",
        address="Lagos",
        notes="Preferred contact by phone.",
    )
    assert created.status_code == 201
    customer = created.get_json()["customer"]
    assert customer["full_name"] == "Ada Lovelace"
    assert customer["email"] == "ada@example.com"
    assert customer["address"] == "Lagos"
    assert customer["business_id"] == business_id
    assert customer["created_at"].endswith("+00:00")
    assert customer["updated_at"].endswith("+00:00")

    detail = client.get(
        f"{CUSTOMERS_URL.format(business_id=business_id)}/{customer['id']}"
    )
    assert detail.status_code == 200
    assert detail.get_json()["customer"]["notes"] == "Preferred contact by phone."

    updated = client.patch(
        f"{CUSTOMERS_URL.format(business_id=business_id)}/{customer['id']}",
        headers=csrf_headers,
        json={"full_name": "Ada Byron", "email": ""},
    )
    assert updated.status_code == 200
    assert updated.get_json()["customer"]["full_name"] == "Ada Byron"
    assert updated.get_json()["customer"]["email"] is None

    searched = client.get(
        f"{CUSTOMERS_URL.format(business_id=business_id)}?q=Byron"
    )
    assert searched.status_code == 200
    assert [row["id"] for row in searched.get_json()["customers"]] == [customer["id"]]

    deleted = client.delete(
        f"{CUSTOMERS_URL.format(business_id=business_id)}/{customer['id']}",
        headers=csrf_headers,
    )
    assert deleted.status_code == 200
    assert client.get(
        f"{CUSTOMERS_URL.format(business_id=business_id)}/{customer['id']}"
    ).status_code == 404


def test_customer_list_is_paginated_and_search_is_business_scoped(
    app, client, csrf_headers
):
    business_id = create_business_session(app, client)
    for index in range(3):
        response = create_customer(
            client,
            csrf_headers,
            business_id,
            full_name=f"Customer {index}",
            phone=f"+234 801 234 567{index}",
        )
        assert response.status_code == 201

    response = client.get(
        f"{CUSTOMERS_URL.format(business_id=business_id)}?page=2&per_page=2"
    )
    assert response.status_code == 200
    assert len(response.get_json()["customers"]) == 1
    assert response.get_json()["pagination"] == {
        "page": 2,
        "per_page": 2,
        "total": 3,
        "pages": 2,
    }
    assert client.get(
        f"{CUSTOMERS_URL.format(business_id=business_id)}?q=%25"
    ).get_json()["pagination"]["total"] == 0


def test_customer_business_and_record_ids_cannot_be_substituted(
    app, client, csrf_headers
):
    business_id = create_business_session(app, client, role="owner")
    with app.app_context():
        other_business = Business(name="Other business")
        other_customer = Customer(
            business=other_business,
            full_name="Other tenant customer",
            phone="+234 801 222 3344",
        )
        db.session.add_all([other_business, other_customer])
        db.session.commit()
        inaccessible_business_id = other_business.id
        inaccessible_customer_id = other_customer.id
    customer = create_customer(client, csrf_headers, business_id)
    customer_id = customer.get_json()["customer"]["id"]

    assert client.get(
        CUSTOMERS_URL.format(business_id=inaccessible_business_id)
    ).status_code == 404
    assert client.get(
        f"{CUSTOMERS_URL.format(business_id=inaccessible_business_id)}/{customer_id}"
    ).status_code == 404
    assert client.get(
        f"{CUSTOMERS_URL.format(business_id=business_id)}/{inaccessible_customer_id}"
    ).status_code == 404
    assert create_customer(
        client, csrf_headers, inaccessible_business_id
    ).status_code == 404


def test_customer_validation_authorization_and_pagination_errors(
    app, client, csrf_headers
):
    business_id = create_business_session(app, client, role="staff")
    base_url = CUSTOMERS_URL.format(business_id=business_id)

    assert client.get(f"{base_url}?page=0").status_code == 400
    assert create_customer(
        client, csrf_headers, business_id, phone="123"
    ).status_code == 400
    assert create_customer(
        client, csrf_headers, business_id, email="not-an-email"
    ).status_code == 400
    assert create_customer(
        client, csrf_headers, business_id, full_name=""
    ).status_code == 400
    assert create_customer(
        client, csrf_headers, business_id, admin=True
    ).status_code == 400

    created = create_customer(client, csrf_headers, business_id)
    customer_id = created.get_json()["customer"]["id"]
    assert client.delete(
        f"{base_url}/{customer_id}", headers=csrf_headers
    ).status_code == 403
    assert client.patch(
        f"{base_url}/{customer_id}",
        headers=csrf_headers,
        json={"business_id": "another-business"},
    ).status_code == 400


def test_customer_routes_require_authentication_and_csrf(app, client):
    with app.app_context():
        business = Business(name="Unprotected business")
        db.session.add(business)
        db.session.commit()
        business_id = business.id
    base_url = CUSTOMERS_URL.format(business_id=business_id)

    assert client.get(base_url).status_code == 401
    response = client.post(base_url, json={"full_name": "No auth", "phone": "1234567"})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "csrf_failed"

