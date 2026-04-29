"""
Flask web dashboard for the News Intelligence Agent.

Page loads instantly. RSS articles appear within seconds.
AI briefs generated concurrently via OpenAI GPT-4o-mini.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request

from .fetcher import Article, aggregate_news
from .sources import TOPICS
from .summarizer import generate_daily_briefing, summarize_article

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates")

_cache: dict[str, object] = {
    "articles": [],
    "daily_briefing": "",
    "last_refresh": None,
    "status": "idle",
}

CACHE_TTL_SECONDS = 1800


def _needs_refresh() -> bool:
    if _cache["status"] in ("fetching", "summarizing"):
        return False
    last = _cache.get("last_refresh")
    if last is None:
        return True
    return (datetime.now(timezone.utc) - last).total_seconds() > CACHE_TTL_SECONDS


async def _refresh_data_async() -> None:
    _cache["status"] = "fetching"
    logger.info("Background: fetching RSS feeds...")

    articles = await aggregate_news(fetch_previews=True, max_preview_count=40)

    _cache["articles"] = articles
    _cache["last_refresh"] = datetime.now(timezone.utc)
    _cache["status"] = "summarizing"
    logger.info("Background: %d articles ready. Generating AI summaries...", len(articles))

    ft = [a for a in articles if a.publisher == "Financial Times"]
    bl = [a for a in articles if a.publisher == "Bloomberg"]
    free = [a for a in articles if not a.is_paywalled]
    queue = ft[:15] + bl[:15] + free[:5]

    seen = set()
    deduped: list[Article] = []
    for a in queue:
        if id(a) not in seen:
            deduped.append(a)
            seen.add(id(a))

    sem = asyncio.Semaphore(10)

    async def _summarize_one(i: int, article: Article):
        async with sem:
            logger.info("AI summary %d/%d: %s", i + 1, len(deduped), article.title[:50])
            await summarize_article(article)

    await asyncio.gather(*[_summarize_one(i, a) for i, a in enumerate(deduped)])

    done = sum(1 for a in deduped if a.ai_brief)
    logger.info("Background: %d/%d AI summaries complete.", done, len(deduped))

    for a in articles:
        if a.ai_status == "pending" and id(a) not in seen:
            a.ai_status = "not_queued"

    briefing = await generate_daily_briefing(deduped)
    _cache["daily_briefing"] = briefing
    _cache["status"] = "ready"
    logger.info("Background: daily briefing generated. All done.")


def _trigger_background_refresh():
    def _run():
        asyncio.run(_refresh_data_async())
    t = threading.Thread(target=_run, daemon=True)
    t.start()


@app.route("/")
def index():
    if _needs_refresh():
        _trigger_background_refresh()
    return render_template("dashboard.html", topics=TOPICS)


@app.route("/api/articles")
def api_articles():
    articles: list[Article] = _cache.get("articles", [])
    topic = request.args.get("topic", "all")
    publisher = request.args.get("publisher", "all")

    filtered = articles
    if topic != "all":
        filtered = [a for a in filtered if topic in a.topics]
    if publisher != "all":
        filtered = [a for a in filtered if a.publisher == publisher]

    return jsonify({
        "articles": [a.to_dict() for a in filtered],
        "daily_briefing": _cache.get("daily_briefing", ""),
        "total": len(articles),
        "filtered": len(filtered),
        "status": _cache["status"],
        "publishers": sorted({a.publisher for a in articles}),
        "last_refresh": _cache["last_refresh"].isoformat() if _cache["last_refresh"] else None,
    })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    if _cache["status"] not in ("fetching", "summarizing"):
        _cache["last_refresh"] = None
        _cache["status"] = "idle"
        _trigger_background_refresh()
    return jsonify({"status": "started"})


if __name__ == "__main__":
    port = int(os.getenv("NEWS_AGENT_PORT", "5050"))
    print(f"\n  News Intelligence Dashboard: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
