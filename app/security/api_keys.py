from __future__ import annotations

import hashlib
import hmac
import secrets


_HASH_NAME = "pbkdf2_sha256"
_ITERATIONS = 260_000


def generate_api_key(prefix: str = "tidp") -> str:
    normalized_prefix = "".join(ch for ch in str(prefix or "tidp").lower() if ch.isalnum())
    if not normalized_prefix:
        normalized_prefix = "tidp"
    return f"{normalized_prefix}_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    if not api_key:
        raise ValueError("api_key is required")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", api_key.encode("utf-8"), salt, _ITERATIONS)
    return f"{_HASH_NAME}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_api_key(api_key: str, encoded_hash: str) -> bool:
    if not api_key or not encoded_hash:
        return False
    try:
        algorithm, iterations_raw, salt_hex, expected_hex = encoded_hash.split("$", 3)
        iterations = int(iterations_raw)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
    except (TypeError, ValueError):
        return False
    if algorithm != _HASH_NAME:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", api_key.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)
