# Book Nook (Flask)

A tiny bookstore demo built with Flask + SQLite.

## Run

python -m venv .venv
..venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
python app.py





\# Bookstore Flask Plus



Modular Flask app split into:

\- `core.py` – app factory, config, DB models, shared constants

\- `shop.py` – customer-facing storefront, cart, checkout

\- `admin.py` – admin login + CRUD for books



\## Run

python core.py



Visit http://127.0.0.1:5000/ and admin at /admin.



