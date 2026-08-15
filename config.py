import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-this-in-production")

    # --- MySQL connection settings ---
    # Set these in a .env file (see .env.example) or as real environment variables.
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
    MYSQL_DB = os.environ.get("MYSQL_DB", "shamba_link")

    # Prefer an explicit DATABASE_URL when provided (e.g. on production).
    # Otherwise fall back to a local SQLite file so the app can start without
    # requiring a hosted MySQL instance during quick deploys / demos.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'shamba.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Engine options: helpful for serverless or pooled environments.
    # These options are passed to SQLAlchemy's create_engine and can
    # reduce stale-connection errors when the app is deployed to Vercel.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 5,
        "max_overflow": 10,
    }

    # Pagination
    LISTINGS_PER_PAGE = 9

    # Image uploads
    UPLOAD_FOLDER = os.path.join(basedir, "static", "uploads")
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload size
