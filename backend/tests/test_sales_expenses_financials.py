from datetime import datetime, timedelta

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

        stored = db.session.get(Sale, sale_id)
        assert stored.status in {"partially_paid", "refunded"}
        assert db.session.execute(db.select(Payment)).scalars().all()


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

        expenses_response = client.get(f"/api/v1/businesses/{business_id}/expenses", headers={"X-CSRFToken": csrf})
        assert expenses_response.status_code == 200
        assert expenses_response.get_json()["expenses"]
