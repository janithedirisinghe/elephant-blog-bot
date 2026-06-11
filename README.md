# Elephant Blog Bot

A multi-agent content bot for the **Tuskers Blog**. On a schedule it pulls recent
news for three topics, has a panel of AI agents discuss and write each story, and
submits the result to the blog backend as a **pending** article for admin approval.
Nothing is ever published automatically.

Built to run on **free** LLM tiers (Groq + Google Gemini).

```
news feeds → topic filter → dedup vs blog → multi-agent writing → HTML → blog (pending) → you approve
```

## Topics ("domains")

Each run produces up to three articles, one per domain:

| Slug | Blog vertical | Category |
|------|---------------|----------|
| `elephants` | Sri Lankan elephant conservation & tourism | Wildlife |
| `tourism` | Sri Lankan travel & destinations | Travel |
| `world-animals` | Global animal & wildlife news | Wildlife |

All three run through the **same** flow; what makes them different (feeds, filters,
expert panel, category, tags) lives in [`domains.py`](domains.py). Adding a fourth
topic is just appending a dict there — no code changes.

## How it works

For each domain, [`crew.py`](crew.py) runs these steps:

1. **Kill switch** — if `BOT_ENABLED` is off, exit immediately.
2. **Fetch news** — [`news.py`](news.py) pulls recent headlines from the domain's
   Google News RSS feeds (no API key needed); HTML in summaries is stripped.
3. **Topic filter** — `title_filter` / `title_exclude` keyword lists keep only
   on-topic stories (e.g. tourism keeps destinations, drops visa/policy news).
4. **Deduplicate** — [`dedup.py`](dedup.py) fetches already-published articles from
   the blog's public endpoints and removes any story already covered. If every
   candidate is already covered, the domain is skipped that day.
5. **Write** — a 6-agent crew runs in sequence (see below).
6. **Save & submit** — the draft is saved to `output/*.md`, and if `BLOG_API_URL`
   is set, converted to HTML and POSTed to the backend as a pending article.

Each domain is isolated: if one fails (e.g. an LLM rate limit), the others still
finish, and a summary at the end lists what saved and what to rerun.

### The agent crew

| Agent | Model | Job |
|-------|-------|-----|
| Content Editor | Gemini | Pick the ONE best story, set angle + SEO keyword |
| Expert 1 | Groq | Domain perspective (e.g. Conservationist) |
| Expert 2 | Groq | Second perspective, responding to the first |
| Skeptic | Groq | Challenge weak / unverified claims |
| Blog Writer | Gemini | Turn the discussion into a 600–800 word post |
| SEO & Fact-Check Editor | Gemini | Fact-check vs the digest, add title + meta description |

Fast/cheap **Groq Llama** runs the chatty panel; higher-quality **Gemini** does the
editing and writing. The expert personas come from each domain's `panel` config.

## Files

| File | Job |
|------|-----|
| [`domains.py`](domains.py) | Config for the three topics (feeds, filters, panel, category) |
| [`news.py`](news.py) | Fetch & clean news from Google News RSS |
| [`dedup.py`](dedup.py) | Drop stories already published on the blog |
| [`crew.py`](crew.py) | Orchestrator + the multi-agent writing flow |
| [`publish.py`](publish.py) | Markdown → HTML, POST to the blog as pending |
| [`simple_draft.py`](simple_draft.py) | Original single-LLM-call version, kept for testing |
| [`.github/workflows/draft-articles.yml`](.github/workflows/draft-articles.yml) | Scheduled run on GitHub Actions |

## Setup

Requires **Python 3.10–3.13**.

```powershell
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
copy .env.example .env         # Windows  (cp on macOS/Linux)
# then edit .env and fill in your keys
```

Get the two free API keys (no credit card):
- **Groq:** https://console.groq.com → API Keys
- **Gemini:** https://aistudio.google.com → Get API key

