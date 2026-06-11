# Elephant Blog Bot

An automated, multi-agent blog drafting system for a Sri Lankan elephant
conservation/tourism site. It pulls recent elephant news, has a panel of agents
discuss it, writes a post, fact-checks it, and saves a draft for you to review.

Built to run on **free** LLM tiers (Groq + Google Gemini).

## What's in here

| File | Job |
|------|-----|
| `news.py` | Scout: fetches recent elephant news from RSS (no API key) |
| `simple_draft.py` | Milestone: news -> ONE LLM call -> draft (no agents) |
| `crew.py` | The full multi-agent version (editor, 3-person panel, writer, reviewer) |
| `requirements.txt` | Dependencies |
| `.env.example` | Template for your API keys |

## Step-by-step setup

### 1. Check Python
You need Python 3.10 - 3.13.
```
python3 --version
```

### 2. Create the project + virtual environment
```
cd elephant-blog-bot
python3 -m venv venv
# macOS / Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Get the two free API keys (no credit card)
- **Groq:** https://console.groq.com -> API Keys -> Create
- **Gemini:** https://aistudio.google.com -> Get API key

Then copy the template and paste your keys:
```
cp .env.example .env      # Windows: copy .env.example .env
```
Edit `.env` and fill in both keys.

### 5. Run it in order (this is the important part)

**a) Test the news fetcher alone:**
```
python news.py
```
You should see a list of recent elephant headlines. If not, edit the `FEEDS`
list in `news.py`.

**b) Test the simple pipeline (no agents):**
```
python simple_draft.py
```
This writes `output/simple-draft-*.md`. Read it. If the quality is good, your
keys + prompt + news source all work. Spend time improving the prompt here --
this is where most of the quality comes from.

**c) Run the full agent crew:**
```
python crew.py
```
This runs the editor -> panel debate -> writer -> reviewer and saves
`output/draft-*.md`. You'll see each agent "think" in the terminal.

## What to do next (don't skip the order)
1. Run for a week and read every draft. Tune the agent `backstory`/`goal` text
   and the task descriptions in `crew.py`.
2. Only once drafts are consistently good, add the publishing step
   (commit Markdown to your Vue site's repo, or call the Webflow CMS API).
3. Last, add a GitHub Actions cron job to run `crew.py` on a schedule and drop
   drafts into a review queue (e.g. open a PR).

## Notes
- The panel "debate" here is sequential (each persona builds on the last). For a
  true back-and-forth, upgrade later to a CrewAI hierarchical manager or AutoGen
  GroupChat.
- Free tiers are rate-limited. If you hit limits, lower the agent count or add
  small delays. The fast Groq model handles the chatty panel; Gemini does the
  editing/writing.
- Keep a human approving every post until you fully trust the output.
