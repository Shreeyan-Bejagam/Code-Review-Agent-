"""GitHub webhook signature verifier."""

import hashlib
import hmac


def verify_github_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """Verify a GitHub webhook signature using HMAC-SHA256."""

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    sent_signature = signature_header.split("=", maxsplit=1)[1]
    digest = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(sent_signature, digest)
