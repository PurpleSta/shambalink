import os
import uuid
from decimal import Decimal, InvalidOperation
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import Listing, Order, CATEGORIES, UNITS, Subscription, SUBSCRIPTION_PLANS

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.route("/")
@login_required
def home():
    if current_user.is_farmer():
        return redirect(url_for("dashboard.farmer_dashboard"))
    return redirect(url_for("dashboard.buyer_dashboard"))


# ---------------------------------------------------------------- Farmer ---

@bp.route("/farmer")
@login_required
def farmer_dashboard():
    if not current_user.is_farmer():
        abort(403)

    listings = current_user.listings.order_by(Listing.created_at.desc()).all()
    listing_ids = [l.id for l in listings]
    incoming_orders = (
        Order.query.filter(Order.listing_id.in_(listing_ids))
        .order_by(Order.created_at.desc())
        .all()
        if listing_ids
        else []
    )

    total_revenue = sum(
        (o.total_price for o in incoming_orders if o.status == "completed"), Decimal("0")
    )
    pending_count = sum(1 for o in incoming_orders if o.status == "pending")

    return render_template(
        "dashboard/farmer.html",
        listings=listings,
        orders=incoming_orders,
        total_revenue=total_revenue,
        pending_count=pending_count,
        active_count=sum(1 for l in listings if l.status == "active"),
        subscription=current_user.current_subscription,
    )


@bp.route("/farmer/listings/new", methods=["GET", "POST"])
@login_required
def new_listing():
    if not current_user.is_farmer():
        abort(403)

    if not current_user.has_active_subscription():
        flash(
            "You need an active listing subscription before you can post produce.",
            "warning",
        )
        return redirect(url_for("dashboard.subscription"))

    if request.method == "POST":
        errors = _validate_listing_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "dashboard/listing_form.html",
                categories=CATEGORIES,
                units=UNITS,
                form=request.form,
                mode="new",
            )

        listing = Listing(
            farmer_id=current_user.id,
            crop_name=request.form["crop_name"].strip(),
            category=request.form["category"],
            description=request.form.get("description", "").strip(),
            quantity_available=Decimal(request.form["quantity_available"]),
            unit=request.form["unit"],
            price_per_unit=Decimal(request.form["price_per_unit"]),
            location=request.form["location"].strip(),
            harvest_date=_parse_date(request.form.get("harvest_date")),
        )

        image_file = request.files.get("image")
        saved_filename, error = _save_listing_image(image_file)
        if error:
            flash(error, "danger")
            return render_template(
                "dashboard/listing_form.html",
                categories=CATEGORIES,
                units=UNITS,
                form=request.form,
                mode="new",
            )
        if saved_filename:
            listing.image_filename = saved_filename

        db.session.add(listing)
        db.session.commit()
        flash(f"'{listing.crop_name}' listed on the marketplace.", "success")
        return redirect(url_for("dashboard.farmer_dashboard"))

    return render_template(
        "dashboard/listing_form.html", categories=CATEGORIES, units=UNITS, form={}, mode="new"
    )


@bp.route("/farmer/listings/<int:listing_id>/edit", methods=["GET", "POST"])
@login_required
def edit_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.farmer_id != current_user.id:
        abort(403)

    if request.method == "POST":
        errors = _validate_listing_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "dashboard/listing_form.html",
                categories=CATEGORIES,
                units=UNITS,
                form=request.form,
                mode="edit",
                listing=listing,
            )

        listing.crop_name = request.form["crop_name"].strip()
        listing.category = request.form["category"]
        listing.description = request.form.get("description", "").strip()
        listing.quantity_available = Decimal(request.form["quantity_available"])
        listing.unit = request.form["unit"]
        listing.price_per_unit = Decimal(request.form["price_per_unit"])
        listing.location = request.form["location"].strip()
        listing.harvest_date = _parse_date(request.form.get("harvest_date"))
        listing.status = request.form.get("status", listing.status)

        if request.form.get("remove_image") == "1":
            _delete_listing_image_file(listing.image_filename)
            listing.image_filename = None

        image_file = request.files.get("image")
        saved_filename, error = _save_listing_image(image_file)
        if error:
            flash(error, "danger")
            return render_template(
                "dashboard/listing_form.html",
                categories=CATEGORIES,
                units=UNITS,
                form=request.form,
                mode="edit",
                listing=listing,
            )
        if saved_filename:
            _delete_listing_image_file(listing.image_filename)
            listing.image_filename = saved_filename

        db.session.commit()
        flash(f"'{listing.crop_name}' updated.", "success")
        return redirect(url_for("dashboard.farmer_dashboard"))

    return render_template(
        "dashboard/listing_form.html",
        categories=CATEGORIES,
        units=UNITS,
        form=listing.__dict__,
        mode="edit",
        listing=listing,
    )


