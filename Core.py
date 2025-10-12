# core.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from decimal import Decimal
import os

# --- DB handle (imported by blueprints) ---
db = SQLAlchemy()

# --- Constants / Config shared across blueprints ---
TAX_RATE = Decimal("0.0825")        # 8.25% example rate
SHIPPING_FLAT = Decimal("4.99")
FREE_SHIPPING_MIN = Decimal("25.00")
PROMOS = {
    "SAVE10": {"type": "percent", "value": Decimal("0.10")},
    "READMORE15": {"type": "percent_over", "value": Decimal("0.15"), "threshold": Decimal("25.00")},
    "FREESHIP": {"type": "freeship"},
}
CATEGORY_ORDER = ["Fiction", "Non-Fiction", "Children's"]

# --- Models ---
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(40), nullable=False)  # Fiction, Non-Fiction, Children's
    price = db.Column(db.Numeric(10, 2), nullable=False)
    image = db.Column(db.String(200), nullable=True)  # path in /static

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(12), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    discount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    shipping = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    tax = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    promo_code = db.Column(db.String(40), nullable=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id_fk = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    qty = db.Column(db.Integer, nullable=False)

def seed_if_empty():
    """Seed initial books on first run."""
    if Book.query.count() > 0:
        return
    from decimal import Decimal
    books = [
        # Children's
        {"slug": "where-the-wild-things-are", "title": "Where the Wild Things are", "author": "Maurice Sendak", "category": "Children's", "price": Decimal("7.99")},
        {"slug": "the-very-hungry-caterpillar", "title": "The Very Hungry Caterpillar", "author": "Eric Carle", "category": "Children's", "price": Decimal("7.99")},
        # Fiction
        {"slug": "the-phantom-tollbooth", "title": "The Phantom Tollbooth", "author": "Norton Juster", "category": "Fiction", "price": Decimal("8.99")},
        {"slug": "caroline", "title": "Caroline", "author": "Neil Gaiman", "category": "Fiction", "price": Decimal("8.99")},
        # Non-Fiction
        {"slug": "sapiens", "title": "Sapiens", "author": "Yuval Noah Harari", "category": "Non-Fiction", "price": Decimal("9.99")},
        {"slug": "atomic-habits", "title": "Atomic Habits", "author": "James Carter", "category": "Non-Fiction", "price": Decimal("9.99")},
    ]
    for b in books:
        db.session.add(Book(**b))
    db.session.commit()

def create_app():
    app = Flask(__name__)
    app.secret_key = "dev-secret-change-me"

    # --- Config ---
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, "bookstore.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Register blueprints (import inside to avoid circular imports)
    from shop import shop_bp
    from admin import admin_bp
    app.register_blueprint(shop_bp)          # storefront at /
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Ensure tables exist at startup
    with app.app_context():
        db.create_all()
        seed_if_empty()

    return app

# Local dev entrypoint
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)


