from flask import Blueprint, render_template, request, current_app
from sqlalchemy import or_

from extensions import db
from models import Listing, CATEGORIES, User

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    featured = (
        Listing.query.filter_by(status="active")
        .order_by(Listing.created_at.desc())
        .limit(6)
        .all()
    )
    farmer_count = User.query.filter_by(role="farmer").count()
    buyer_count = User.query.filter_by(role="buyer").count()
    active_listings = Listing.query.filter_by(status="active").count()
    return render_template(
        "index.html",
        featured=featured,
        farmer_count=farmer_count,
        buyer_count=buyer_count,
        active_listings=active_listings,
    )


@bp.route("/marketplace")
def marketplace():
    query = Listing.query.filter_by(status="active")

    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()
    page = request.args.get("page", 1, type=int)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Listing.crop_name.ilike(like), Listing.description.ilike(like))
        )
    if category:
        query = query.filter_by(category=category)
    if location:
        query = query.filter(Listing.location.ilike(f"%{location}%"))

    query = query.order_by(Listing.created_at.desc())
    pagination = query.paginate(
        page=page, per_page=current_app.config["LISTINGS_PER_PAGE"], error_out=False
    )

    return render_template(
        "marketplace/browse.html",
        pagination=pagination,
        listings=pagination.items,
        categories=CATEGORIES,
        search=search,
        selected_category=category,
        location=location,
    )


@bp.route("/marketplace/<int:listing_id>")
def listing_detail(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    related = (
        Listing.query.filter(
            Listing.category == listing.category,
            Listing.id != listing.id,
            Listing.status == "active",
        )
        .limit(3)
        .all()
    )
    return render_template("marketplace/detail.html", listing=listing, related=related)