@bp.route("/farmer/listings/<int:listing_id>/delete", methods=["POST"])
@login_required
def delete_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    if listing.farmer_id != current_user.id:
        abort(403)
    name = listing.crop_name
    _delete_listing_image_file(listing.image_filename)
    db.session.delete(listing)
    db.session.commit()
    flash(f"'{name}' removed from the marketplace.", "info")
    return redirect(url_for("dashboard.farmer_dashboard"))


@bp.route("/farmer/orders/<int:order_id>/status", methods=["POST"])
@login_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    if order.listing.farmer_id != current_user.id:
        abort(403)

    new_status = request.form.get("status")
    if new_status not in ("pending", "confirmed", "completed", "cancelled"):
        abort(400)

    order.status = new_status
    if new_status == "confirmed" and order.listing.status == "active":
        # optional: reduce available quantity when confirmed
        pass
    db.session.commit()
    flash(f"Order #{order.id} marked as {new_status}.", "success")
    return redirect(url_for("dashboard.farmer_dashboard"))


# ------------------------------------------------------------ Subscription ---

@bp.route("/farmer/subscription")
@login_required
def subscription():
    if not current_user.is_farmer():
        abort(403)

    history = current_user.subscriptions.order_by(Subscription.created_at.desc()).all()
    return render_template(
        "dashboard/subscription.html",
        plans=SUBSCRIPTION_PLANS,
        active_subscription=current_user.current_subscription,
        pending_subscription=current_user.pending_subscription,
        history=history,
    )


@bp.route("/farmer/subscription/subscribe", methods=["POST"])
@login_required
def subscribe():
    if not current_user.is_farmer():
        abort(403)

    plan = request.form.get("plan")
    if plan not in SUBSCRIPTION_PLANS:
        flash("Please choose a valid plan.", "danger")
        return redirect(url_for("dashboard.subscription"))

    if current_user.has_active_subscription():
        flash("You already have an active subscription.", "info")
        return redirect(url_for("dashboard.subscription"))

    if current_user.pending_subscription:
        flash("You already have a subscription awaiting payment.", "info")
        return redirect(url_for("dashboard.subscription"))

    sub = Subscription(
        farmer_id=current_user.id,
        plan=plan,
        amount=SUBSCRIPTION_PLANS[plan]["amount"],
        status="pending",
    )
    db.session.add(sub)
    db.session.commit()
    flash(
        f"Subscription request created — {SUBSCRIPTION_PLANS[plan]['label']}, "
        f"KES {SUBSCRIPTION_PLANS[plan]['amount']}. Complete payment to activate it.",
        "info",
    )
    return redirect(url_for("dashboard.subscription"))


@bp.route("/farmer/subscription/<int:subscription_id>/confirm-payment", methods=["POST"])
@login_required
def confirm_subscription_payment(subscription_id):
    """
    Placeholder for real payment collection. Wire this up to an M-Pesa
    STK Push callback (or other gateway webhook) later — the callback
    handler would call sub.activate(payment_reference=...) exactly like
    this route does, instead of a person clicking a button.
    """
    if not current_user.is_farmer():
        abort(403)

    sub = Subscription.query.get_or_404(subscription_id)
    if sub.farmer_id != current_user.id:
        abort(403)
    if sub.status != "pending":
        flash("This subscription isn't awaiting payment.", "danger")
        return redirect(url_for("dashboard.subscription"))

    reference = request.form.get("payment_reference", "").strip() or "DEMO-PAYMENT"
    sub.activate(payment_reference=reference)
    db.session.commit()
    flash(
        f"Payment confirmed. Your subscription is active until {sub.end_date.strftime('%d %b %Y')}.",
        "success",
    )
    return redirect(url_for("dashboard.subscription"))


