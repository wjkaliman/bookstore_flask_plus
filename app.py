from flask import Flask, render_template, redirect, url_for, session, request, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from decimal import Decimal
import uuid, os

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"

# --- Config ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "bookstore.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Storefront settings
TAX_RATE = Decimal("0.0825")   # 8.25% example rate
SHIPPING_FLAT = Decimal("4.99")
FREE_SHIPPING_MIN = Decimal("25.00")
PROMOS = {
    "SAVE10": {"type": "percent", "value": Decimal("0.10")},
    "READMORE15": {"type": "percent_over", "value": Decimal("0.15"), "threshold": Decimal("25.00")},
    "FREESHIP": {"type": "freeship"},
}

db = SQLAlchemy(app)

# --- Models ---
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(40), nullable=False) # Fiction, Non-Fiction, Children's
    price = db.Column(db.Numeric(10,2), nullable=False)
    image = db.Column(db.String(200), nullable=True)  # path in /static

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(12), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    subtotal = db.Column(db.Numeric(10,2), nullable=False)
    discount = db.Column(db.Numeric(10,2), nullable=False, default=0)
    shipping = db.Column(db.Numeric(10,2), nullable=False, default=0)
    tax = db.Column(db.Numeric(10,2), nullable=False, default=0)
    total = db.Column(db.Numeric(10,2), nullable=False)
    promo_code = db.Column(db.String(40), nullable=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id_fk = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Numeric(10,2), nullable=False)
    qty = db.Column(db.Integer, nullable=False)

# --- Helpers ---
CATEGORY_ORDER = ["Fiction", "Non-Fiction", "Children's"]

def seed_if_empty():
    if Book.query.count() > 0:
        return
    # Prices by category (per user spec)
    children_price = Decimal("7.99")
    fiction_price = Decimal("8.99")
    nonfiction_price = Decimal("9.99")
    books = [
        # Children's
        {"slug": "where-the-wild-things-are", "title": "Where the Wild Things are", "author": "Maurice Sendak", "category": "Children's", "price": children_price},
        {"slug": "the-very-hungry-caterpillar", "title": "The Very Hungry Caterpillar", "author": "Eric Carle", "category": "Children's", "price": children_price},
        # Fiction
        {"slug": "the-phantom-tollbooth", "title": "The Phantom Tollbooth", "author": "Norton Juster", "category": "Fiction", "price": fiction_price},
        {"slug": "caroline", "title": "Caroline", "author": "Neil Gaiman", "category": "Fiction", "price": fiction_price},
        # Non-Fiction
        {"slug": "sapiens", "title": "Sapiens", "author": "Yuval Noah Harari", "category": "Non-Fiction", "price": nonfiction_price},
        {"slug": "atomic-habits", "title": "Atomic Habits", "author": "James Carter", "category": "Non-Fiction", "price": nonfiction_price},
    ]
    for b in books:
        bk = Book(**b)
        db.session.add(bk)
    db.session.commit()

def featured_book():
    bk = Book.query.filter_by(slug="sapiens").first()
    return bk or Book.query.first()

def get_cart():
    return session.setdefault("cart", {})  # slug -> qty

def cart_items():
    cart = get_cart()
    items = []
    subtotal = Decimal("0.00")
    for slug, qty in cart.items():
        book = Book.query.filter_by(slug=slug).first()
        if not book:
            continue
        qty = int(qty)
        price = Decimal(str(book.price))
        line_total = price * qty
        subtotal += line_total
        items.append({"book": book, "qty": qty, "line_total": line_total})
    return items, subtotal

def apply_promo(subtotal, promo_code):
    if not promo_code:
        return Decimal("0.00"), None
    code = promo_code.strip().upper()
    rule = PROMOS.get(code)
    if not rule: 
        return Decimal("0.00"), "Invalid code"
    if rule["type"] == "percent":
        return (subtotal * rule["value"]).quantize(Decimal("0.01")), None
    if rule["type"] == "percent_over":
        if subtotal >= rule["threshold"]:
            return (subtotal * rule["value"]).quantize(Decimal("0.01")), None
        else:
            return Decimal("0.00"), f"Code applies to orders ≥ ${rule['threshold']}"
    if rule["type"] == "freeship":
        return Decimal("0.00"), None
    return Decimal("0.00"), "Invalid code"

