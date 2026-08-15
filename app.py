from flask import Flask

from config import Config
from extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # If running on Vercel, the filesystem is read-only except for /tmp.
    # Use a SQLite database stored in /tmp/app.db there. Locally, default
    # to a file-based SQLite database `app.db` in the project root.
    import os

    if os.environ.get("VERCEL"):
        # Vercel provides a writable /tmp directory for ephemeral storage.
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
            "DATABASE_URL", "sqlite:////tmp/app.db"
        )
    else:
        # Local development: use a local SQLite file if DATABASE_URL isn't set.
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
            "DATABASE_URL", "sqlite:///app.db"
        )

    db.init_app(app)
    login_manager.init_app(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from auth import bp as auth_bp
    from main import bp as main_bp
    from dashboard import bp as dashboard_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp)

    @app.context_processor
    def inject_globals():
        from datetime import datetime

        return {"current_year": datetime.utcnow().year}

    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template

        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template

        return render_template("errors/404.html"), 404

    # Ensure database tables are created on startup. This runs inside the
    # application context so SQLAlchemy has access to the current app config.
    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
