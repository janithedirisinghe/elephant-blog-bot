"""
Milestone script (no agents yet): fetch news, then write a draft with ONE LLM call.

This is the first thing to get working. If this produces a draft you'd be happy
to edit and publish, your keys, prompt, and news source are all good -- and only
THEN is it worth adding the multi-agent version in crew.py.

Run:  python simple_draft.py
"""

import truststore

truststore.inject_into_ssl()  # trust the Windows cert store (Avast re-signs TLS traffic)

from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from litellm import completion

from news import fetch_elephant_news

load_dotenv()

MODEL = "gemini/gemini-2.5-flash"  # free tier, high quality for writing


def generate_draft(news_digest: str) -> str:
    prompt = (
        "You are a writer for a Sri Lankan elephant conservation and tourism blog.\n\n"
        "Here is today's news digest:\n\n"
        f"{news_digest}\n\n"
        "Pick the single most interesting story and write a ~600-word blog post in "
        "Markdown: an H1 title, a short intro, two H2 sections, and a closing thought. "
        "Be accurate and only state facts supported by the digest. Have a clear point of view."
    )
    response = completion(
        model=MODEL, messages=[{"role": "user", "content": prompt}], num_retries=3
    )
    return response.choices[0].message.content


def main():
    items = fetch_elephant_news(limit=12)
    if not items:
        print("No news found -- check your feeds in news.py.")
        return

    digest = "\n\n".join(
        f"- {it['title']} ({it['published']})\n  {it['summary']}\n  Source: {it['link']}"
        for it in items
    )
    print("Generating a draft from the latest news...\n")
    draft = generate_draft(digest)

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    fname = out_dir / f"simple-draft-{datetime.now():%Y%m%d-%H%M}.md"
    fname.write_text(draft, encoding="utf-8")
    print(f"Draft saved to {fname}")


if __name__ == "__main__":
    main()
