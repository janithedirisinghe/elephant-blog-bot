"""
Scout step: fetch recent Sri Lankan elephant news from free RSS feeds.

Uses Google News RSS search, which needs no API key. You can add or swap
feeds in the FEEDS list below (e.g. a Mongabay or conservation-org feed).

Run it on its own to test:  python news.py
"""

import re
from html import unescape

import feedparser

# Google News RSS search feeds. "when:30d" limits to the last 30 days.
FEEDS = [
    "https://news.google.com/rss/search?q=Sri+Lanka+elephant+when:30d&hl=en-LK&gl=LK&ceid=LK:en",
    "https://news.google.com/rss/search?q=human+elephant+conflict+Sri+Lanka+when:30d&hl=en-LK&gl=LK&ceid=LK:en",
    "https://news.google.com/rss/search?q=elephant+conservation+when:30d&hl=en&gl=US&ceid=US:en",
]


def _strip_html(text: str) -> str:
    """Google News summaries arrive as HTML; reduce them to plain text."""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def fetch_news(feeds, limit: int = 12):
    """Return a list of recent news items as dicts: title, link, summary, published."""
    seen = set()
    items = []
    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "")
            key = title.lower()
            if not title or key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "title": title,
                    "link": link,
                    "summary": _strip_html(entry.get("summary", "")),
                    "published": entry.get("published", ""),
                }
            )
    return items[:limit]


def fetch_elephant_news(limit: int = 12):
    """Elephant-news shortcut, kept for simple_draft.py."""
    return fetch_news(FEEDS, limit)


if __name__ == "__main__":
    results = fetch_elephant_news()
    print(f"Found {len(results)} stories:\n")
    for item in results:
        print("-", item["title"])
