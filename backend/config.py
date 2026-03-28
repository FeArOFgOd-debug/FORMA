import os
from pathlib import Path

from dotenv import load_dotenv

# Project root: parent of backend/
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

EXA_API_KEY = os.environ.get("EXA_API_KEY", "").strip()
APIFY_API_KEY = os.environ.get("APIFY_API_KEY", "").strip()
CONVEX_URL = os.environ.get("CONVEX_URL", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()



