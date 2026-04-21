import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

DB_PATH = BASE_DIR / "coupons.db"
SECRET_KEY = os.environ.get("COUPON_SECRET_KEY", "change-me-in-production-please")
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
ADMIN_PIN = os.environ.get("ADMIN_PIN", "1234")
