# admin.py
from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from decimal import Decimal
import os

from core import db, Book, CATEGORY_ORDER

admin_bp = Blueprint("admin", __name__)

def require_admin():
    if session.get("is_admin"):
        return None
    return redirect(url_for("admin.admin_login"))

@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pwd = request.form.get("password", "")
        expected = os.environ.get("ADMIN_PASSWORD", "admin123")
        if pwd == expected:
            session["is_admin"] = True
            return redirect(url_for("admin.admin"))
        else:
            flash("Incorrect password.", "error")
    return render_template("admin_login.html", categories=CATEGORY_ORDER)

@admin_bp.route("/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Logged out.", "success")
    return redirect(url_for("shop.index"))

@admin_bp.route("/")
def admin():
    if require_admin(): return require_admin()
    books = Book.query.order_by(Book.category, Book.title).all()
    return render_template("admin.html", books=books, categories=CATEGORY_ORDER)

@admin_bp.route("/new", methods=["GET", "POST"])
def admin_new():
    if require_admin(): return require_admin()
    if request.method == "POST":
        title = request.form.get("title","").strip()
        author = request.form.get("author","").strip()
        category = request.form.get("category","").strip()
        price = request.form.get("price","").strip()
        slug = request.form.get("slug","").strip() or "-".join(title.lower().split())
        image = request.form.get("image","").strip() or None
        if not title or not author or category not in CATEGORY_ORDER:
            flash("Please provide title, author, and valid category.", "error")
            return redirect(url_for("admin.admin_new"))
        try:
            p = Decimal(price)
        except:
            flash("Invalid price.", "error")
            return redirect(url_for("admin.admin_new"))
        db.session.add(Book(title=title, author=author, category=category, price=p, slug=slug, image=image))
        db.session.commit()
        flash("Book created.", "success")
        return redirect(url_for("admin.admin"))
    return render_template("admin_edit.html", book=None, categories=CATEGORY_ORDER)

@admin_bp.route("/edit/<int:book_id>", methods=["GET", "POST"])
def admin_edit(book_id):
    if require_admin(): return require_admin()
    bk = Book.query.get_or_404(book_id)
    if request.method == "POST":
        bk.title = request.form.get("title","").strip()
        bk.author = request.form.get("author","").strip()
        bk.category = request.form.get("category","").strip()
        try:
            bk.price = Decimal(request.form.get("price","0").strip())
        except:
            flash("Invalid price.", "error")
            return redirect(url_for("admin.admin_edit", book_id=bk.id))
        bk.slug = request.form.get("slug","").strip() or bk.slug
        bk.image = request.form.get("image","").strip() or None
        if bk.category not in CATEGORY_ORDER:
            flash("Invalid category.", "error")
            return redirect(url_for("admin.admin_edit", book_id=bk.id))
        db.session.commit()
        flash("Book updated.", "success")
        return redirect(url_for("admin.admin"))
    return render_template("admin_edit.html", book=bk, categories=CATEGORY_ORDER)

@admin_bp.route("/delete/<int:book_id>", methods=["POST"])
def admin_delete(book_id):
    if require_admin(): return require_admin()
    bk = Book.query.get_or_404(book_id)
    db.session.delete(bk)
    db.session.commit()
    flash("Book deleted.", "success")
    return redirect(url_for("admin.admin"))
