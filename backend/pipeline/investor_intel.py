from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from backend.config import OPENAI_API_KEY
from backend.pipeline.exa_search import search_web_deep

_SYSTEM_PROMPT = """\
You are a venture capital research analyst. You will receive web research \
about investors and funding activity in a market related to the user's idea.

Synthesize the research into an investor intelligence brief. Return ONLY valid \
JSON (no markdown fences) with this exact structure:
{
  "investors": [
    {
      "name": "person or firm name",
      "firm": "firm name (or 'Independent')",
      "focus": "investment thesis / focus area",
      "notable_portfolio": ["company 1", "company 2"]
    }
  ],
  "funding_landscape": "2-3 sentence overview of funding activity in this space",
  "avg_seed_size": "estimated typical seed round size with reasoning",
  "top_accelerators": ["relevant accelerator or program 1", ...],
  "fundraising_tips": ["actionable tip for the founder"]
}
"""


def get_investor_intel(idea: str) -> dict[str, Any]:
    """Search for investors and VCs active in the idea's market."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing.")

    queries = [
        f"investors funding {idea} startups VC seed round",
        f"venture capital firms investing {idea} market recent deals",
    ]

    all_results: list[dict[str, Any]] = []
    for q in queries:
        try:
            results = search_web_deep(q, num_results=5, max_characters=5000, search_type="auto")
            all_results.extend(results)
        except Exception:
            pass

    research_text = "\n\n".join(
        f"Source: {r.get('title', 'N/A')} ({r.get('url', '')})\n"
        f"{(r.get('text') or '')[:3000]}"
        for r in all_results[:8]
    )

    user_msg = (
        f"Business idea: {idea}\n\n"
        f"--- INVESTOR / FUNDING RESEARCH ---\n{research_text or '(no results found)'}"
    )

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    return json.loads(response.choices[0].message.content)
