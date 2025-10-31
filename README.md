# 📚 bookstore Flask Plus

**bookstore Flask Plus** is a modular web application built with **Flask** that simulates an online bookstore.  
It demonstrates clean software design using blueprints, data persistence with **SQLAlchemy**, and a user-friendly interface for both customers and administrators.

## 🚀 Features

### 🛍️ Storefront
- Browse books by category (Fiction, Non-Fiction, Children’s, etc.)
- Add books to a shopping cart
- Apply promo codes and calculate taxes/shipping dynamically
- Complete checkout and generate receipts

### 🧑‍💼 Admin Panel
- Secure login for administrators  
- Add, edit, and delete books through a web interface  
- Manage prices, categories, and promotions  

### ⚙️ Core Module
- Application factory pattern for flexible configuration  
- Centralized constants for tax, shipping, and discount logic  
- SQLAlchemy models for **Book**, **Order**, and **OrderItem**  
- Auto-seeding with demo data for quick startup  

## 🧩 Project Structure
bookstore_flask_plus/
├── core.py        # App factory, DB models, configuration
├── shop.py        # Customer storefront, cart, checkout
├── admin.py       # Admin blueprint for book management
├── templates/     # Jinja2
├── static/        # CSS, images, JS
├── bookstore.db   # SQLite (auto-generated)
└── requirements.txt

## 🧠 Technical Highlights
- Framework: Flask (Python 3.11+)  
- Database: SQLite via SQLAlchemy ORM  
- Templating: Jinja2 with Bootstrap styling  
- Session Management: Flask session for cart & promotions  
- Version Control: Git & GitHub for collaboration  
- Testing: Manual validation during sprint reviews (future unit tests planned)

## 🧑‍🤝‍🧑 Team Roles
- Warren Judson – Product Owner & Scrum Master  
- Torkisha Cox – Developer (Admin Module)  
- Stephen Ambrosier – Developer (Shop Module)  
- Jacquee James – Developer (Core Module)

## ▶️ How to Run (Development)
.venv\Scripts\activate
pip install -r requirements.txt
python core.py
# then open http://127.0.0.1:5000/

## 🔐 Admin Access
- URL: http://127.0.0.1:5000/admin  
- Password: admin123 (default; override via ADMIN_PASSWORD env var)

## 📝 Notes
This project was developed for a CTU group assignment (CS492) to demonstrate Scrum collaboration, modular Flask design, and GitHub workflows. The codebase is structured for clarity and instructional value while remaining production-aware.
