# shop.py
from flask import Blueprint, render_template, redirect, url_for, session, request, flash, abort
from sqlalchemy import func
from decimal import Decimal
import uuid

from core import (
    db, Book, Order, OrderItem,
    TAX_RATE, SHIPPING_FLAT, FREE_SHIPPING_MIN, PROMOS, CATEGORY_ORDER
)

shop_bp = Blueprint("shop", __name__)

# --- Helpers (storefront-specific) ---
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
@shop_bp.route("/")
def index():
    feat = featured_book()
    return render_template("index.html", featured=feat, categories=CATEGORY_ORDER)

@shop_bp.route("/category/<category>")
def category(category):
    books = Book.query.filter(func.lower(Book.category) == category.lower()).all()
    if not books and category not in CATEGORY_ORDER:
        abort(404)
    return render_template("category.html", category=category, books=books, categories=CATEGORY_ORDER)

@shop_bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    results = []
    if q:
        like = f"%%{q.lower()}%%"
        results = Book.query.filter(
            func.lower(Book.title).like(like)
            | func.lower(Book.author).like(like)
            | func.lower(Book.category).like(like)
        ).all()
    return render_template("search.html", q=q, results=results, categories=CATEGORY_ORDER)

@shop_bp.route("/add/<slug>", methods=["POST"])
def add_to_cart(slug):
    book = Book.query.filter_by(slug=slug).first()
    if not book:
        flash("Book not found.", "error")
        return redirect(url_for("shop.index"))
    cart = get_cart()
    cart[slug] = int(cart.get(slug, 0)) + 1
    session["cart"] = cart
    flash(f"Added '{book.title}' to cart.", "success")
    return redirect(request.referrer or url_for("shop.index"))

@shop_bp.route("/cart", methods=["GET", "POST"])
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
        return redirect(url_for("shop.cart_view"))

    items, subtotal = cart_items()
    promo_code = session.get("promo_code")
    discount, promo_msg = apply_promo(subtotal, promo_code)
    ship = shipping_cost(subtotal - discount, promo_code)
    tax = ((subtotal - discount + ship) * TAX_RATE).quantize(Decimal("0.01"))
    total = (subtotal - discount + ship + tax).quantize(Decimal("0.01"))

    return render_template(
        "cart.html",
        items=items,
        subtotal=subtotal,
        discount=discount,
        shipping=ship,
        tax=tax,
        total=total,
        promo_code=promo_code,
        promo_msg=promo_msg,
        categories=CATEGORY_ORDER,
    )

@shop_bp.route("/apply-promo", methods=["POST"])
def apply_promo_route():
    code = request.form.get("promo", "").strip()
    session["promo_code"] = code or None
    return redirect(url_for("shop.cart_view"))

@shop_bp.route("/remove/<slug>", methods=["POST"])
def remove(slug):
    cart = get_cart()
    if slug in cart:
        del cart[slug]
        session["cart"] = cart
    flash("Item removed.", "success")
    return redirect(url_for("shop.cart_view"))

@shop_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, subtotal = cart_items()
    if not items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("shop.index"))

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
            return redirect(url_for("shop.checkout"))

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
            promo_code=promo_code,
        )
        db.session.add(order)
        db.session.flush()
        for it in items:
            db.session.add(
                OrderItem(
                    order_id_fk=order.id,
                    title=it["book"].title,
                    price=it["book"].price,
                    qty=it["qty"],
                )
            )
        db.session.commit()
        session["cart"] = {}
        session["last_order_id"] = order_id
        return redirect(url_for("shop.receipt", order_id=order_id))

    return render_template(
        "checkout.html",
        items=items,
        subtotal=subtotal,
        discount=discount,
        shipping=ship,
        tax=tax,
        total=total,
        categories=CATEGORY_ORDER,
    )

@shop_bp.route("/receipt/<order_id>")
def receipt(order_id):
    order = Order.query.filter_by(order_id=order_id).first()
    if not order:
        flash("Receipt not found.", "error")
        return redirect(url_for("shop.index"))
    items = OrderItem.query.filter_by(order_id_fk=order.id).all()
    return render_template("receipt.html", order=order, items=items, categories=CATEGORY_ORDER)