def shipping_cost(subtotal, promo_code):
    code = (promo_code or "").strip().upper()
    if code == "FREESHIP":
        return Decimal("0.00")
    if subtotal >= FREE_SHIPPING_MIN:
        return Decimal("0.00")
    return SHIPPING_FLAT

# --- Routes: Storefront ---
@app.before_request
def init_db():
    db.create_all()
    seed_if_empty()

@app.route("/")
def index():
    feat = featured_book()
    return render_template("index.html", featured=feat, categories=CATEGORY_ORDER)

@app.route("/category/<category>")
def category(category):
    books = Book.query.filter(func.lower(Book.category) == category.lower()).all()
    if not books and category not in CATEGORY_ORDER:
        abort(404)
    return render_template("category.html", category=category, books=books, categories=CATEGORY_ORDER)

@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        like = f"%%{q.lower()}%%"
        results = Book.query.filter(
            func.lower(Book.title).like(like) | func.lower(Book.author).like(like) | func.lower(Book.category).like(like)
        ).all()
    return render_template("search.html", q=q, results=results, categories=CATEGORY_ORDER)

@app.route("/add/<slug>", methods=["POST"])
def add_to_cart(slug):
    book = Book.query.filter_by(slug=slug).first()
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("index"))
    cart = get_cart()
    cart[slug] = int(cart.get(slug, 0)) + 1
    session["cart"] = cart
    flash(f"Added '{book.title}' to cart.", "success")
    return redirect(request.referrer or url_for("index"))

@app.route("/cart", methods=["GET", "POST"])
def cart_view():
    if request.method == "POST":
        cart = {}
        for key, val in request.form.items():
            if not key.startswith("qty-"): 
                continue
            slug = key.replace("qty-", "", 1)
            try:
                qty = max(0, int(val))
            except ValueError:
                qty = 0
            if qty > 0:
                cart[slug] = qty
        session["cart"] = cart
        flash("Cart updated.", "success")
        return redirect(url_for("cart_view"))
    items, subtotal = cart_items()
    promo_code = session.get("promo_code")
    discount, promo_msg = apply_promo(subtotal, promo_code)
    ship = shipping_cost(subtotal - discount, promo_code)
    tax = ((subtotal - discount + ship) * TAX_RATE).quantize(Decimal("0.01"))
    total = (subtotal - discount + ship + tax).quantize(Decimal("0.01"))
    return render_template("cart.html", items=items, subtotal=subtotal, discount=discount, shipping=ship, tax=tax, total=total,
                           promo_code=promo_code, promo_msg=promo_msg, categories=CATEGORY_ORDER)

@app.route("/apply-promo", methods=["POST"])
def apply_promo_route():
    code = request.form.get("promo", "").strip()
    session["promo_code"] = code or None
    return redirect(url_for("cart_view"))

