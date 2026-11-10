from app import db
from app.models import Business, BusinessMembership, Product, User
from app.services.auth_service import create_session, utc_now

PRODUCTS_URL = "/api/v1/businesses/{business_id}/products"


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


def create_product(client, csrf_headers, business_id, **overrides):
    payload = {
        "name": "Premium rice bag",
        "category": "Groceries",
        "type": "product",
        "sku": "RICE-001",
        "selling_price": "5000.00",
        "purchase_cost": "3500.00",
        "quantity_on_hand": "24",
        "reorder_level": "10",
        "stock_unit": "bag",
    }
    payload.update(overrides)
    return client.post(
        PRODUCTS_URL.format(business_id=business_id),
        headers=csrf_headers,
        json=payload,
    )


def test_product_create_update_inventory_and_history(app, client, csrf_headers):
    business_id = create_business_session(app, client, role="owner")
    created = create_product(
        client,
        csrf_headers,
        business_id,
        category="Food staples",
        quantity_on_hand="12",
        reorder_level="5",
    )
    assert created.status_code == 201
    product = created.get_json()["product"]
    assert product["name"] == "Premium rice bag"
    assert product["category"] == "Food staples"
    assert product["quantity_on_hand"] == "12"
    assert product["reorder_level"] == "5"
    assert product["type"] == "product"

    adjusted = client.post(
        f"{PRODUCTS_URL.format(business_id=business_id)}/{product['id']}/stock-adjustment",
        headers=csrf_headers,
        json={"delta_quantity": -2, "reason": "sale", "note": "Sold in a small retail batch"},
    )
    assert adjusted.status_code == 200
    movement = adjusted.get_json()["movement"]
    assert movement["delta_quantity"] == "-2"
    assert movement["reason"] == "sale"
    product_after = adjusted.get_json()["product"]
    assert product_after["quantity_on_hand"] == "10"

    detail = client.get(
        f"{PRODUCTS_URL.format(business_id=business_id)}/{product['id']}"
    )
    assert detail.status_code == 200
    assert len(detail.get_json()["movements"]) >= 1

    updated = client.patch(
        f"{PRODUCTS_URL.format(business_id=business_id)}/{product['id']}",
        headers=csrf_headers,
        json={"name": "Premium rice sack", "selling_price": "5500"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["product"]["name"] == "Premium rice sack"
    assert updated.get_json()["product"]["selling_price"] == "5500.00"


def test_product_list_filters_low_stock_and_services_are_not_physical_inventory(
    app, client, csrf_headers
):
    business_id = create_business_session(app, client, role="owner")
    create_product(
        client,
        csrf_headers,
        business_id,
        name="Yam bag",
        sku="YAM-001",
        quantity_on_hand="6",
        reorder_level="10",
    )
    create_product(
        client,
        csrf_headers,
        business_id,
        name="Consulting session",
        type="service",
        category="Services",
        selling_price="2500.00",
        quantity_on_hand="99",
        reorder_level="2",
        stock_unit="service",
    )

    low_stock = client.get(
        f"{PRODUCTS_URL.format(business_id=business_id)}?low_stock=true"
    )
    assert low_stock.status_code == 200
    assert low_stock.get_json()["pagination"]["total"] == 1
    names = [row["name"] for row in low_stock.get_json()["products"]]
    assert names == ["Yam bag"]

    created_service = create_product(
        client,
        csrf_headers,
        business_id,
        name="Delivery fee",
        type="service",
        category="Services",
        selling_price="800.00",
        quantity_on_hand="20",
    )
    assert created_service.status_code == 201
    service = created_service.get_json()["product"]
    assert service["type"] == "service"
    assert service["quantity_on_hand"] == "0"
    assert service["stock_unit"] == "service"


def test_product_business_isolation_and_staff_permissions(app, client, csrf_headers):
    business_id = create_business_session(app, client, role="staff")
    base_url = PRODUCTS_URL.format(business_id=business_id)

    product_response = create_product(client, csrf_headers, business_id)
    assert product_response.status_code == 403

    list_response = client.get(base_url)
    assert list_response.status_code == 200

    with app.app_context():
        other_business = Business(name="Other business")
        other_product = Product(
            business=other_business,
            name="Other product",
            category="Other",
            type="product",
            selling_price="100.00",
            purchase_cost="50.00",
            quantity_on_hand="3",
            reorder_level="1",
        )
        db.session.add_all([other_business, other_product])
        db.session.commit()
        inaccessible_business_id = other_business.id
        inaccessible_product_id = other_product.id

    assert client.get(
        f"/api/v1/businesses/{inaccessible_business_id}/products"
    ).status_code == 404
    assert client.get(
        f"/api/v1/businesses/{business_id}/products/{inaccessible_product_id}"
    ).status_code == 404
    assert client.post(
        f"/api/v1/businesses/{business_id}/products/{inaccessible_product_id}/archive",
        headers=csrf_headers,
    ).status_code == 403


def test_product_routes_require_authentication_and_csrf(app, client):
    with app.app_context():
        business = Business(name="Unprotected business")
        db.session.add(business)
        db.session.commit()
        business_id = business.id

    response = client.post(
        PRODUCTS_URL.format(business_id=business_id),
        json={"name": "No auth", "category": "Safety", "selling_price": "10000"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "csrf_failed"
