import os
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

EXA_API_KEY = os.environ.get("EXA_API_KEY", "").strip()
APIFY_API_KEY = os.environ.get("APIFY_API_KEY", "").strip()
CONVEX_URL = os.environ.get("CONVEX_URL", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
_SUPABASE_URL_RAW = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "").strip()
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "").strip()

JWT_AUDIENCE = os.environ.get("JWT_AUDIENCE", "").strip() or None


def _normalize_supabase_url(raw: str) -> str:
    candidate = (raw or "").strip().strip("'\"").rstrip("/")
    if not candidate:
        return ""
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


SUPABASE_URL = _normalize_supabase_url(_SUPABASE_URL_RAW)
SUPABASE_AUTH_BASE_URL = f"{SUPABASE_URL}/auth/v1" if SUPABASE_URL else ""

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

_extra = os.environ.get("CORS_ORIGINS", "").strip()
CORS_ORIGINS: List[str] = (
    [o.strip() for o in _extra.split(",") if o.strip()]
    if _extra
    else _DEFAULT_CORS_ORIGINS
)

