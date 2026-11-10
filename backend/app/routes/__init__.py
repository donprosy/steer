"""API route blueprints."""

from flask import Blueprint

from app.routes.auth import auth
from app.routes.customers import customers
from app.routes.expenses import expenses
from app.routes.health import health
from app.routes.products import products
from app.routes.reports import reports
from app.routes.sales import sales

api = Blueprint("api", __name__)
api.register_blueprint(health)
api.register_blueprint(auth, url_prefix="/auth")
api.register_blueprint(customers, url_prefix="/businesses")
api.register_blueprint(products, url_prefix="/businesses")
api.register_blueprint(sales, url_prefix="/businesses")
api.register_blueprint(expenses, url_prefix="/businesses")
api.register_blueprint(reports, url_prefix="/businesses")
