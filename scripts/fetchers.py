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


_TRENDING_RE = re.compile(
    r'<h2[^>]*class="h3[^"]*"[^>]*>\s*<a[^>]*href="(/[^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL,
)
_DESC_RE = re.compile(r'<p[^>]*class="col-9[^"]*"[^>]*>(.*?)</p>', re.DOTALL)


def _strip_tags(s: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse_github_trending(text, source, category, keywords, now_ts) -> List[Item]:
    """解析 github.com/trending 页面，按关键词过滤 AI 相关仓库。
    trending 页无发布时间，统一用抓取时间 now_ts。"""
    repos = _TRENDING_RE.findall(text)
    descs = _DESC_RE.findall(text)
    lowered = [k.lower() for k in keywords]
    published = datetime.fromtimestamp(now_ts, tz=timezone.utc)
    items = []
    for idx, (href, name_html) in enumerate(repos):
        name = re.sub(r"\s+", " ", _strip_tags(name_html)).strip()
        desc = _strip_tags(descs[idx]) if idx < len(descs) else ""
        haystack = (name + " " + desc + " " + href).lower()
        if not any(k in haystack for k in lowered):
            continue
        url = "https://github.com" + href.strip()
        items.append(Item(name, url, source, category, published, desc))
    return items
