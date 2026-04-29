"""
Source definitions for the News Intelligence Agent.

Curated feeds from Financial Times, Bloomberg, and Harvard Business Review.
HBR article RSS was discontinued; HBR articles are included via the main feed fallback.
"""

from dataclasses import dataclass, field


@dataclass
class RSSSource:
    name: str
    url: str
    publisher: str
    topics: list[str] = field(default_factory=list)
    is_paywalled: bool = False


TOPICS = {
    "fintech": "Fintech / Payments",
    "markets": "Markets / Economy",
    "mena": "MENA / Gulf",
}

# ---------------------------------------------------------------------------
# Financial Times
# ---------------------------------------------------------------------------

FT_FEEDS = [
    RSSSource(
        name="FT Home",
        url="https://www.ft.com/rss/home",
        publisher="Financial Times",
        topics=["markets"],
        is_paywalled=True,
    ),
    RSSSource(
        name="FT Companies",
        url="https://www.ft.com/companies?format=rss",
        publisher="Financial Times",
        topics=["markets"],
        is_paywalled=True,
    ),
    RSSSource(
        name="FT Markets",
        url="https://www.ft.com/markets?format=rss",
        publisher="Financial Times",
        topics=["markets"],
        is_paywalled=True,
    ),
    RSSSource(
        name="FT Lex",
        url="https://www.ft.com/lex?format=rss",
        publisher="Financial Times",
        topics=["markets"],
        is_paywalled=True,
    ),
    RSSSource(
        name="FT Technology",
        url="https://www.ft.com/technology?format=rss",
        publisher="Financial Times",
        topics=["fintech"],
        is_paywalled=True,
    ),
    RSSSource(
        name="FT Middle East & Africa",
        url="https://www.ft.com/world/mideast?format=rss",
        publisher="Financial Times",
        topics=["mena"],
        is_paywalled=True,
    ),
]

# ---------------------------------------------------------------------------
# Bloomberg
# ---------------------------------------------------------------------------

BLOOMBERG_FEEDS = [
    RSSSource(
        name="Bloomberg Markets",
        url="https://feeds.bloomberg.com/markets/news.rss",
        publisher="Bloomberg",
        topics=["markets"],
        is_paywalled=True,
    ),
    RSSSource(
        name="Bloomberg Technology",
        url="https://feeds.bloomberg.com/technology/news.rss",
        publisher="Bloomberg",
        topics=["fintech"],
        is_paywalled=True,
    ),
    RSSSource(
        name="Bloomberg Politics",
        url="https://feeds.bloomberg.com/politics/news.rss",
        publisher="Bloomberg",
        topics=["markets", "mena"],
        is_paywalled=True,
    ),
]

# ---------------------------------------------------------------------------
# Harvard Business Review (podcast feed -- articles RSS discontinued)
# ---------------------------------------------------------------------------

HBR_FEEDS = [
    RSSSource(
        name="HBR IdeaCast",
        url="http://feeds.harvardbusiness.org/harvardbusiness/ideacast",
        publisher="Harvard Business Review",
        topics=["markets"],
        is_paywalled=False,
    ),
    RSSSource(
        name="HBR On Strategy",
        url="https://feeds.feedburner.com/harvardbusiness/on-strategy",
        publisher="Harvard Business Review",
        topics=["markets"],
        is_paywalled=False,
    ),
    RSSSource(
        name="HBR On Leadership",
        url="https://feeds.feedburner.com/harvardbusiness/on-leadership",
        publisher="Harvard Business Review",
        topics=["markets"],
        is_paywalled=False,
    ),
]

# ---------------------------------------------------------------------------
# Free sources (full text extractable -- used for richer content)
# ---------------------------------------------------------------------------

FREE_FEEDS = [
    RSSSource(
        name="BBC Business",
        url="https://feeds.bbci.co.uk/news/business/rss.xml",
        publisher="BBC News",
        topics=["markets"],
    ),
    RSSSource(
        name="BBC Technology",
        url="https://feeds.bbci.co.uk/news/technology/rss.xml",
        publisher="BBC News",
        topics=["fintech"],
    ),
    RSSSource(
        name="NPR Business",
        url="https://feeds.npr.org/1006/rss.xml",
        publisher="NPR",
        topics=["markets"],
    ),
]

# ---------------------------------------------------------------------------
# Aggregated
# ---------------------------------------------------------------------------

ALL_FEEDS: list[RSSSource] = FT_FEEDS + BLOOMBERG_FEEDS + HBR_FEEDS + FREE_FEEDS

PAYWALLED_PUBLISHERS = {"Financial Times", "Bloomberg"}


def get_feeds_by_topic(topic: str) -> list[RSSSource]:
    return [f for f in ALL_FEEDS if topic in f.topics]


def get_feeds_by_publisher(publisher: str) -> list[RSSSource]:
    return [f for f in ALL_FEEDS if f.publisher == publisher]
