"""
The multi-agent version: an editor picks the topic, a 3-persona panel discusses it,
a writer turns the discussion into a post, and a reviewer fact-checks and polishes it.

The Scout (news fetching) is handled by news.py and passed in as context -- that is
simpler and more reliable than giving an agent a live web tool to start with.

Output is written to output/draft-*.md for you to review. Nothing is published
automatically -- that step is added later, on purpose.

Run:  python crew.py
"""

import truststore

truststore.inject_into_ssl()  # trust the Windows cert store (Avast re-signs TLS traffic)

from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

from news import fetch_elephant_news

load_dotenv()

# Fast model for the chatty panel debate; higher-quality model for editing/writing.
fast_llm = LLM(model="groq/llama-3.3-70b-versatile", temperature=0.7, num_retries=3)
quality_llm = LLM(model="gemini/gemini-2.5-flash", temperature=0.6, num_retries=3)


def build_crew(news_digest: str) -> Crew:
    editor = Agent(
        role="Content Editor",
        goal="Choose the single most blog-worthy elephant story and set a clear angle and SEO keyword.",
        backstory="A seasoned editor for a Sri Lankan elephant conservation and tourism site "
        "who knows what readers and search engines respond to.",
        llm=quality_llm,
        verbose=True,
    )
    conservationist = Agent(
        role="Conservationist",
        goal="Argue the ecology, habitat, and protection angle of the chosen story.",
        backstory="A field biologist focused on Sri Lankan elephant habitats and human-elephant conflict.",
        llm=fast_llm,
        verbose=True,
    )
    tourism_guide = Agent(
        role="Safari and Tourism Guide",
        goal="Bring the visitor experience and ethical-tourism perspective to the story.",
        backstory="A veteran safari guide who knows where travellers can see wild tuskers "
        "and cares deeply about ethical, low-impact tourism.",
        llm=fast_llm,
        verbose=True,
    )
    skeptic = Agent(
        role="Skeptic and Balancer",
        goal="Challenge weak or one-sided claims and make sure the piece stays accurate and balanced.",
        backstory="A critical thinker who dislikes fluff and demands evidence for every claim.",
        llm=fast_llm,
        verbose=True,
    )
    writer = Agent(
        role="Blog Writer",
        goal="Turn the panel discussion into one engaging, well-structured blog post.",
        backstory="A wildlife writer who turns expert debate into clear, vivid, honest articles.",
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

    pick = Task(
        description=f"Today's elephant news digest:\n\n{news_digest}\n\n"
        "Pick the ONE most blog-worthy story. Give a short brief: the topic, the angle, "
        "and a primary SEO keyword.",
        expected_output="A short brief with chosen topic, angle, and primary SEO keyword.",
        agent=editor,
    )
    cons_view = Task(
        description="Read the editor's brief. Give your conservationist take in 4-6 sentences.",
        expected_output="The conservationist's perspective on the chosen topic.",
        agent=conservationist,
        context=[pick],
    )
    tour_view = Task(
        description="Read the brief and the conservationist's view. Add the tourism / visitor "
        "perspective in 4-6 sentences, responding to what was said.",
        expected_output="The tourism perspective, building on the conservationist's view.",
        agent=tourism_guide,
        context=[pick, cons_view],
    )
    skeptic_view = Task(
        description="Read the brief and both views. Point out any weak, one-sided, or unverified "
        "claims and note what must be checked. 4-6 sentences.",
        expected_output="A critical review of the discussion so far.",
        agent=skeptic,
        context=[pick, cons_view, tour_view],
    )
    draft = Task(
        description="Using the brief and the full panel discussion, write a 600-800 word blog post "
        "in Markdown: an H1 title, a short intro, two or three H2 sections, and a closing thought.",
        expected_output="A complete blog post in Markdown.",
        agent=writer,
        context=[pick, cons_view, tour_view, skeptic_view],
    )
    review = Task(
        description="Polish the draft for clarity and flow. Make sure every factual claim is "
        "consistent with the source news digest. At the very top, add an SEO-friendly title and a "
        "meta description of about 150 characters.",
        expected_output="The final, publish-ready blog post in Markdown with title and meta description.",
        agent=reviewer,
        context=[draft],
    )

    return Crew(
        agents=[editor, conservationist, tourism_guide, skeptic, writer, reviewer],
        tasks=[pick, cons_view, tour_view, skeptic_view, draft, review],
        process=Process.sequential,
        verbose=True,
    )


def main():
    print("Fetching elephant news...")
    items = fetch_elephant_news(limit=12)
    if not items:
        print("No news found -- check your feeds in news.py.")
        return

    digest = "\n\n".join(
        f"- {it['title']} ({it['published']})\n  {it['summary']}\n  Source: {it['link']}"
        for it in items
    )
    crew = build_crew(digest)
    result = crew.kickoff()

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    fname = out_dir / f"draft-{datetime.now():%Y%m%d-%H%M}.md"
    fname.write_text(str(result), encoding="utf-8")
    print(f"\nDraft saved to {fname}")
    print("Review it, edit if needed, then publish.")


if __name__ == "__main__":
    main()
