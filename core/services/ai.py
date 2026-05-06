"""OpenAI-backed copy with safe fallbacks when no API key."""

from __future__ import annotations

import json
import os
from typing import Any

from django.utils import timezone as dj_tz


def _client():
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    from openai import OpenAI

    return OpenAI(api_key=api_key)


def _chat(
    prompt: str,
    max_tokens: int = 900,
    *,
    json_object: bool = False,
) -> str | None:
    client = _client()
    if not client:
        return None
    try:
        kwargs: dict[str, Any] = {
            "model": os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
            "messages": [
                {
                    "role": "system",
                    "content": "You write concise, conversion-focused marketing copy.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        if json_object:
            kwargs["response_format"] = {"type": "json_object"}
        r = client.chat.completions.create(**kwargs)
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return None


def fallback_website_copy(business) -> dict[str, str]:
    bn, svc, ct = business.name, business.service, business.city
    return {
        "hero_title": f"{bn} — {svc} in {ct}",
        "hero_subtitle": (
            f"Fast, reliable {svc.lower()} serving {ct}. "
            "Request a quote today — friendly crew, fair pricing."
        ),
        "services_text": (
            f"• Residential & commercial {svc.lower()}\n"
            f"• Same-week availability\n"
            f"• Serving {ct} and nearby areas\n"
            "• Fully insured / professional team"
        ),
        "testimonials_text": (
            f"• “Saved us hours—{bn} showed up when they said they would.” — Alex M., {ct}\n"
            f"• “Fair price and straightforward. Will use again.” — Jordan R., near {ct}\n"
            f"• “Easy to schedule. Crew was respectful.” — Sam T., {ct}"
        ),
        "meta_description": f"{svc} in {ct} by {bn}. Request service today.",
    }


def ai_website_bundle(business) -> dict[str, Any]:
    """Return dict suited for Website model fields."""

    fb = fallback_website_copy(business)
    now = dj_tz.now()
    prompt = f"""Business name: "{business.name}"
Service: "{business.service}"
City: "{business.city}"

Return JSON only with keys:
hero_title (string, short headline)
hero_subtitle (string, 2 sentences plain text)
services_text (string, 4-6 lines each starting with "• ")
testimonials_text (string, exactly 3 fictional quote lines starting with "• ")
meta_description (string, <= 300 chars SEO)"""

    text = _chat(prompt, max_tokens=900, json_object=True)
    if not text:
        fb["generated_at"] = now
        return fb
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        fb["generated_at"] = now
        return fb
    return {
        "hero_title": str(data.get("hero_title") or fb["hero_title"])[:240],
        "hero_subtitle": str(data.get("hero_subtitle") or fb["hero_subtitle"])[:2000],
        "services_text": str(data.get("services_text") or fb["services_text"])[:5000],
        "testimonials_text": str(data.get("testimonials_text") or fb["testimonials_text"])[:5000],
        "meta_description": str(data.get("meta_description") or fb["meta_description"])[:300],
        "generated_at": now,
    }


def fallback_posts_bundle(business) -> str:
    svc, bn, ct = business.service, business.name, business.city
    return (
        f"1. Need {svc.lower()} fast in {ct}? {bn} has you covered—DM us!\n\n"
        f"2. This week only: prioritize {svc.lower()} jobs in {ct}. Comment CALL for a quote.\n\n"
        f"3. Before/after season? Book {svc.lower()}—we show up when we say we will ({bn})."
    )


def ai_facebook_posts(business) -> str:
    r = _chat(
        f"Write exactly 3 Facebook posts for '{business.name}' ({business.service}) in {business.city}. "
        "Separate posts with blank lines. Casual, short, conversion-focused.",
        max_tokens=500,
    )
    return r or fallback_posts_bundle(business)


def ai_google_update(business) -> str:
    r = _chat(
        f"Write one Google Business Profile update (<300 chars) for {business.service} "
        f"business '{business.name}' in {business.city}. End with soft CTA.",
        max_tokens=180,
    )
    return (
        r
        or f"{business.name}: {business.service} in {business.city}. Book today—friendly team, dependable scheduling."
    )[:299]


def ai_short_ad(business) -> str:
    r = _chat(
        f"Short paid ad headline + 2 lines body for '{business.name}' ({business.service}, {business.city}).",
        max_tokens=200,
    )
    return r or f"Hire {business.name}\nFast {business.service.lower()} in {business.city}. Get a quote now."
