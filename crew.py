"""
The multi-agent version: an editor picks the topic, a 3-persona panel discusses it,
a writer turns the discussion into a post, and a reviewer fact-checks and polishes it.

The same flow runs once per domain defined in domains.py (Sri Lankan elephants,
Sri Lankan tourism, world animal news), producing one article each.

The Scout (news fetching) is handled by news.py and passed in as context -- that is
simpler and more reliable than giving an agent a live web tool to start with.

Output is written to output/draft-<domain>-*.md for you to review. Nothing is
published automatically -- that step is added later, on purpose.

Run:  python crew.py
"""

import truststore

truststore.inject_into_ssl()  # trust the Windows cert store (Avast re-signs TLS traffic)

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
import crewai.llms.cache as _llm_cache

# crewai 1.14.6 leaks its internal "cache_breakpoint" message marker through the
# litellm path, and Groq's API rejects messages with unknown properties. Disable
# the marker (Gemini caches implicitly, so nothing is lost).
_llm_cache.mark_cache_breakpoint = lambda message: dict(message)

from domains import DOMAINS
from news import fetch_news
from publish import send_draft

load_dotenv()

# Fast model for the chatty panel debate; higher-quality model for editing/writing.
# QUALITY_MODEL in .env can override, e.g. gemini/gemini-2.5-flash-lite when the
# flash free-tier daily quota (20 requests/model) is used up.
fast_llm = LLM(model="groq/llama-3.3-70b-versatile", temperature=0.7, num_retries=3)
quality_llm = LLM(
    model=os.getenv("QUALITY_MODEL", "gemini/gemini-2.5-flash"),
    temperature=0.6,
    num_retries=3,
)


def build_crew(news_digest: str, domain: dict) -> Crew:
    site = domain["site"]

    editor = Agent(
        role="Content Editor",
        goal="Choose the single most blog-worthy story and set a clear angle and SEO keyword.",
        backstory=f"A seasoned editor for {site} "
        "who knows what readers and search engines respond to.",
        llm=quality_llm,
        verbose=True,
    )
    panelists = [
        Agent(
            role=p["role"],
            goal=p["goal"],
            backstory=p["backstory"],
            llm=fast_llm,
            verbose=True,
        )
        for p in domain["panel"]
    ]
    writer = Agent(
        role="Blog Writer",
        goal="Turn the panel discussion into one engaging, well-structured blog post.",
        backstory=f"A writer for {site} who turns expert debate into clear, vivid, honest articles.",
        llm=quality_llm,
        verbose=True,
    )
    reviewer = Agent(
        role="SEO and Fact-Check Editor",
        goal="Polish the draft, confirm every claim matches the source news, and optimise the title and meta description.",
        backstory="A meticulous editor who protects the site's credibility and search ranking.",
        llm=quality_llm,
        verbose=True,
    )

    editorial = domain.get("editorial", "")
    pick = Task(
        description=f"Today's news digest:\n\n{news_digest}\n\n"
        "Pick the ONE most blog-worthy story. Give a short brief: the topic, the angle, "
        "and a primary SEO keyword."
        + (f"\n\nEditorial line for this blog: {editorial}" if editorial else ""),
        expected_output="A short brief with chosen topic, angle, and primary SEO keyword.",
        agent=editor,
    )

    # Panel: each persona builds on the discussion so far; the last one critiques.
    view_tasks = []
    for i, agent in enumerate(panelists):
        if i == 0:
            description = (
                f"Read the editor's brief. Give your take as the {agent.role} in 4-6 sentences."
            )
            expected = f"The {agent.role}'s perspective on the chosen topic."
        elif i < len(panelists) - 1:
            description = (
                "Read the brief and the discussion so far. Add your perspective as "
                f"the {agent.role} in 4-6 sentences, responding to what was said."
            )
            expected = f"The {agent.role}'s perspective, building on the discussion."
        else:
            description = (
                "Read the brief and all views. Point out any weak, one-sided, or "
                "unverified claims and note what must be checked. 4-6 sentences."
            )
            expected = "A critical review of the discussion so far."
        view_tasks.append(
            Task(
                description=description,
                expected_output=expected,
                agent=agent,
                context=[pick, *view_tasks],
            )
        )

    draft = Task(
        description="Using the brief and the full panel discussion, write a 600-800 word blog post "
        "in Markdown: an H1 title, a short intro, two or three H2 sections, and a closing thought.",
        expected_output="A complete blog post in Markdown.",
        agent=writer,
        context=[pick, *view_tasks],
    )
    review = Task(
        description="Polish the draft for clarity and flow. Make sure every factual claim is "
        "consistent with the source news digest.\n"
        "Return the result in EXACTLY this format (no code fences, no extra labels):\n"
        "TITLE: <SEO-friendly title>\n"
        "META: <meta description of about 150 characters>\n"
        "\n"
        "<the full blog post in Markdown, starting with the # H1 line>",
        expected_output="TITLE: and META: lines, a blank line, then the publish-ready post in Markdown.",
        agent=reviewer,
        context=[draft],
    )

    return Crew(
        agents=[editor, *panelists, writer, reviewer],
        tasks=[pick, *view_tasks, draft, review],
        process=Process.sequential,
        verbose=True,
    )


def run_domain(domain: dict) -> Path | None:
    print(f"\n{'=' * 60}\nDomain: {domain['slug']}\n{'=' * 60}")
    print("Fetching news...")
    items = fetch_news(domain["feeds"], limit=40)
    keywords = domain.get("title_filter")
    if keywords:
        items = [it for it in items if any(k in it["title"].lower() for k in keywords)]
    excluded = domain.get("title_exclude")
    if excluded:
        items = [it for it in items if not any(k in it["title"].lower() for k in excluded)]
    items = items[:12]
    if not items:
        print(f"No news found for {domain['slug']} -- check its feeds in domains.py.")
        return None

    digest = "\n\n".join(
        f"- {it['title']} ({it['published']})\n  {it['summary']}\n  Source: {it['link']}"
        for it in items
    )
    crew = build_crew(digest, domain)
    result = crew.kickoff()

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    fname = out_dir / f"draft-{domain['slug']}-{datetime.now():%Y%m%d-%H%M}.md"
    fname.write_text(str(result), encoding="utf-8")
    print(f"\nDraft saved to {fname}")

    if os.getenv("BLOG_API_URL"):
        try:
            send_draft(fname, domain)
        except Exception as e:  # a publish hiccup must not fail the whole run
            print(f"Could not send draft to blog API: {e}")
    return fname


def main():
    # Optional args select domains by slug, e.g.:  python crew.py tourism world-animals
    slugs = sys.argv[1:]
    known = {d["slug"] for d in DOMAINS}
    unknown = set(slugs) - known
    if unknown:
        print(f"Unknown domain(s): {', '.join(sorted(unknown))}. Available: {', '.join(sorted(known))}")
        return
    domains = [d for d in DOMAINS if not slugs or d["slug"] in slugs]

    saved = []
    failed = []
    for domain in domains:
        try:
            fname = run_domain(domain)
            if fname:
                saved.append(fname)
            else:
                failed.append(domain["slug"])
        except Exception as e:  # one domain failing must not kill the others
            print(f"\n{domain['slug']} failed: {e}")
            failed.append(domain["slug"])

    print(f"\n{'=' * 60}\nDone. {len(saved)} draft(s) saved:")
    for fname in saved:
        print(f"  {fname}")
    if failed:
        print(f"Failed (rerun later): {', '.join(failed)}")
    print("Review the drafts, edit if needed, then publish.")


if __name__ == "__main__":
    main()
