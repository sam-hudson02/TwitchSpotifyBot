import hmac


def check_token(configured: str | None, presented: str | None) -> bool:
    """Constant-time comparison of the presented token against the configured
    one. False if either is missing."""
    if not configured or not presented:
        return False
    return hmac.compare_digest(configured, presented)
