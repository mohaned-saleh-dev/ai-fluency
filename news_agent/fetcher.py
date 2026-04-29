"""
Fetcher module for the News Intelligence Agent.

Handles RSS parsing, free preview extraction from paywalled sites,
and article deduplication. Sources limited to FT, Bloomberg, and HBR.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import feedparser
import httpx
from bs4 import BeautifulSoup

from .sources import ALL_FEEDS, RSSSource

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = 15
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


@dataclass
class Article:
    title: str
    url: str
    publisher: str
    source_name: str
    published: Optional[datetime] = None
    summary: str = ""
    preview_text: str = ""
    topics: list[str] = field(default_factory=list)
    is_paywalled: bool = False
    ai_brief: Optional[str] = None
    ai_status: str = "pending"

    @property
    def fingerprint(self) -> str:
        normalized = re.sub(r"[^a-z0-9 ]", "", self.title.lower()).strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    @property
    def published_display(self) -> str:
        if not self.published:
            return "Unknown"
        return self.published.strftime("%b %d, %Y %H:%M")

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "publisher": self.publisher,
            "source_name": self.source_name,
            "published": self.published_display,
            "summary": self.summary,
            "preview_text": self.preview_text,
            "topics": self.topics,
            "is_paywalled": self.is_paywalled,
            "ai_brief": self.ai_brief,
            "ai_status": self.ai_status,
        }


# ---------------------------------------------------------------------------
# RSS Fetching
# ---------------------------------------------------------------------------

def _parse_pub_date(entry: dict) -> Optional[datetime]:
    for key in ("published", "updated", "created"):
        raw = entry.get(key)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except Exception:
                    pass
    return None


def _extract_summary(entry: dict) -> str:
    raw = entry.get("summary") or entry.get("description") or ""
    if raw:
        soup = BeautifulSoup(raw, "html.parser")
        return soup.get_text(separator=" ", strip=True)[:500]
    return ""


async def fetch_rss_feed(client: httpx.AsyncClient, source: RSSSource) -> list[Article]:
    try:
        resp = await client.get(source.url, timeout=FETCH_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", source.name, e)
        return []

    feed = feedparser.parse(resp.text)
    articles: list[Article] = []

    for entry in feed.entries:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            continue

        articles.append(
            Article(
                title=title,
                url=link,
                publisher=source.publisher,
                source_name=source.name,
                published=_parse_pub_date(entry),
                summary=_extract_summary(entry),
                topics=list(source.topics),
                is_paywalled=source.is_paywalled,
            )
        )

    logger.info("Fetched %d articles from %s", len(articles), source.name)
    return articles


# ---------------------------------------------------------------------------
# Free preview extraction (meta tags + first paragraphs)
# ---------------------------------------------------------------------------

async def extract_article_text(client: httpx.AsyncClient, url: str) -> str:
    """Extract full article text from a URL. Works best on free/non-paywalled sites."""
    try:
        resp = await client.get(url, timeout=FETCH_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        logger.debug("Article fetch failed for %s: %s", url, e)
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup.find_all(["nav", "script", "style", "footer", "header", "aside", "form", "figure"]):
        tag.decompose()

    parts: list[str] = []

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        parts.append(og_desc["content"].strip())

    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 50 and text not in parts:
            parts.append(text)

    return "\n\n".join(parts)[:5000]


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(articles: list[Article]) -> list[Article]:
    seen: dict[str, Article] = {}
    for article in articles:
        fp = article.fingerprint
        if fp in seen:
            if len(article.summary) > len(seen[fp].summary):
                seen[fp] = article
        else:
            seen[fp] = article
    return list(seen.values())


# ---------------------------------------------------------------------------
# Main aggregation pipeline
# ---------------------------------------------------------------------------

async def aggregate_news(
    topics: list[str] | None = None,
    sources: list[RSSSource] | None = None,
    fetch_previews: bool = True,
    max_preview_count: int = 20,
) -> list[Article]:
    """Fetch RSS feeds, extract free previews, deduplicate."""
    if sources is None:
        sources = ALL_FEEDS

    feed_sources = sources
    if topics:
        feed_sources = [s for s in sources if any(t in s.topics for t in topics)]

    headers = {"User-Agent": USER_AGENT}
    all_articles: list[Article] = []

    async with httpx.AsyncClient(headers=headers) as client:
        rss_tasks = [fetch_rss_feed(client, s) for s in feed_sources]
        results = await asyncio.gather(*rss_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.error("Fetch task failed: %s", result)

        all_articles = deduplicate(all_articles)
        all_articles.sort(
            key=lambda a: a.published or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        if fetch_previews:
            free_targets = [a for a in all_articles if not a.is_paywalled][:max_preview_count]
            if free_targets:
                logger.info("Extracting full text from %d free articles...", len(free_targets))
                text_results = await asyncio.gather(
                    *[extract_article_text(client, a.url) for a in free_targets],
                    return_exceptions=True,
                )
                extracted = 0
                for article, text in zip(free_targets, text_results):
                    if isinstance(text, str) and text:
                        article.preview_text = text
                        extracted += 1
                logger.info("Extracted text from %d/%d free articles", extracted, len(free_targets))

    logger.info("Aggregation complete: %d articles from %d feeds", len(all_articles), len(feed_sources))
    return all_articles
