from datetime import datetime, timedelta, timezone

from app import db
from app.models import Business, BusinessMembership, Customer, Expense, Payment, Product, Sale, SaleItem, User
from app.services.auth_service import create_session


def _seed_business(app, user_email="owner@example.com"):
    with app.app_context():
        user = User(
            email=user_email,
            display_name="Owner",
            password_hash="hashed-password",
            is_active=True,
            email_verified_at=datetime.utcnow(),
        )
        business = Business(name="Test Business")
        membership = BusinessMembership(user=user, business=business, role="owner", status="active")
        customer = Customer(business=business, full_name="Jane Buyer", phone="08000000000")
        product = Product(
            business=business,
            name="Widget",
            category="Inventory",
            type="product",
            selling_price=250.00,
            purchase_cost=150.00,
            quantity_on_hand=12,
            reorder_level=3,
        )
        db.session.add_all([user, business, membership, customer, product])
        db.session.commit()
        return user.id, business.id, customer.id, product.id


def test_sales_payments_and_refunds_are_recorded_for_business(client, app, csrf_headers):
    user_id, business_id, customer_id, product_id = _seed_business(app)
    with app.app_context():
        user = db.session.get(User, user_id)
        _, raw_token = create_session(user)
        client.set_cookie(key=app.config["AUTH_COOKIE_NAME"], value=raw_token, domain="localhost")
        csrf = client.get("/api/v1/auth/csrf").get_json()["csrf_token"]
        headers = {"X-CSRFToken": csrf}
        response = client.post(
            f"/api/v1/businesses/{business_id}/sales",
            headers=headers,
            json={
                "customer_id": customer_id,
                "items": [{"product_id": product_id, "quantity": 2, "unit_price": "250.00"}],
                "notes": "Initial sale",
                "initial_payment_amount": "200.00",
            },
        )
        assert response.status_code == 201, response.get_data(as_text=True)
        sale_payload = response.get_json()["sale"]
        sale_id = sale_payload["id"]
        assert sale_payload["total_amount"] == "500.00"
        assert sale_payload["amount_paid"] == "200.00"

        payment_response = client.post(
            f"/api/v1/businesses/{business_id}/sales/{sale_id}/payments",
            headers=headers,
            json={"amount": "150.00", "method": "cash"},
        )
        assert payment_response.status_code == 200

        refund_response = client.post(
            f"/api/v1/businesses/{business_id}/sales/{sale_id}/refunds",
            headers=headers,
            json={"amount": "50.00", "method": "cash"},
        )
        assert refund_response.status_code == 200
        cancel_paid_sale = client.post(
            f"/api/v1/businesses/{business_id}/sales/{sale_id}/cancel",
            headers=headers,
            json={"reason": "Should require a full refund first"},
        )
        assert cancel_paid_sale.status_code == 400
        assert db.session.get(Product, product_id).quantity_on_hand == 10

        stored = db.session.get(Sale, sale_id)
        assert stored.status in {"partially_paid", "refunded"}
        assert db.session.execute(db.select(Payment)).scalars().all()
        detail = client.get(f"/api/v1/businesses/{business_id}/sales/{sale_id}")
        assert detail.get_json()["sale"]["outstanding_balance"] == "150.00"


def test_full_refund_reverses_sale_stock_and_financial_totals(client, app):
    user_id, business_id, customer_id, product_id = _seed_business(app)
    with app.app_context():
        user = db.session.get(User, user_id)
        _, raw_token = create_session(user)
        client.set_cookie(key=app.config["AUTH_COOKIE_NAME"], value=raw_token, domain="localhost")
        csrf = client.get("/api/v1/auth/csrf").get_json()["csrf_token"]
        headers = {"X-CSRFToken": csrf}
        created = client.post(
            f"/api/v1/businesses/{business_id}/sales",
            headers=headers,
            json={
                "customer_id": customer_id,
                "items": [{"product_id": product_id, "quantity": 2, "unit_price": "250.00"}],
                "initial_payment_amount": "500.00",
            },
        )
        assert created.status_code == 201
        sale_id = created.get_json()["sale"]["id"]

        refund = client.post(
            f"/api/v1/businesses/{business_id}/sales/{sale_id}/refunds",
            headers=headers,
            json={"amount": "500.00", "method": "cash"},
        )
        assert refund.status_code == 200
        detail = client.get(f"/api/v1/businesses/{business_id}/sales/{sale_id}")
        assert detail.get_json()["sale"]["status"] == "refunded"
        assert detail.get_json()["sale"]["outstanding_balance"] == "0.00"
        assert db.session.get(Product, product_id).quantity_on_hand == 12
        cancelled = client.post(
            f"/api/v1/businesses/{business_id}/sales/{sale_id}/cancel",
            headers=headers,
            json={"reason": "Duplicate action check"},
        )
        assert cancelled.status_code == 400
        assert db.session.get(Product, product_id).quantity_on_hand == 12

        summary = client.get(
            f"/api/v1/businesses/{business_id}/dashboard?range=this_month",
            headers=headers,
        ).get_json()
        assert summary["net_sales"] == "0.00"
        assert summary["cash_collected"] == "0.00"
        assert summary["cogs"] == "0.00"
        assert summary["outstanding_receivables"] == "0.00"


