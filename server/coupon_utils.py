import base64
import hashlib
import hmac
import io
import random
import string

import qrcode

from config import SECRET_KEY

# Base32-friendly charset: uppercase letters without I, L, O + digits 2-9
CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_code() -> str:
    """Generate a random coupon code like EVT-A3X9-K7M2-P5Q1."""

    def random_group(length: int = 4) -> str:
        return "".join(random.choices(CHARSET, k=length))

    return f"EVT-{random_group()}-{random_group()}-{random_group()}"


def sign_coupon(code: str, event_id: int) -> str:
    """Return HMAC-SHA256 hex digest for the given coupon code and event_id."""
    message = f"{code}:{event_id}".encode("utf-8")
    key = SECRET_KEY.encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify_coupon(code: str, event_id: int, signature: str) -> bool:
    """Verify that a coupon's HMAC signature is valid (constant-time compare)."""
    expected = sign_coupon(code, event_id)
    return hmac.compare_digest(expected, signature)


def generate_qr_base64(data: str) -> str:
    """Generate a QR code for *data* and return it as a base64-encoded PNG string."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")
