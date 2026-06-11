"""
Domain definitions: each domain is one blog vertical that runs through the same
editor -> panel -> writer -> reviewer crew in crew.py and produces one article.

To add a vertical, append a dict here -- crew.py picks it up automatically.
Each domain needs:
  slug   - used in the output filename (output/draft-<slug>-*.md)
  site   - description of the blog, injected into the agents' backstories
  feeds  - Google News RSS search URLs (no API key needed)
  panel  - exactly the discussion personas, in speaking order; the LAST one
           gets the critique task, so keep a skeptic-type persona last.
"""

from news import FEEDS as ELEPHANT_FEEDS

SKEPTIC = {
    "role": "Skeptic and Balancer",
    "goal": "Challenge weak or one-sided claims and make sure the piece stays accurate and balanced.",
    "backstory": "A critical thinker who dislikes fluff and demands evidence for every claim.",
}

DOMAINS = [
    {
        "slug": "elephants",
        "site": "a Sri Lankan elephant conservation and tourism blog",
        "category": "Wildlife",
        "tags": ["elephants", "sri lanka", "conservation"],
        "feeds": ELEPHANT_FEEDS,
        "panel": [
            {
                "role": "Conservationist",
                "goal": "Argue the ecology, habitat, and protection angle of the chosen story.",
                "backstory": "A field biologist focused on Sri Lankan elephant habitats and human-elephant conflict.",
            },
            {
                "role": "Safari and Tourism Guide",
                "goal": "Bring the visitor experience and ethical-tourism perspective to the story.",
                "backstory": "A veteran safari guide who knows where travellers can see wild tuskers "
                "and cares deeply about ethical, low-impact tourism.",
            },
            SKEPTIC,
        ],
    },
    {
        "slug": "tourism",
        "site": "a Sri Lankan travel and destinations blog",
        "category": "Travel",
        "tags": ["sri lanka", "travel", "destinations"],
        "feeds": [
            "https://news.google.com/rss/search?q=%22Sri+Lanka%22+best+places+OR+destinations+when:30d&hl=en&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=%22Sri+Lanka%22+new+destination+OR+attraction+OR+resort+when:30d&hl=en-LK&gl=LK&ceid=LK:en",
            "https://news.google.com/rss/search?q=Sigiriya+OR+Ella+OR+Yala+OR+Mirissa+OR+%22Arugam+Bay%22+travel+when:30d&hl=en&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=%22Sri+Lanka%22+elephant+safari+OR+%22elephant+gathering%22+when:30d&hl=en&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=%22best+time+to+visit%22+%22Sri+Lanka%22+when:60d&hl=en&gl=US&ceid=US:en",
        ],
        # Only keep stories whose title mentions the island or a known destination.
        "title_filter": [
            "sri lanka", "ceylon", "sigiriya", "ella", "yala", "mirissa",
            "arugam", "kandy", "colombo", "galle", "trincomalee", "nuwara eliya",
            "anuradhapura", "polonnaruwa", "minneriya", "udawalawe", "wilpattu",
        ],
        # Drop administrative/policy and off-topic national news before the
        # editor ever sees it -- the blog wants destinations, not bureaucracy.
        "title_exclude": [
            "visa", "arrival", "minister", "ministry", "tax", "election",
            "bombing", "fire", "court", "arrest", "spy",
        ],
        "editorial": "Prefer stories about specific places and travel experiences: trending or "
        "newly opened destinations, the best seasons and time periods to visit, destination "
        "facilities and recent upgrades, and elephant-related travel experiences. AVOID "
        "administrative or policy news (visas, taxes, arrival statistics, ministry announcements) "
        "unless the story is genuinely about a destination experience.",
        "panel": [
            {
                "role": "Destination Specialist",
                "goal": "Bring deep local knowledge of Sri Lankan places, culture, and travel seasons to the chosen story.",
                "backstory": "A Sri Lankan travel writer who has visited every province and knows "
                "the hidden gems beyond the guidebooks.",
            },
            {
                "role": "Traveller Advocate",
                "goal": "Represent the practical visitor perspective: costs, logistics, safety, and real experience quality.",
                "backstory": "A travel consultant who plans Sri Lanka itineraries for foreign "
                "visitors and hears their honest feedback afterwards.",
            },
            SKEPTIC,
        ],
    },
    {
        "slug": "world-animals",
        "site": "a global animal and wildlife news blog",
        "category": "Wildlife",
        "tags": ["wildlife", "animals", "conservation"],
        "feeds": [
            "https://news.google.com/rss/search?q=wildlife+conservation+when:7d&hl=en&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=endangered+species+when:7d&hl=en&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=animal+rescue+OR+welfare+when:7d&hl=en&gl=US&ceid=US:en",
        ],
        "panel": [
            {
                "role": "Wildlife Biologist",
                "goal": "Explain the science and conservation stakes of the chosen story.",
                "backstory": "A zoologist who follows wildlife research and conservation programmes worldwide.",
            },
            {
                "role": "Animal Welfare Advocate",
                "goal": "Bring the animal welfare and human-impact perspective to the story.",
                "backstory": "A campaigner who works with animal welfare organisations around the world.",
            },
            SKEPTIC,
        ],
    },
]
