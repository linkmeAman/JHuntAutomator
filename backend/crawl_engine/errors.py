class SourceBlockedError(Exception):
    """Raised when a source appears to block or captcha the request."""


class SourceBadConfigError(Exception):
    """Raised when configuration for a source is invalid (e.g., 404 board)."""


class SourceTransientNetworkError(Exception):
    """Raised for transient network/connection issues."""


class SourceTLSCertError(Exception):
    """Raised when TLS verification fails."""


class SourceRateLimitedError(Exception):
    """Raised when a source responds with rate limit indicators (429)."""