@bp.route("/farmer/subscription/<int:subscription_id>/cancel", methods=["POST"])
@login_required
def cancel_subscription(subscription_id):
    sub = Subscription.query.get_or_404(subscription_id)
    if sub.farmer_id != current_user.id:
        abort(403)
    if sub.status != "pending":
        flash("Only a subscription awaiting payment can be cancelled.", "danger")
        return redirect(url_for("dashboard.subscription"))

    sub.status = "cancelled"
    db.session.commit()
    flash("Subscription request cancelled.", "info")
    return redirect(url_for("dashboard.subscription"))


# ----------------------------------------------------------------- Buyer ---

@bp.route("/buyer")
@login_required
def buyer_dashboard():
    if not current_user.is_buyer():
        abort(403)

    orders = current_user.orders.order_by(Order.created_at.desc()).all()
    total_spent = sum(
        (o.total_price for o in orders if o.status == "completed"), Decimal("0")
    )
    return render_template(
        "dashboard/buyer.html",
        orders=orders,
        total_spent=total_spent,
        pending_count=sum(1 for o in orders if o.status == "pending"),
    )


@bp.route("/buyer/order/<int:listing_id>", methods=["POST"])
@login_required
def place_order(listing_id):
    if not current_user.is_buyer():
        abort(403)

    listing = Listing.query.get_or_404(listing_id)
    if listing.status != "active":
        flash("This listing is no longer available.", "danger")
        return redirect(url_for("main.marketplace"))

    try:
        quantity = Decimal(request.form.get("quantity", "0"))
    except InvalidOperation:
        quantity = Decimal("0")

    if quantity <= 0:
        flash("Enter a valid quantity to order.", "danger")
        return redirect(url_for("main.listing_detail", listing_id=listing.id))

    if quantity > listing.quantity_available:
        flash(
            f"Only {listing.quantity_available} {listing.unit} available.", "danger"
        )
        return redirect(url_for("main.listing_detail", listing_id=listing.id))

    order = Order(
        buyer_id=current_user.id,
        listing_id=listing.id,
        quantity=quantity,
        total_price=quantity * listing.price_per_unit,
        note=request.form.get("note", "").strip(),
    )
    listing.quantity_available -= quantity
    if listing.quantity_available <= 0:
        listing.status = "sold_out"

    db.session.add(order)
    db.session.commit()

    flash(
        f"Order placed for {quantity} {listing.unit} of {listing.crop_name}. "
        "The farmer will confirm shortly.",
        "success",
    )
    return redirect(url_for("dashboard.buyer_dashboard"))


@bp.route("/buyer/order/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id:
        abort(403)
    if order.status != "pending":
        flash("Only pending orders can be cancelled.", "danger")
        return redirect(url_for("dashboard.buyer_dashboard"))

    order.status = "cancelled"
    order.listing.quantity_available += order.quantity
    if order.listing.status == "sold_out":
        order.listing.status = "active"
    db.session.commit()
    flash(f"Order #{order.id} cancelled.", "info")
    return redirect(url_for("dashboard.buyer_dashboard"))


# --------------------------------------------------------------- helpers ---

def _validate_listing_form(form):
    errors = []
    required = ["crop_name", "category", "quantity_available", "unit", "price_per_unit", "location"]
    for field in required:
        if not form.get(field):
            errors.append(f"'{field.replace('_', ' ').title()}' is required.")

    if form.get("category") and form["category"] not in CATEGORIES:
        errors.append("Please choose a valid category.")
    if form.get("unit") and form["unit"] not in UNITS:
        errors.append("Please choose a valid unit.")

    for numeric_field in ("quantity_available", "price_per_unit"):
        value = form.get(numeric_field)
        if value:
            try:
                if Decimal(value) <= 0:
                    errors.append(f"'{numeric_field.replace('_', ' ').title()}' must be greater than zero.")
            except InvalidOperation:
                errors.append(f"'{numeric_field.replace('_', ' ').title()}' must be a number.")

    return errors


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    )


def _save_listing_image(file_storage):
    """Validate and save an uploaded image. Returns (filename, error_message)."""
    if not file_storage or not file_storage.filename:
        return None, None

    if not _allowed_image(file_storage.filename):
        return None, "Image must be a PNG, JPG, JPEG, or WEBP file."

    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    file_storage.save(os.path.join(upload_folder, filename))

    return filename, None


def _delete_listing_image_file(filename):
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
