from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from backend.config import EXA_API_KEY, OPENAI_API_KEY
from backend.pipeline.exa_search import search_web_deep

_SYSTEM_PROMPT = """\
You are a startup failure analyst. You will receive web research about startups \
and companies that failed in a market similar to the user's business idea.

Synthesize the research into structured failure case studies. Return ONLY valid \
JSON (no markdown fences) with this exact structure:
{
  "cases": [
    {
      "company": "company name",
      "what_failed": "1-2 sentence description of what went wrong",
      "lesson": "actionable takeaway for the user's idea"
    }
  ],
  "key_lessons": ["lesson 1", "lesson 2", ...],
  "how_to_avoid": ["specific action the user should take to avoid these failures"]
}

If the research does not contain clear failure stories, infer common failure \
modes for that market based on the available data.
"""


def get_failure_cases(idea: str, web_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Search for failure stories in the idea's market and synthesize lessons."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing.")

    queries = [
        f"{idea} startup failure lessons why failed",
        f"companies that failed similar to {idea} what went wrong",
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

    existing_context = "\n".join(
        f"- {r.get('title', '')} ({r.get('url', '')})"
        for r in web_results[:5]
    )

    user_msg = (
        f"Business idea: {idea}\n\n"
        f"--- EXISTING MARKET CONTEXT ---\n{existing_context}\n\n"
        f"--- FAILURE RESEARCH ---\n{research_text or '(no results found)'}"
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