def test_expense_and_dashboard_summary_are_business_scoped(client, app, csrf_headers):
    user_id, business_id, customer_id, product_id = _seed_business(app)
    with app.app_context():
        user = db.session.get(User, user_id)
        _, raw_token = create_session(user)
        client.set_cookie(key=app.config["AUTH_COOKIE_NAME"], value=raw_token, domain="localhost")
        csrf = client.get("/api/v1/auth/csrf").get_json()["csrf_token"]
        headers = {"X-CSRFToken": csrf}

        sale_response = client.post(
            f"/api/v1/businesses/{business_id}/sales",
            headers=headers,
            json={
                "customer_id": customer_id,
                "items": [{"product_id": product_id, "quantity": 1, "unit_price": "250.00"}],
                "initial_payment_amount": "250.00",
            },
        )
        assert sale_response.status_code == 201

        expense = Expense(
            business_id=business_id,
            category="Operations",
            description="Rent",
            amount=120.00,
            payment_method="bank_transfer",
            expense_date=datetime.utcnow() - timedelta(days=1),
        )
        db.session.add(expense)
        db.session.commit()

        report = client.get(f"/api/v1/businesses/{business_id}/dashboard?range=this_month", headers={"X-CSRFToken": csrf})
        assert report.status_code == 200
        payload = report.get_json()
        assert payload["total_sales"] == "250.00"
        assert payload["operating_expenses"] == "120.00"
        assert payload["gross_profit"] == "100.00"
        assert payload["customer_count"] == 1
        assert payload["products_in_stock"] == 1
        assert payload["inventory_units"] == "11"
        assert any(point["sales"] == "250.00" for point in payload["trend"])
        assert any(point["expenses"] == "120.00" for point in payload["trend"])
        assert payload["recent_expenses"][0]["description"] == "Rent"
        assert any(item["type"] == "sale" for item in payload["recent_activity"])
        assert any(item["type"] == "expense" for item in payload["recent_activity"])

        expenses_response = client.get(f"/api/v1/businesses/{business_id}/expenses", headers={"X-CSRFToken": csrf})
        assert expenses_response.status_code == 200
        assert expenses_response.get_json()["expenses"]


def test_sales_search_pagination_and_custom_date_range(client, app):
    user_id, business_id, customer_id, product_id = _seed_business(app)
    with app.app_context():
        user = db.session.get(User, user_id)
        _, raw_token = create_session(user)
        client.set_cookie(key=app.config["AUTH_COOKIE_NAME"], value=raw_token, domain="localhost")
        csrf = client.get("/api/v1/auth/csrf").get_json()["csrf_token"]
        headers = {"X-CSRFToken": csrf}
        created = client.post(
            f"/api/v1/businesses/{business_id}/sales",
            headers=headers,
            json={
                "customer_id": customer_id,
                "items": [{"product_id": product_id, "quantity": 1, "unit_price": "250.00"}],
                "notes": "March market sale",
            },
        )
        assert created.status_code == 201
        today = datetime.now(timezone.utc).date().isoformat()
        listing = client.get(
            f"/api/v1/businesses/{business_id}/sales?q=March%20market&range=custom&start_date="
            f"{today}&end_date={today}&page=1&per_page=1"
        )
        assert listing.status_code == 200
        payload = listing.get_json()
        assert payload["pagination"]["total"] == 1
        assert payload["sales"][0]["customer"] == "Jane Buyer"
        assert payload["sales"][0]["reference_number"]


def test_sale_metadata_edit_status_filter_and_locked_states(client, app):
    user_id, business_id, customer_id, product_id = _seed_business(app)
    with app.app_context():
        user = db.session.get(User, user_id)
        _, raw_token = create_session(user)
        client.set_cookie(key=app.config["AUTH_COOKIE_NAME"], value=raw_token, domain="localhost")
        csrf = client.get("/api/v1/auth/csrf").get_json()["csrf_token"]
        headers = {"X-CSRFToken": csrf}

        created = client.post(
            f"/api/v1/businesses/{business_id}/sales",
            headers=headers,
            json={
                "customer_id": customer_id,
                "items": [{"product_id": product_id, "quantity": 1, "unit_price": "250.00"}],
                "notes": "Original note",
            },
        )
        assert created.status_code == 201
        sale_id = created.get_json()["sale"]["id"]

        updated = client.patch(
            f"/api/v1/businesses/{business_id}/sales/{sale_id}",
            headers=headers,
            json={"notes": "Updated note", "customer_id": None},
        )
        assert updated.status_code == 200
        assert updated.get_json()["sale"]["notes"] == "Updated note"
        assert updated.get_json()["sale"]["customer_id"] is None

        filtered = client.get(
            f"/api/v1/businesses/{business_id}/sales?status=pending",
            headers=headers,
        )
        assert filtered.status_code == 200
        assert filtered.get_json()["pagination"]["total"] == 1

        invalid_filter = client.get(
            f"/api/v1/businesses/{business_id}/sales?status=unknown",
            headers=headers,
        )
        assert invalid_filter.status_code == 400
