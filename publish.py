"""
Send finished drafts to the Tuskers Blog Backend as PENDING articles.

The crew saves every draft to output/*.md regardless; if BLOG_API_URL is set in
.env, the draft is also POSTed to `POST /articles/bot` (x-api-key auth), where
the backend forces publishedStatus=pending and botCreated=true. Approval then
happens in the admin panel (PATCH /admin/articles/:id/approve).

The article body is converted from Markdown to an HTML fragment (content tags
only -- h2/h3, p, ul/li, table, etc. -- no <html>/<head>/<body> wrapper), which
is what the blog stores in `content`. The leading H1 is dropped because the
blog renders `title` itself.

Manual use:  python publish.py output\\draft-tourism-20260611-1512.md tourism
"""

import os
import re
import sys
from datetime import date
from pathlib import Path

import markdown
import requests
from dotenv import load_dotenv

load_dotenv()

AUTHOR = "Tusker AI Bot"
ARTICLE_TYPE = "ai-generated"


def parse_draft(text: str) -> dict:
    """Split a draft into title, meta description, and Markdown body.

    Prefers the strict "TITLE:/META:" format the reviewer is instructed to use,
    but tolerates the older variants seen in real output: bold **Title:** lines
    and YAML front matter, optionally wrapped in a ```markdown code fence.
    """
    text = text.strip()
    fence = re.match(r"^```(?:markdown)?\s*\n(.*)\n```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    title = meta = None

    m = re.search(r"^TITLE:\s*(.+)$", text, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        text = text.replace(m.group(0), "", 1)
    m = re.search(r"^META:\s*(.+)$", text, re.MULTILINE)
    if m:
        meta = m.group(1).strip()
        text = text.replace(m.group(0), "", 1)

    if title is None:
        m = re.search(r"^\*\*Title:?\*\*:?\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
        if m:
            title = m.group(1).strip().strip("*").strip()
            text = text.replace(m.group(0), "", 1)
    if meta is None:
        m = re.search(
            r"^\*\*Meta[ _-]?Description:?\*\*:?\s*(.+)$", text, re.MULTILINE | re.IGNORECASE
        )
        if m:
            meta = m.group(1).strip()
            text = text.replace(m.group(0), "", 1)

    yaml = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if yaml:
        block = yaml.group(1)
        if title is None:
            m = re.search(r"^title:\s*(.+)$", block, re.MULTILINE)
            if m:
                title = m.group(1).strip().strip("\"'")
        if meta is None:
            m = re.search(r"^meta_description:\s*(.+)$", block, re.MULTILINE)
            if m:
                meta = m.group(1).strip().strip("\"'")
        text = text[yaml.end():]

    body = text.strip()
    if title is None:
        m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = m.group(1).strip() if m else "Untitled draft"

    return {"title": title, "meta_description": meta or "", "content": body}


def body_to_html(markdown_body: str) -> str:
    """Markdown body -> HTML fragment with content tags only.

    Drops the leading H1 (the blog renders the title separately), then converts
    the rest. python-markdown emits a fragment (h2, p, ul/li, table, ...) --
    there is never an <html>/<head>/<body> wrapper.
    """
    body = re.sub(r"^#\s+.+\n+", "", markdown_body.strip(), count=1)
    return markdown.markdown(body, extensions=["tables"])


def first_paragraph(markdown_body: str, max_len: int = 200) -> str:
    """Fallback excerpt: first non-heading paragraph, truncated."""
    for block in markdown_body.split("\n\n"):
        block = block.strip()
        if block and not block.startswith("#"):
            text = re.sub(r"[*_`\[\]]", "", block.replace("\n", " "))
            return text[:max_len].rsplit(" ", 1)[0] + ("..." if len(text) > max_len else "")
    return ""


def send_draft(draft_path: Path, domain: dict) -> bool:
    """POST one draft file to /articles/bot as a pending article. Returns success."""
    api_url = os.getenv("BLOG_API_URL")
    if not api_url:
        return False
    api_key = os.getenv("BOT_API_KEY", "")

    article = parse_draft(draft_path.read_text(encoding="utf-8"))
    payload = {
        "title": article["title"],
        "excerpt": article["meta_description"] or first_paragraph(article["content"]),
        "content": body_to_html(article["content"]),
        "category": domain.get("category", "General"),
        "tags": domain.get("tags", []),
        "author": AUTHOR,
        "publishDate": date.today().isoformat(),
        "articleType": ARTICLE_TYPE,
    }
    response = requests.post(
        api_url, json=payload, headers={"x-api-key": api_key}, timeout=30
    )
    if response.ok:
        print(f"Sent to blog as pending: {article['title']!r}")
        return True
    print(f"Blog API rejected the draft ({response.status_code}): {response.text[:300]}")
    return False


if __name__ == "__main__":
    from domains import DOMAINS

    if len(sys.argv) != 3:
        slugs = ", ".join(d["slug"] for d in DOMAINS)
        print(f"Usage: python publish.py <draft.md> <domain-slug>   (slugs: {slugs})")
        sys.exit(1)
    domain = next((d for d in DOMAINS if d["slug"] == sys.argv[2]), None)
    if domain is None:
        print(f"Unknown domain slug: {sys.argv[2]}")
        sys.exit(1)
    ok = send_draft(Path(sys.argv[1]), domain)
    sys.exit(0 if ok else 1)
