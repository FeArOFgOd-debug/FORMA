from __future__ import annotations

from typing import Any

from apify_client import ApifyClient

from backend.config import APIFY_API_KEY

_client: ApifyClient | None = None


def _get_client() -> ApifyClient:
    global _client
    if not APIFY_API_KEY:
        raise ValueError("APIFY_API_KEY is missing. Add it to your .env file.")
    if _client is None:
        _client = ApifyClient(token=APIFY_API_KEY)
    return _client


def scrape_reddit(query: str, *, max_posts: int = 20) -> list[dict[str, Any]]:
    """Search Reddit for posts/comments related to *query*."""
    client = _get_client()
    run_input = {
        "searches": [query],
        "maxPostCount": max_posts,
        "maxComments": 0,
        "proxy": {"useApifyProxy": True},
    }
    run = client.actor("trudax/reddit-scraper-lite").call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    normalized: list[dict[str, Any]] = []
    for item in items:
        normalized.append({
            "source": "reddit",
            "title": item.get("title", ""),
            "body": item.get("body", ""),
            "url": item.get("url", ""),
            "score": item.get("score", 0),
            "num_comments": item.get("numberOfComments", 0),
            "subreddit": item.get("subreddit", ""),
            "created_at": item.get("createdAt"),
        })
    return normalized


def scrape_twitter(query: str, *, max_tweets: int = 30) -> list[dict[str, Any]]:
    """Search Twitter/X for tweets related to *query*."""
    client = _get_client()
    run_input = {
        "searchTerms": [query],
        "maxTweets": max_tweets,
        "addUserInfo": True,
        "scrapeTweetReplies": False,
    }
    run = client.actor("apidojo/tweet-scraper").call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    normalized: list[dict[str, Any]] = []
    for item in items:
        normalized.append({
            "source": "twitter",
            "text": item.get("full_text", item.get("text", "")),
            "url": item.get("url", ""),
            "likes": item.get("favorite_count", 0),
            "retweets": item.get("retweet_count", 0),
            "author": item.get("user", {}).get("name", ""),
            "created_at": item.get("created_at"),
        })
    return normalized
