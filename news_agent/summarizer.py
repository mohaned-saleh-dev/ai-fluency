"""
Summarizer module for the News Intelligence Agent.

Uses Gemini to produce structured intelligence briefs from raw article data.
Never reproduces verbatim article text -- only synthesizes and summarizes.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv

from .fetcher import Article

load_dotenv()

logger = logging.getLogger(__name__)

_model: Optional[genai.GenerativeModel] = None


def _get_model() -> genai.GenerativeModel:
    global _model
    if _model is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment")
        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        _model = genai.GenerativeModel(model_name)
    return _model


ARTICLE_BRIEF_PROMPT = """\
You are a senior financial analyst assistant. Given the following article metadata, \
produce a concise intelligence brief. Do NOT reproduce verbatim article text. \
Instead, synthesize the information into your own words.

ARTICLE:
- Title: {title}
- Publisher: {publisher}
- Published: {published}
- RSS Summary: {summary}
- Free Preview Excerpt: {preview}

Produce a brief in this exact format:

**Key Facts**
- (3-5 bullet points of the essential information)

**Why It Matters**
(One short paragraph explaining the significance and implications)

**Topic Tags**: (comma-separated relevant tags)

Be concise. Total response should be under 200 words.
"""

DAILY_BRIEFING_PROMPT = """\
You are a senior financial analyst producing a morning intelligence briefing. \
Below are summaries of today's top articles from major financial publications. \
Synthesize them into a cohesive daily briefing. Do NOT reproduce any verbatim text.

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


async def summarize_article(article: Article) -> str:
    """Generate an AI intelligence brief for a single article."""
    model = _get_model()

    prompt = ARTICLE_BRIEF_PROMPT.format(
        title=article.title,
        publisher=article.publisher,
        published=article.published_display,
        summary=article.summary or "(not available)",
        preview=article.preview_text or "(not available)",
    )

    try:
        response = await model.generate_content_async(prompt)
        brief = response.text.strip()
        article.ai_brief = brief
        return brief
    except Exception as e:
        logger.error("Summarization failed for '%s': %s", article.title, e)
        return ""


async def generate_daily_briefing(articles: list[Article]) -> str:
    """Generate a synthesized daily briefing across all articles."""
    model = _get_model()

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
        response = await model.generate_content_async(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error("Daily briefing generation failed: %s", e)
        return "Daily briefing generation failed. Please try again."


async def summarize_batch(
    articles: list[Article],
    requests_per_minute: int = 4,
) -> list[Article]:
    """Summarize articles sequentially, respecting the Gemini free-tier rate limit."""
    import asyncio

    delay = 60.0 / requests_per_minute

    for i, article in enumerate(articles):
        logger.info("Summarizing %d/%d: %s", i + 1, len(articles), article.title[:60])
        await summarize_article(article)
        if i < len(articles) - 1:
            await asyncio.sleep(delay)

    return articles
