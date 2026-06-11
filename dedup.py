"""
Duplicate prevention: drop news items already covered by published articles.

Before a domain is drafted, we fetch the blog's already-published articles (public
endpoints only -- no auth needed) and remove any news item that clearly matches one
of them, so the crew never re-writes a story that is already on the blog.

Only PUBLISHED articles are checked. Pending/rejected drafts are deliberately not
visible on the public endpoints, so a story sitting in the review queue can still
be re-drafted -- that gap is accepted for now.

Matching is intentionally mechanical (no LLM): a news headline counts as covered if
its title is very similar to a published title, OR most of its distinctive words
already appear in that article's title + excerpt. Published titles are SEO-styled
while headlines are newsy, so the word-overlap signal does most of the work.
"""

import os
import re
from difflib import SequenceMatcher

import requests

# Words too common (or too universal in this blog) to be distinctive for matching.
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "to", "for", "with", "is",
    "are", "this", "that", "its", "it", "as", "by", "from", "at", "be", "new",
    "how", "what", "why", "your", "you", "guide", "complete", "sri", "lanka",
    "lankas", "lankan",
}

TITLE_SIMILARITY = 0.62   # SequenceMatcher ratio on normalized titles
WORD_OVERLAP = 0.6        # fraction of a headline's distinctive words found in an article


def _api_base() -> str | None:
    url = os.getenv("BLOG_API_URL")
    if not url:
        return None
    return re.sub(r"/articles/bot/?$", "", url.rstrip("/"))


def _as_list(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "articles", "items", "results"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def fetch_existing_articles(domain: dict) -> list[dict]:
    """Published articles relevant to this domain (its category + recent), deduped."""
    base = _api_base()
    if not base:
        return []

    # All published articles, plus category/recent as fallbacks in case /articles
    # is paginated. Checking the full set catches cross-category duplicates too.
    paths = ["/articles", "/articles/recent"]
    category = domain.get("category")
    if category:
        paths.append(f"/articles/category/{requests.utils.quote(category)}")

    by_id: dict[str, dict] = {}
    for path in paths:
        try:
            resp = requests.get(base + path, timeout=20)
            if not resp.ok:
                continue
            for art in _as_list(resp.json()):
                key = art.get("_id") or art.get("slug") or art.get("title", "")
                by_id[key] = art
        except Exception as e:
            print(f"  (could not read {path}: {e})")
    return list(by_id.values())


def _normalize_title(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower())


def _stem(word: str) -> str:
    """Cheap singularization so 'elephants'/'elephant' and 'adults'/'adult' match."""
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _distinctive_words(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {_stem(w) for w in words if len(w) >= 4 and w not in STOPWORDS}


def _is_covered(headline: str, article: dict) -> bool:
    art_title = article.get("title", "")
    ratio = SequenceMatcher(
        None, _normalize_title(headline), _normalize_title(art_title)
    ).ratio()
    if ratio >= TITLE_SIMILARITY:
        return True

    headline_words = _distinctive_words(headline)
    if not headline_words:
        return False
    article_words = _distinctive_words(art_title + " " + article.get("excerpt", ""))
    overlap = len(headline_words & article_words) / len(headline_words)
    return overlap >= WORD_OVERLAP


def filter_new_items(items: list[dict], existing: list[dict]):
    """Split news items into (new, [(headline, matched_article_title), ...])."""
    new_items, covered = [], []
    for it in items:
        match = next((a for a in existing if _is_covered(it["title"], a)), None)
        if match:
            covered.append((it["title"], match.get("title", "")))
        else:
            new_items.append(it)
    return new_items, covered
