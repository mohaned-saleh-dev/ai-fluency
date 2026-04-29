"""
Summarizer module for the News Intelligence Agent.

Uses OpenAI (GPT-4o-mini) for fast, cheap article summarization.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI

from .fetcher import Article

load_dotenv()

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None
MODEL = "gpt-4o-mini"


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment")
        _client = AsyncOpenAI(api_key=api_key)
    return _client


ARTICLE_BRIEF_PROMPT = """\
You are a senior financial analyst and business journalist. A reader wants to \
understand what a paywalled article is about WITHOUT having a subscription. \
Using the headline, publisher, date, and any available summary below, write a \
comprehensive briefing.

ARTICLE:
- Title: {title}
- Publisher: {publisher}
- Published: {published}
- Available summary: {summary}
- Additional context: {preview}

Write a full briefing covering:

1. **What happened** — Explain the core news event or development in 3-4 sentences. \
Use your knowledge to fill in context beyond the headline.

2. **Background** — 2-3 sentences of essential context. What led to this? What's the \
history?

3. **Key details** — 4-6 bullet points covering the most important facts, numbers, \
names, and specifics that a reader of this article would learn.

4. **Why it matters** — 2-3 sentences on the implications for markets, businesses, \
or the broader economy.

5. **What to watch** — 1-2 sentences on what happens next.

Write 300-400 words total. Use a professional, analytical tone. Draw on your training \
knowledge to provide real substance — don't just rephrase the headline. The reader \
should feel they understand the story as well as if they had read the full article.
"""

DAILY_BRIEFING_PROMPT = """\
You are a senior financial analyst producing a morning intelligence briefing. \
Below are summaries of today's top articles from major financial publications. \
Synthesize them into a cohesive daily briefing.

ARTICLES:
{articles_block}

Produce a daily briefing with these sections:

## Top Themes Today
(3-5 themes with 2-3 sentence explanations each)

## Market Signals
(Key takeaways for financial markets, if applicable)

## MENA Spotlight
(Relevant developments in the MENA region, if any articles touch on this)

## Fintech & Payments
(Notable fintech/payments developments, if any)

## What to Watch
(2-3 forward-looking points about upcoming events or trends)

Keep the entire briefing under 500 words. Write in a crisp, analytical tone.
"""


async def _generate(prompt: str, max_tokens: int = 1024) -> str:
    client = _get_client()
    resp = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


async def summarize_article(article: Article) -> str:
    """Generate an AI intelligence brief for a single article."""
    prompt = ARTICLE_BRIEF_PROMPT.format(
        title=article.title,
        publisher=article.publisher,
        published=article.published_display,
        summary=article.summary or "(not available)",
        preview=article.preview_text[:3000] if article.preview_text else "(not available)",
    )

    try:
        brief = await _generate(prompt)
        article.ai_brief = brief
        article.ai_status = "done"
        return brief
    except Exception as e:
        logger.error("Summarization failed for '%s': %s", article.title, e)
        article.ai_status = "error"
        return ""


async def generate_daily_briefing(articles: list[Article]) -> str:
    """Generate a synthesized daily briefing across all articles."""
    article_entries = []
    for i, a in enumerate(articles[:30], 1):
        entry = (
            f"{i}. [{a.publisher}] {a.title}\n"
            f"   Summary: {a.summary or '(none)'}\n"
            f"   AI Brief: {a.ai_brief or '(not yet summarized)'}"
        )
        article_entries.append(entry)

    articles_block = "\n\n".join(article_entries)
    prompt = DAILY_BRIEFING_PROMPT.format(articles_block=articles_block)

    try:
        return await _generate(prompt, max_tokens=1500)
    except Exception as e:
        logger.error("Daily briefing generation failed: %s", e)
        return "Daily briefing generation failed. Please try again."


async def summarize_batch(
    articles: list[Article],
    concurrency: int = 10,
) -> list[Article]:
    """Summarize articles concurrently."""
    sem = asyncio.Semaphore(concurrency)

    async def _do(i: int, article: Article):
        async with sem:
            logger.info("Summarizing %d/%d: %s", i + 1, len(articles), article.title[:60])
            await summarize_article(article)

    await asyncio.gather(*[_do(i, a) for i, a in enumerate(articles)])
    return articles
