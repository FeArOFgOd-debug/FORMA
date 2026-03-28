from __future__ import annotations

import argparse
import json
import sys
import warnings
from typing import Any

from backend.config import EXA_API_KEY

warnings.filterwarnings(
    "ignore",
    message=r".*urllib3 .* doesn't match a supported version.*",
    category=Warning,
)

from exa_py import Exa


def search_web_deep(
    prompt: str,
    *,
    num_results: int = 10,
    max_characters: int = 20000,
    search_type: str = "deep",
) -> list[dict[str, Any]]:
    """Run an Exa search for a prompt and return normalized results."""
    if not EXA_API_KEY:
        raise ValueError("EXA_API_KEY is missing. Add it to your .env file.")

    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    exa = Exa(api_key=EXA_API_KEY)
    response = exa.search_and_contents(
        prompt.strip(),
        type=search_type,
        num_results=num_results,
        text={"max_characters": max_characters},
    )

    normalized: list[dict[str, Any]] = []
    for item in response.results:
        normalized.append(
            {
                "title": item.title,
                "url": item.url,
                "published_date": getattr(item, "published_date", None),
                "text": getattr(item, "text", None),
            }
        )
    return normalized


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deep web search using Exa.")
    parser.add_argument("prompt", help="Prompt/query to search on the web")
    parser.add_argument(
        "--type",
        default="deep",
        choices=["fast", "auto", "deep", "deep-reasoning"],
        help="Exa search depth/speed mode",
    )
    parser.add_argument("--num-results", type=int, default=10)
    parser.add_argument("--max-characters", type=int, default=20000)
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    try:
        results = search_web_deep(
            args.prompt,
            num_results=args.num_results,
            max_characters=args.max_characters,
            search_type=args.type,
        )
        payload = {
            "ok": True,
            "query": args.prompt,
            "type": args.type,
            "num_results": len(results),
            "results": results,
        }
        print(json.dumps(payload, ensure_ascii=True))
    except Exception as exc:
        error_payload = {"ok": False, "error": str(exc)}
        print(json.dumps(error_payload, ensure_ascii=True))
        sys.exit(1)


if __name__ == "__main__":
    main()