@app.route("/remove/<slug>", methods=["POST"])
def remove(slug):
    cart = get_cart()
    if slug in cart:
        del cart[slug]
        session["cart"] = cart
    flash("Item removed.", "success")
    return redirect(url_for("cart_view"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, subtotal = cart_items()
    if not items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("index"))

    promo_code = session.get("promo_code")
    discount, _ = apply_promo(subtotal, promo_code)
    ship = shipping_cost(subtotal - discount, promo_code)
    tax = ((subtotal - discount + ship) * TAX_RATE).quantize(Decimal("0.01"))
    total = (subtotal - discount + ship + tax).quantize(Decimal("0.01"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        if not name or not email:
            flash("Please provide name and email.", "error")
            return redirect(url_for("checkout"))
        order_id = str(uuid.uuid4())[:8].upper()
        order = Order(
            order_id=order_id,
            name=name,
            email=email,
            subtotal=subtotal,
            discount=discount,
            shipping=ship,
            tax=tax,
            total=total,
            promo_code=promo_code
        )
        db.session.add(order)
        db.session.flush()
        for it in items:
            db.session.add(OrderItem(order_id_fk=order.id, title=it["book"].title, price=it["book"].price, qty=it["qty"]))        
        db.session.commit()
        session["cart"] = {}
        session["last_order_id"] = order_id
        return redirect(url_for("receipt", order_id=order_id))

    return render_template("checkout.html", items=items, subtotal=subtotal, discount=discount, shipping=ship, tax=tax, total=total, categories=CATEGORY_ORDER)

@app.route("/receipt/<order_id>")
def receipt(order_id):
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        flash("Receipt not found.", "error")
        return redirect(url_for("index"))
    items = OrderItem.query.filter_by(order_id_fk=order.id).all()
    return render_template("receipt.html", order=order, items=items, categories=CATEGORY_ORDER)

# --- Routes: Admin (demo only) ---
def require_admin():
    if session.get("is_admin"):
        return
    return redirect(url_for("admin_login"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        expected = os.environ.get("ADMIN_PASSWORD", "admin123")
        if pwd == expected:
            session["is_admin"] = True
            return redirect(url_for("admin"))
        else:
            flash("Incorrect password.", "error")
    return render_template("admin_login.html", categories=CATEGORY_ORDER)

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Logged out.", "success")
    return redirect(url_for("index"))

@app.route("/admin")
def admin():
    if require_admin(): return require_admin()
    books = Book.query.order_by(Book.category, Book.title).all()
    return render_template("admin.html", books=books, categories=CATEGORY_ORDER)

@app.route("/admin/new", methods=["GET", "POST"])
def admin_new():
    if require_admin(): return require_admin()
    if request.method == "POST":
        title = request.form.get("title","" ).strip()
        author = request.form.get("author","" ).strip()
        category = request.form.get("category","" ).strip()
        price = request.form.get("price","" ).strip()
        slug = request.form.get("slug","" ).strip() or "-".join(title.lower().split())
        image = request.form.get("image","" ).strip() or None
        if not title or not author or category not in CATEGORY_ORDER:
            flash("Please provide title, author, and valid category.", "error")
            return redirect(url_for("admin_new"))
        try:
            p = Decimal(price)
        except:
            flash("Invalid price.", "error")
            return redirect(url_for("admin_new"))
        db.session.add(Book(title=title, author=author, category=category, price=p, slug=slug, image=image))
        db.session.commit()
        flash("Book created.", "success")
        return redirect(url_for("admin"))
    return render_template("admin_edit.html", book=None, categories=CATEGORY_ORDER)

@app.route("/admin/edit/<int:book_id>", methods=["GET", "POST"])
def admin_edit(book_id):
    if require_admin(): return require_admin()
    bk = Book.query.get_or_404(book_id)
    if request.method == "POST":
        bk.title = request.form.get("title","" ).strip()
        bk.author = request.form.get("author","" ).strip()
        bk.category = request.form.get("category","" ).strip()
        try:
            bk.price = Decimal(request.form.get("price","0").strip())
        except:
            flash("Invalid price.", "error")
            return redirect(url_for("admin_edit", book_id=bk.id))
        bk.slug = request.form.get("slug","" ).strip() or bk.slug
        bk.image = request.form.get("image","" ).strip() or None
        if bk.category not in CATEGORY_ORDER:
            flash("Invalid category.", "error")
            return redirect(url_for("admin_edit", book_id=bk.id))
        db.session.commit()
        flash("Book updated.", "success")
        return redirect(url_for("admin"))
    return render_template("admin_edit.html", book=bk, categories=CATEGORY_ORDER)

@app.route("/admin/delete/<int:book_id>", methods=["POST"])
def admin_delete(book_id):
    if require_admin(): return require_admin()
    bk = Book.query.get_or_404(book_id)
    db.session.delete(bk)
    db.session.commit()
    flash("Book deleted.", "success")
    return redirect(url_for("admin"))

# --- Run ---
if __name__ == "__main__":
    app.run(debug=True)
