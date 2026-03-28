from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from backend.config import OPENAI_API_KEY

_SYSTEM_PROMPT = """\
You are a sentiment analysis expert. You will receive social media posts and \
comments about a business idea collected from Reddit and Twitter/X.

Analyze the overall public sentiment and return ONLY valid JSON (no markdown \
fences) with this exact structure:
{
  "reddit_sentiment": "positive" | "neutral" | "negative",
  "twitter_sentiment": "positive" | "neutral" | "negative",
  "overall_sentiment_score": <float 0-1, where 1 = extremely positive>,
  "key_concerns": ["concern 1", "concern 2", ...],
  "key_positives": ["positive 1", "positive 2", ...],
  "notable_comments": [
    {"source": "reddit"|"twitter", "text": "...", "sentiment": "positive"|"neutral"|"negative"}
  ],
  "summary": "2-3 sentence summary of overall public perception"
}
"""


def analyze_sentiment(
    reddit_posts: list[dict[str, Any]],
    twitter_posts: list[dict[str, Any]],
    idea: str,
) -> dict[str, Any]:
    """Run GPT-4o sentiment analysis on scraped social content."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing. Add it to your .env file.")

    reddit_text = "\n\n".join(
        f"[r/{p.get('subreddit', '?')}] {p.get('title', '')} — {p.get('body', '')}"
        for p in reddit_posts[:20]
    )
    twitter_text = "\n\n".join(
        f"@{p.get('author', '?')}: {p.get('text', '')}"
        for p in twitter_posts[:30]
    )

    user_msg = (
        f"Business idea: {idea}\n\n"
        f"--- REDDIT POSTS ({len(reddit_posts)} total) ---\n{reddit_text or '(none)'}\n\n"
        f"--- TWITTER/X POSTS ({len(twitter_posts)} total) ---\n{twitter_text or '(none)'}"
    )

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    return json.loads(response.choices[0].message.content)
