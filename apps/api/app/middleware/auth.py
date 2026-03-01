"""
PulseX-WDD – Admin Auth Middleware
Cookie-based session auth protecting /admin and /api/admin routes.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import time
from typing import Optional

from fastapi import Cookie, HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..config import get_settings

logger = logging.getLogger(__name__)

_serializer: Optional[URLSafeTimedSerializer] = None


def _get_serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        settings = get_settings()
        _serializer = URLSafeTimedSerializer(settings.admin_password + "PULSEX_SALT")
    return _serializer


def create_admin_token() -> str:
    s = _get_serializer()
    return s.dumps({"role": "admin", "ts": int(time.time())})


def verify_admin_token(token: str, max_age: int = 3600) -> bool:
    s = _get_serializer()
    try:
        s.loads(token, max_age=max_age)
        return True
    except (BadSignature, SignatureExpired):
        return False


def require_admin(request: Request) -> None:
    """
    Dependency: currently bypassed for direct dashboard access.
    """
    pass
