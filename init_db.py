"""
Run this once to create all tables in your MySQL database:

    python init_db.py

Add --seed to also populate a couple of demo farmers, buyers, and listings:

    python init_db.py --seed
"""
import sys
from datetime import date, timedelta

from app import create_app
from extensions import db
from models import User, Listing

app = create_app()


def seed_demo_data():
    if User.query.first():
        print("Database already has data — skipping seed.")
        return

    farmer = User(
        name="Jane Wanjiru",
        email="farmer@example.com",
        role="farmer",
        phone="0712345678",
        location="Kirinyaga, Kenya",
    )
    farmer.set_password("password123")

    buyer = User(
        name="Mombasa Fresh Produce Ltd",
        email="buyer@example.com",
        role="buyer",
        phone="0798765432",
        location="Nairobi, Kenya",
    )
    buyer.set_password("password123")

    db.session.add_all([farmer, buyer])
    db.session.flush()

    listings = [
        Listing(
            farmer_id=farmer.id,
            crop_name="Fresh Tomatoes",
            category="Vegetables",
            description="Grade A tomatoes, hand-picked this week. Suitable for retail and processing.",
            quantity_available=500,
            unit="kg",
            price_per_unit=45,
            location="Kirinyaga, Kenya",
            harvest_date=date.today() - timedelta(days=2),
        ),
        Listing(
            farmer_id=farmer.id,
            crop_name="Dry Maize",
            category="Grains & Cereals",
            description="Well-dried, aflatoxin-tested maize, ready for milling.",
            quantity_available=40,
            unit="bag (90kg)",
            price_per_unit=3800,
            location="Trans Nzoia, Kenya",
            harvest_date=date.today() - timedelta(days=20),
        ),
        Listing(
            farmer_id=farmer.id,
            crop_name="French Beans",
            category="Vegetables",
            description="Export-grade French beans, sorted and ready for pickup.",
            quantity_available=120,
            unit="kg",
            price_per_unit=90,
            location="Kirinyaga, Kenya",
            harvest_date=date.today() - timedelta(days=1),
        ),
    ]
    db.session.add_all(listings)
    db.session.commit()
    print("Seeded 2 demo users (farmer@example.com / buyer@example.com, password: password123)")
    print("and 3 demo listings.")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Tables created.")
        if "--seed" in sys.argv:
            seed_demo_data()
