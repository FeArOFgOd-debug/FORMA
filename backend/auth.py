from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Optional, Tuple

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, Query

from backend.config import SUPABASE_ANON_KEY, SUPABASE_AUTH_BASE_URL, SUPABASE_JWT_SECRET

logger = logging.getLogger(__name__)


@dataclass
class AuthUser:
    user_id: str
    email: Optional[str] = None


def _extract_bearer(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    token = parts[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token")
    return token


def _verify_with_jwks(token: str, issuer: str) -> AuthUser:
    jwks_url = f"{issuer}/.well-known/jwks.json"
    signing_key = jwt.PyJWKClient(jwks_url, timeout=8.0).get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=issuer,
        options={"verify_aud": False},
    )
    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("token missing sub claim")
    return AuthUser(user_id=user_id, email=payload.get("email"))


def _verify_with_secret(token: str) -> AuthUser:
    payload = jwt.decode(
        token,
        SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )
    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("token missing sub claim")
    return AuthUser(user_id=user_id, email=payload.get("email"))


def _verify_with_userinfo(token: str, issuer: str) -> Tuple[Optional[AuthUser], str]:
    """Fallback validation via Supabase Auth userinfo endpoint."""
    url = f"{issuer}/user"
    headers = {"Authorization": f"Bearer {token}"}
    if SUPABASE_ANON_KEY:
        headers["apikey"] = SUPABASE_ANON_KEY

    try:
        resp = httpx.get(url, headers=headers, timeout=10.0)
    except Exception as exc:
        logger.warning("auth_verify_userinfo_failed reason=network_error error=%s", exc)
        return None, "network_error"

    if resp.status_code != 200:
        logger.warning("auth_verify_userinfo_failed reason=status_%s", resp.status_code)
        return None, f"status_{resp.status_code}"

    try:
        body = resp.json()
    except ValueError:
        logger.warning("auth_verify_userinfo_failed reason=invalid_json")
        return None, "invalid_json"

    user_id = body.get("id") or body.get("sub")
    if not user_id:
        logger.warning("auth_verify_userinfo_failed reason=missing_user_id")
        return None, "missing_user_id"
    return AuthUser(user_id=user_id, email=body.get("email")), "ok"


def verify_supabase_token(token: str) -> AuthUser:
    if not SUPABASE_AUTH_BASE_URL:
        raise HTTPException(status_code=500, detail="SUPABASE_URL is not configured")

    if SUPABASE_JWT_SECRET:
        try:
            return _verify_with_secret(token)
        except jwt.ExpiredSignatureError:
            logger.warning("auth_verify_secret_failed reason=token_expired")
            raise HTTPException(status_code=401, detail="Invalid auth token")
        except jwt.InvalidTokenError as exc:
            logger.warning("auth_verify_secret_failed reason=invalid_token_%s", exc.__class__.__name__)
        except Exception as exc:
            logger.warning("auth_verify_secret_failed reason=%s", exc.__class__.__name__)

    issuer = SUPABASE_AUTH_BASE_URL
    jwks_reason = "unknown"
    jwks_network_failure = False

    try:
        return _verify_with_jwks(token, issuer)
    except jwt.ExpiredSignatureError:
        logger.warning("auth_verify_jwks_failed reason=token_expired")
        raise HTTPException(status_code=401, detail="Invalid auth token")
    except jwt.InvalidTokenError as exc:
        jwks_reason = f"invalid_token_{exc.__class__.__name__}"
        logger.warning("auth_verify_jwks_failed reason=%s", jwks_reason)
    except Exception as exc:
        jwks_reason = exc.__class__.__name__
        jwks_network_failure = True
        logger.warning("auth_verify_jwks_failed reason=%s", jwks_reason)

    # Some Supabase projects/environments can produce tokens that fail the local
    # JWKS path. Fallback to authoritative /auth/v1/user introspection.
    user, userinfo_reason = _verify_with_userinfo(token, issuer)
    if user:
        return user

    if jwks_network_failure and userinfo_reason == "network_error":
        raise HTTPException(status_code=503, detail="Auth verification unavailable")

    if jwks_reason.startswith("invalid_token_"):
        raise HTTPException(status_code=401, detail="Invalid auth token")

    raise HTTPException(status_code=401, detail="Invalid auth token")


def get_current_user(authorization: Optional[str] = Header(default=None)) -> AuthUser:
    token = _extract_bearer(authorization)
    return verify_supabase_token(token)


def get_current_user_with_query_token(
    authorization: Optional[str] = Header(default=None),
    access_token: Optional[str] = Query(default=None),
) -> AuthUser:
    token = access_token or _extract_bearer(authorization)
    return verify_supabase_token(token)
