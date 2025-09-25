#!/usr/bin/env python3
from __future__ import annotations

from datetime import date
from typing import List
import os

DEFAULT_TOPICS_FALLBACK = "Minimalismus,Selbstentwicklung,Frugalismus,Investieren"


def resolve_topics() -> List[str]:
    """Parse topics from environment variables with graceful defaults."""
    raw_topics = os.getenv("TOPICS", "")
    if raw_topics:
        candidates = [topic.strip() for topic in raw_topics.split(",")]
    else:
        default_raw = os.getenv("DEFAULT_TOPICS", DEFAULT_TOPICS_FALLBACK)
        candidates = [topic.strip() for topic in default_raw.split(",")]
    filtered = [topic for topic in candidates if topic]
    if not filtered:
        filtered = [topic.strip() for topic in DEFAULT_TOPICS_FALLBACK.split(",") if topic.strip()]
    return filtered


def pick_for_today(topics: List[str]) -> str:
    """Return a deterministic topic based on the current date."""
    if not topics:
        raise ValueError("Topic list must not be empty.")
    today = date.today()
    base = date(2025, 1, 1)
    delta_days = (today - base).days
    index = delta_days % len(topics)
    return topics[index]
