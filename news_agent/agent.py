"""
Interactive CLI agent for the News Intelligence Agent.

Supports natural language queries like:
  "What's happening in MENA fintech today?"
  "Show me the latest from FT Lex"
  "Give me a daily briefing"

Run with: python -m news_agent.agent
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

import google.generativeai as genai
from dotenv import load_dotenv

from .fetcher import Article, aggregate_news
from .sources import TOPICS
from .summarizer import generate_daily_briefing, summarize_batch

load_dotenv()
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

_cached_articles: list[Article] = []
_last_fetch: datetime | None = None


def _print_header():
    print("\n" + "=" * 60)
    print("  NewsIntel  --  Financial News Intelligence Agent")
    print("=" * 60)
    print()
    print("  Commands:")
    print("    briefing         Generate today's daily briefing")
    print("    fetch [topic]    Fetch latest news (topics: fintech, markets, mena, tech)")
    print("    search <query>   Search fetched articles by keyword")
    print("    show <n>         Show full details for article #n")
    print("    ask <question>   Ask an AI question about today's news")
    print("    sources          List all configured sources")
    print("    help             Show this help")
    print("    quit             Exit")
    print()


def _print_article_list(articles: list[Article], limit: int = 20):
    if not articles:
        print("  No articles found.\n")
        return
    for i, a in enumerate(articles[:limit], 1):
        pw = " [PAYWALLED]" if a.is_paywalled else ""
        topics_str = ", ".join(a.topics)
        print(f"  {i:>3}. [{a.publisher}]{pw} {a.title}")
        print(f"       {a.published_display}  |  Topics: {topics_str}")
        if a.summary:
            print(f"       {a.summary[:120]}...")
        print()
    if len(articles) > limit:
        print(f"  ... and {len(articles) - limit} more articles.\n")


def _print_article_detail(article: Article, index: int):
    print(f"\n  {'=' * 56}")
    print(f"  Article #{index}")
    print(f"  {'=' * 56}")
    print(f"  Title:     {article.title}")
    print(f"  Publisher: {article.publisher}")
    print(f"  Date:      {article.published_display}")
    print(f"  URL:       {article.url}")
    print(f"  Topics:    {', '.join(article.topics)}")
    print()
    if article.summary:
        print(f"  RSS Summary:\n  {article.summary}\n")
    if article.preview_text:
        print(f"  Free Preview:\n  {article.preview_text[:500]}\n")
    if article.ai_brief:
        print(f"  AI Brief:\n  {article.ai_brief}\n")


async def _do_fetch(topic: str | None = None) -> list[Article]:
    global _cached_articles, _last_fetch
    topics = [topic] if topic and topic != "all" else None
    print("  Fetching news from all sources... (this may take 15-30 seconds)")
    articles = await aggregate_news(topics=topics)
    _cached_articles = articles
    _last_fetch = datetime.now(timezone.utc)

    publishers = {}
    for a in articles:
        publishers[a.publisher] = publishers.get(a.publisher, 0) + 1
    breakdown = ", ".join(f"{p}: {c}" for p, c in sorted(publishers.items()))
    print(f"  Fetched {len(articles)} articles ({breakdown})\n")
    return articles


async def _do_briefing():
    if not _cached_articles:
        await _do_fetch()

    print("  Summarizing top articles with AI...")
    top = _cached_articles[:20]
    await summarize_batch(top)

    print("  Generating daily briefing...\n")
    briefing = await generate_daily_briefing(top)
    print("  " + "-" * 56)
    print("  DAILY INTELLIGENCE BRIEFING")
    print("  " + "-" * 56)
    for line in briefing.split("\n"):
        print(f"  {line}")
    print()


async def _do_ask(question: str):
    if not _cached_articles:
        print("  No articles loaded. Running fetch first...")
        await _do_fetch()

    context_entries = []
    for a in _cached_articles[:25]:
        entry = f"- [{a.publisher}] {a.title}: {a.summary or '(no summary)'}"
        if a.ai_brief:
            entry += f"\n  Brief: {a.ai_brief[:200]}"
        context_entries.append(entry)

    context = "\n".join(context_entries)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("  Error: GEMINI_API_KEY not set.\n")
        return

    genai.configure(api_key=api_key)
    model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    model = genai.GenerativeModel(model_name)

    prompt = (
        f"You are a financial news analyst. Based on the following articles from today, "
        f"answer the user's question concisely and informatively. Do NOT reproduce verbatim "
        f"article text. Synthesize in your own words.\n\n"
        f"TODAY'S ARTICLES:\n{context}\n\n"
        f"USER QUESTION: {question}\n\n"
        f"Answer in a clear, analytical tone. Keep it under 300 words."
    )

    try:
        response = await model.generate_content_async(prompt)
        print(f"\n  {'=' * 56}")
        for line in response.text.strip().split("\n"):
            print(f"  {line}")
        print(f"  {'=' * 56}\n")
    except Exception as e:
        print(f"  AI query failed: {e}\n")


def _search_articles(query: str) -> list[Article]:
    q = query.lower()
    return [
        a for a in _cached_articles
        if q in a.title.lower()
        or q in a.summary.lower()
        or q in (a.preview_text or "").lower()
        or q in a.publisher.lower()
        or any(q in t for t in a.topics)
    ]


async def main():
    _print_header()

    while True:
        try:
            raw = input("  newsagent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye.\n")
            break

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("quit", "exit", "q"):
            print("  Goodbye.\n")
            break

        elif cmd == "help":
            _print_header()

        elif cmd == "sources":
            from .sources import ALL_FEEDS
            print(f"\n  Configured feeds ({len(ALL_FEEDS)}):\n")
            for f in ALL_FEEDS:
                pw = " [PAYWALLED]" if f.is_paywalled else ""
                print(f"    {f.name}{pw}")
                print(f"      {f.url}")
                print(f"      Topics: {', '.join(f.topics)}\n")

        elif cmd == "fetch":
            topic = arg if arg in TOPICS else None
            articles = await _do_fetch(topic)
            _print_article_list(articles)

        elif cmd == "briefing":
            await _do_briefing()

        elif cmd == "search":
            if not arg:
                print("  Usage: search <keyword>\n")
                continue
            if not _cached_articles:
                print("  No articles loaded. Run 'fetch' first.\n")
                continue
            results = _search_articles(arg)
            print(f"\n  Search results for '{arg}':\n")
            _print_article_list(results)

        elif cmd == "show":
            if not arg or not arg.isdigit():
                print("  Usage: show <article_number>\n")
                continue
            idx = int(arg)
            if not _cached_articles or idx < 1 or idx > len(_cached_articles):
                print(f"  Invalid article number. Range: 1-{len(_cached_articles)}\n")
                continue
            article = _cached_articles[idx - 1]
            if not article.ai_brief:
                print("  Generating AI brief...")
                from .summarizer import summarize_article
                await summarize_article(article)
            _print_article_detail(article, idx)

        elif cmd == "ask":
            if not arg:
                print("  Usage: ask <your question>\n")
                continue
            await _do_ask(arg)

        else:
            # Treat the full input as a natural language question
            await _do_ask(raw)


if __name__ == "__main__":
    asyncio.run(main())
