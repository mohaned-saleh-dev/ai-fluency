"""
Source definitions for the News Intelligence Agent.

Curated feeds from Financial Times, Bloomberg, and Harvard Business Review only.
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
        name="FT Companies & Markets",
        url="https://www.ft.com/companies-markets?format=rss",
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
        name="Bloomberg Middle East",
        url="https://feeds.bloomberg.com/middle-east/news.rss",
        publisher="Bloomberg",
        topics=["mena"],
        is_paywalled=True,
    ),
]

# ---------------------------------------------------------------------------
# Harvard Business Review
# ---------------------------------------------------------------------------

HBR_FEEDS = [
    RSSSource(
        name="HBR - Main Feed",
        url="https://feeds.hbr.org/harvardbusiness",
        publisher="Harvard Business Review",
        topics=["markets"],
        is_paywalled=True,
    ),
    RSSSource(
        name="HBR - Most Popular",
        url="https://hbr.org/rss/most-popular",
        publisher="Harvard Business Review",
        topics=["markets"],
        is_paywalled=True,
    ),
    RSSSource(
        name="HBR - Technology",
        url="https://hbr.org/topic/technology/feed",
        publisher="Harvard Business Review",
        topics=["fintech"],
        is_paywalled=True,
    ),
    RSSSource(
        name="HBR - Finance",
        url="https://hbr.org/topic/finance/feed",
        publisher="Harvard Business Review",
        topics=["markets", "fintech"],
        is_paywalled=True,
    ),
]

# ---------------------------------------------------------------------------
# Aggregated list
# ---------------------------------------------------------------------------

ALL_FEEDS: list[RSSSource] = FT_FEEDS + BLOOMBERG_FEEDS + HBR_FEEDS

PAYWALLED_PUBLISHERS = {"Financial Times", "Bloomberg", "Harvard Business Review"}


def get_feeds_by_topic(topic: str) -> list[RSSSource]:
    return [f for f in ALL_FEEDS if topic in f.topics]


def get_feeds_by_publisher(publisher: str) -> list[RSSSource]:
    return [f for f in ALL_FEEDS if f.publisher == publisher]
