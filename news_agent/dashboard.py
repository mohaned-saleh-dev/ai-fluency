"""
Flask web dashboard for the News Intelligence Agent.

Page loads instantly. RSS articles appear within seconds.
AI briefs fill in progressively in the background.
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

    articles = await aggregate_news(fetch_previews=False)

    _cache["articles"] = articles
    _cache["last_refresh"] = datetime.now(timezone.utc)
    _cache["status"] = "ready"
    logger.info("Background: %d articles ready. Starting AI summaries...", len(articles))

    for i, article in enumerate(articles[:10]):
        logger.info("AI summary %d/10: %s", i + 1, article.title[:50])
        await summarize_article(article)
        await asyncio.sleep(16)

    briefing = await generate_daily_briefing(articles[:10])
    _cache["daily_briefing"] = briefing
    logger.info("Background: daily briefing generated.")


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
    if _cache["status"] not in ("fetching",):
        _cache["last_refresh"] = None
        _cache["status"] = "idle"
        _trigger_background_refresh()
    return jsonify({"status": "started"})


if __name__ == "__main__":
    port = int(os.getenv("NEWS_AGENT_PORT", "5050"))
    print(f"\n  News Intelligence Dashboard: http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
