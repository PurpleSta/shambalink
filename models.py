from datetime import datetime, date, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db

CATEGORIES = [
    "Vegetables",
    "Fruits",
    "Grains & Cereals",
    "Legumes",
    "Tubers & Roots",
    "Dairy & Livestock",
    "Poultry & Eggs",
    "Herbs & Spices",
]

UNITS = ["kg", "bag (90kg)", "crate", "tonne", "litre", "piece", "bunch"]

# Subscription plans: farmers pay a flat KES 2000 fee to list produce,
# renewable either every 6 months or every 12 months.
SUBSCRIPTION_PLANS = {
    "biannual": {"label": "Bi-Annual (6 months)", "days": 182, "amount": 2000},
    "annual": {"label": "Annual (12 months)", "days": 365, "amount": 2000},
}


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("farmer", "buyer", name="user_role"), nullable=False)
    phone = db.Column(db.String(30))
    location = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    listings = db.relationship(
        "Listing", backref="farmer", lazy="dynamic", cascade="all, delete-orphan"
    )
    orders = db.relationship(
        "Order", backref="buyer", lazy="dynamic", cascade="all, delete-orphan"
    )
    subscriptions = db.relationship(
        "Subscription",
        backref="farmer",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="Subscription.created_at.desc()",
    )

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def is_farmer(self):
        return self.role == "farmer"

    def is_buyer(self):
        return self.role == "buyer"

    @property
    def current_subscription(self):
        """Most recent active, non-expired subscription, if any."""
        return (
            self.subscriptions.filter_by(status="active")
            .filter(Subscription.end_date >= date.today())
            .order_by(Subscription.end_date.desc())
            .first()
        )

    @property
    def pending_subscription(self):
        return self.subscriptions.filter_by(status="pending").first()

    def has_active_subscription(self):
        return self.current_subscription is not None

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Listing(db.Model):
    __tablename__ = "listings"

    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    crop_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text)

    quantity_available = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(30), nullable=False)
    price_per_unit = db.Column(db.Numeric(10, 2), nullable=False)

    location = db.Column(db.String(120), nullable=False)
    harvest_date = db.Column(db.Date, default=date.today)
    image_filename = db.Column(db.String(255))
    status = db.Column(
        db.Enum("active", "sold_out", "inactive", name="listing_status"),
        default="active",
        nullable=False,
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    orders = db.relationship("Order", backref="listing", lazy="dynamic")

    @property
    def total_value(self):
        return self.quantity_available * self.price_per_unit

    def __repr__(self):
        return f"<Listing {self.crop_name} by farmer#{self.farmer_id}>"


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey("listings.id"), nullable=False)

    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(
        db.Enum("pending", "confirmed", "completed", "cancelled", name="order_status"),
        default="pending",
        nullable=False,
    )
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Order #{self.id} qty={self.quantity} status={self.status}>"


class Subscription(db.Model):
    """
    A farmer's paid listing subscription. Payment collection isn't wired to
    a real gateway yet — `confirm_payment()` is a stand-in for what an
    M-Pesa STK Push callback (or similar) would do once that's connected.
    """
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    plan = db.Column(db.Enum("biannual", "annual", name="subscription_plan"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)

    status = db.Column(
        db.Enum("pending", "active", "expired", "cancelled", name="subscription_status"),
        default="pending",
        nullable=False,
    )

    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    payment_reference = db.Column(db.String(120))  # e.g. M-Pesa receipt number, once wired up

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def activate(self, payment_reference=None):
        from models import SUBSCRIPTION_PLANS  # local import avoids circular ref at module load

        days = SUBSCRIPTION_PLANS[self.plan]["days"]
        self.status = "active"
        self.start_date = date.today()
        self.end_date = date.today() + timedelta(days=days)
        self.payment_reference = payment_reference

    @property
    def is_active(self):
        return self.status == "active" and self.end_date and self.end_date >= date.today()

    @property
    def days_remaining(self):
        if not self.end_date:
            return None
        return max((self.end_date - date.today()).days, 0)

    def __repr__(self):
        return f"<Subscription farmer#{self.farmer_id} plan={self.plan} status={self.status}>"
