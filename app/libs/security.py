import hashlib
import hmac


def hash_text(text: str) -> str:
    """Calculate SHA256 hash of text."""
    return hashlib.sha256(text.encode()).hexdigest()


def secure_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    return hmac.compare_digest(a.encode(), b.encode())
