import re
import html as _html
import sys
import calendar
import requests
from datetime import datetime, timezone
from typing import List

import feedparser

from scripts.models import Item

REQUEST_TIMEOUT = 20


def _struct_to_utc(struct_time):
    if struct_time is None:
        return None
    return datetime.fromtimestamp(calendar.timegm(struct_time), tz=timezone.utc)


def parse_rss(text, source: str, category: str) -> List[Item]:
    """从 RSS/Atom 文本解析出 Item 列表。缺发布时间的条目跳过。"""
    feed = feedparser.parse(text)
    items = []
    for e in feed.entries:
        published = _struct_to_utc(
            getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
        )
        if published is None:
            continue
        link = getattr(e, "link", "")
        title = getattr(e, "title", "")
        if not link or not title:
            continue
        summary = getattr(e, "summary", "")
        items.append(Item(title, link, source, category, published, summary))
    return items


def parse_hackernews(data: dict, source: str, category: str) -> List[Item]:
    items = []
    for h in data.get("hits", []):
        title = h.get("title")
        ts = h.get("created_at_i")
        if not title or ts is None:
            continue
        url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        published = datetime.fromtimestamp(ts, tz=timezone.utc)
        items.append(Item(title, url, source, category, published, ""))
    return items
