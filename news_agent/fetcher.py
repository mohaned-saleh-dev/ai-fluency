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

async def extract_free_preview(client: httpx.AsyncClient, url: str) -> str:
    """Pull publicly served meta descriptions and the first few <p> tags."""
    try:
        resp = await client.get(url, timeout=FETCH_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        logger.debug("Preview fetch failed for %s: %s", url, e)
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")
    parts: list[str] = []

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        parts.append(og_desc["content"].strip())

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        desc = meta_desc["content"].strip()
        if desc not in parts:
            parts.append(desc)

    p_count = 0
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 60 and text not in parts:
            parts.append(text)
            p_count += 1
            if p_count >= 3:
                break

    return " ".join(parts)[:1500]


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
            # Bloomberg returns 403 on all direct article URLs; skip them
            skip_domains = {"bloomberg.com"}
            targets = [
                a for a in all_articles[:max_preview_count]
                if not any(d in a.url for d in skip_domains)
            ]
            preview_results = await asyncio.gather(
                *[extract_free_preview(client, a.url) for a in targets],
                return_exceptions=True,
            )
            for article, preview in zip(targets, preview_results):
                if isinstance(preview, str) and preview:
                    article.preview_text = preview

    logger.info("Aggregation complete: %d articles from %d feeds", len(all_articles), len(feed_sources))
    return all_articles