## Configuration (`.env`)

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | yes | Groq (fast panel model) |
| `GEMINI_API_KEY` | yes | Google Gemini (editing/writing model) |
| `BOT_ENABLED` | no | Kill switch — `false`/`0`/`no`/`off` disables the bot. Default: enabled |
| `QUALITY_MODEL` | no | Override the Gemini model (e.g. `gemini/gemini-2.5-flash-lite` when the flash daily quota is hit) |
| `BLOG_API_URL` | no | Backend bot endpoint, e.g. `https://<host>/articles/bot`. Unset = save local files only |
| `BOT_API_KEY` | no | Must match the backend's `BOT_API_KEY`; sent as the `x-api-key` header |

> **Never commit real keys.** `.env` is gitignored; `.env.example` holds placeholders only.

## Running

```powershell
python news.py            # test the news fetcher alone (no LLM, no keys)
python simple_draft.py    # quick single-call draft (elephants only)
python crew.py            # the full pipeline — all three domains
python crew.py tourism    # just one domain
python crew.py tourism world-animals   # a subset
```

Each run saves drafts to `output/draft-<domain>-<timestamp>.md`. If `BLOG_API_URL`
is set, drafts are also submitted to the blog as **pending** and appear in the admin
review queue (`/admin/articles/pending`). See
[`docs/backendconfigaraion.md`](docs/backendconfigaraion.md) for the backend contract.

## Deployment (GitHub Actions)

[`.github/workflows/draft-articles.yml`](.github/workflows/draft-articles.yml) runs
the bot on a schedule (every 4 days at 01:00 UTC ≈ 06:30 Sri Lanka time) plus a
manual "Run workflow" button.

To activate it:
1. **Set repo secrets** (Settings → Secrets and variables → Actions → Secrets):
   `GROQ_API_KEY`, `GEMINI_API_KEY`, `BLOG_API_URL`, `BOT_API_KEY`.
   Optionally set `BOT_ENABLED` / `QUALITY_MODEL` as repo **Variables**.
2. **The backend must be publicly reachable** — a cloud runner cannot reach
   `localhost`. Use the backend's public URL and ensure `BOT_API_KEY` is in its
   production environment.
3. Push, then test once with the manual button before trusting the schedule.

To pause: set the `BOT_ENABLED` variable to `false` (soft — runner still starts but
does nothing) or disable the workflow in the Actions tab (hard — nothing runs).

## Tuning

Everything topic-specific is in [`domains.py`](domains.py), editable in plain English:

- **`feeds`** — Google News RSS search URLs.
- **`title_filter`** — only keep stories whose title contains one of these words.
- **`title_exclude`** — drop stories whose title contains one of these words.
- **`editorial`** — guidance injected into the Editor on what to pick / avoid.
- **`panel`** — the expert personas for the discussion.

Dedup sensitivity lives at the top of [`dedup.py`](dedup.py)
(`TITLE_SIMILARITY`, `WORD_OVERLAP`).

## Troubleshooting

- **`Missing Gemini API key`** — no `.env`, or keys are in `.env.example` instead.
- **`CERTIFICATE_VERIFY_FAILED`** (Windows) — antivirus (e.g. Avast) intercepts TLS.
  Handled by `truststore` at the top of `crew.py`/`simple_draft.py`; harmless elsewhere.
- **`503 high demand` / `429 RESOURCE_EXHAUSTED`** — Gemini free-tier congestion or
  the ~20 requests/day cap. Retry, or set `QUALITY_MODEL=gemini/gemini-2.5-flash-lite`.
  A full 3-domain run uses ~9 Gemini calls, so once/day is comfortable.
- **`cache_breakpoint is unsupported` (Groq)** — a CrewAI quirk, already patched in
  `crew.py`.

## Safety model

Four independent guards keep anything bad from reaching the blog unattended:

1. **Kill switch** (`BOT_ENABLED`) — stops the whole bot.
2. **Topic filters** — only on-topic stories are considered.
3. **Dedup** — nothing already published gets rewritten.
4. **Pending status** — every article waits for your manual approval.
