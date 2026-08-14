# ShambaLink

A working MVP of a farmer-to-buyer agritech marketplace: farmers list produce, buyers browse and order directly, no broker in between. Built with **Python, Flask, MySQL, Bootstrap, and vanilla JS**, exactly as requested.

## What's included

- **Two account types**: farmer and buyer, with role-specific dashboards
- **Farmers** can create, edit, delete, and manage the status of produce listings, and confirm/fulfil incoming orders
- **Listing subscription**: farmers must have an active KES 2,000 subscription (Bi-Annual/6 months or Annual/12 months) before they can post produce. Payment collection is a placeholder for now — see "Before you go live" below.
- **Buyers** can search/filter the marketplace (by crop, category, location), view listing detail, place orders, and track/cancel pending orders
- Password hashing (Werkzeug), session auth (Flask-Login)
- Server-side validation on all forms
- A custom-designed UI on top of Bootstrap — not the default Bootstrap look

This is a functional MVP, not a production-hardened system — see "Before you go live" below.

## Project structure

```
shamba-link/
├── app.py              # Flask app factory
├── config.py            # Configuration (reads MySQL creds from .env)
├── extensions.py        # db, login_manager instances
├── models.py             # User, Listing, Order (SQLAlchemy models)
├── auth.py               # Blueprint: register / login / logout
├── main.py                # Blueprint: landing page + public marketplace browsing
├── dashboard.py            # Blueprint: farmer & buyer dashboards, listing & order actions
├── init_db.py               # Creates tables (+ optional demo data)
├── schema.sql                # Reference SQL schema (for manual DB setup/review)
├── requirements.txt
├── .env.example
├── static/
│   ├── css/style.css        # Custom design system
│   └── js/main.js
└── templates/
    ├── base.html
    ├── index.html
    ├── auth/
    ├── marketplace/
    ├── dashboard/
    └── errors/
```

## Setup

### 1. Install MySQL and create a database

Install MySQL Server if you don't have it, then:

```sql
CREATE DATABASE shamba_link CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

(`schema.sql` has the full reference schema if you'd rather create tables by hand — but you don't need to, step 4 does it for you.)

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure your database connection

```bash
cp .env.example .env
```

Edit `.env` with your real MySQL credentials:

```
SECRET_KEY=some-random-string
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=shamba_link
```

### 4. Create the tables

```bash
python init_db.py
```

Add `--seed` to also create two demo accounts and three sample listings:

```bash
python init_db.py --seed
# Farmer: farmer@example.com / password123
# Buyer:  buyer@example.com  / password123
```

### 5. Run the app

```bash
python app.py
```

Visit **http://localhost:5000**.

## Key routes

| Route | Purpose |
|---|---|
| `/` | Landing page |
| `/marketplace` | Browse/search/filter active listings |
| `/marketplace/<id>` | Listing detail + order form |
| `/auth/register`, `/auth/login`, `/auth/logout` | Auth |
| `/dashboard/farmer` | Farmer's listings + incoming orders |
| `/dashboard/farmer/listings/new` | Create a listing |
| `/dashboard/buyer` | Buyer's order history |

## Before you go live

This is an MVP scaffold, built to demonstrate and validate the core flow. Before real farmers and buyers touch it:

- **Payments**: there's no payment integration yet. In Kenya you'd likely want M-Pesa (Daraja API) for both farmer payouts and buyer payments. The subscription flow already has the right shape for this — `Subscription.activate()` in `models.py` is exactly what an M-Pesa STK Push callback should call once a payment webhook confirms success; right now a farmer just clicks a "Simulate Payment" button on `/dashboard/farmer/subscription` instead. Swap that one button for a real Daraja STK Push request + callback route and the rest of the gating logic (blocking `new_listing` for anyone without an active subscription) doesn't need to change.
- **Image uploads**: listings are text-only right now. Buyers will want photos — add file upload (e.g. to S3 or Cloudinary) plus an `image_url` column on `listings`.
- **SMS/notifications**: many smallholder farmers are more reachable by SMS than by checking a dashboard. Consider Africa's Talking or similar for order alerts.
- **Production server**: run behind Gunicorn + Nginx, not `python app.py`'s dev server.
- **Environment secrets**: never commit a real `.env`; generate a strong `SECRET_KEY`.
- **Rate limiting / spam protection** on registration and order placement.
- Per the earlier discussion: validate the single-crop, single-region flow with real transactions before expanding into inputs financing or credit scoring — this scaffold is deliberately just the marketplace layer.
