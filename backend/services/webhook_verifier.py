from __future__ import annotations

import hashlib
import hmac

GITHUB_SIGNATURE_PREFIX = "sha256="


def build_signature(payload: bytes, secret: str) -> str:
    """Return GitHub's sha256 HMAC signature for a raw webhook payload."""
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"{GITHUB_SIGNATURE_PREFIX}{digest}"


def verify_signature(
    payload: bytes,
    signature_header: str | None,
    secret: str,
) -> bool:
    """Verify a GitHub webhook signature using constant-time comparison."""
    if not payload or not signature_header or not secret:
        return False
    if not signature_header.startswith(GITHUB_SIGNATURE_PREFIX):
        return False

    expected = build_signature(payload, secret)
    return hmac.compare_digest(expected, signature_header)