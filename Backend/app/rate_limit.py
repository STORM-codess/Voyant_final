"""
Shared rate limiter (slowapi). Limits are keyed by client IP by default.

Two tiers, both configurable via env:
  - RATE_LIMIT_DEFAULT: applied app-wide as a safety net
  - RATE_LIMIT_AI: a tighter limit decorated onto expensive AI endpoints,
    so a misbehaving client can't run up the model bill.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
)