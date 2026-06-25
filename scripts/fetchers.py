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
        try:
            title = h.get("title")
            ts = h.get("created_at_i")
            if not title or ts is None:
                continue
            object_id = h.get("objectID")
            url = h.get("url") or (
                f"https://news.ycombinator.com/item?id={object_id}" if object_id else "")
            if not url:
                continue
            published = datetime.fromtimestamp(ts, tz=timezone.utc)
            items.append(Item(title, url, source, category, published, ""))
        except Exception as exc:  # noqa: BLE001
            _log(f"[skip-row] HN: {exc}")
            continue
    return items


_ARTICLE_RE = re.compile(r'<article\b.*?</article>', re.DOTALL)
_NAME_RE = re.compile(
    r'<h2[^>]*class="h3[^"]*"[^>]*>\s*<a[^>]*href="(/[^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL,
)
_DESC_RE = re.compile(r'<p[^>]*class="col-9[^"]*"[^>]*>(.*?)</p>', re.DOTALL)


def _strip_tags(s: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def _keyword_matches(haystack_lower: str, tokens: set, keyword: str) -> bool:
    """Return True if keyword matches the haystack using token-aware logic.

    Multi-word or hyphenated keywords (e.g. "machine learning", "fine-tun") use
    substring match against the full lowercased haystack string so partial phrases
    are still found.  Single-token keywords (e.g. "ai", "gpt", "llm") must be
    present as a complete token to avoid false positives like "ai" inside
    "container" or "daily".
    """
    if " " in keyword or "-" in keyword:
        return keyword in haystack_lower
    return keyword in tokens


def parse_github_trending(text, source, category, keywords, now_ts) -> List[Item]:
    """解析 github.com/trending 页面，按 <article> 分块逐个解析，按关键词过滤。
    trending 页无发布时间，统一用抓取时间 now_ts。
    keywords 为空列表时不过滤，返回全部仓库。"""
    lowered = [k.lower() for k in keywords]
    published = datetime.fromtimestamp(now_ts, tz=timezone.utc)
    items = []
    for block in _ARTICLE_RE.findall(text):
        m = _NAME_RE.search(block)
        if not m:
            continue
        href, name_html = m.group(1), m.group(2)
        name = re.sub(r"\s+", " ", _strip_tags(name_html)).strip()
        dm = _DESC_RE.search(block)
        desc = _strip_tags(dm.group(1)) if dm else ""
        if lowered:
            haystack = (name + " " + desc + " " + href).lower()
            tokens = set(re.findall(r"[a-z0-9]+", haystack))
            if not any(_keyword_matches(haystack, tokens, k) for k in lowered):
                continue
        url = "https://github.com" + href.strip()
        items.append(Item(name, url, source, category, published, desc))
    return items


def _parse_iso_utc(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_hf_papers(data: list, source: str, category: str) -> List[Item]:
    items = []
    for row in data:
        try:
            paper = row.get("paper", {})
            pid = paper.get("id")
            title = paper.get("title")
            ts = row.get("publishedAt")
            if not pid or not title or not ts:
                continue
            published = _parse_iso_utc(ts)
            url = f"https://huggingface.co/papers/{pid}"
            items.append(Item(title, url, source, category, published, paper.get("summary", "")))
        except Exception as exc:  # noqa: BLE001 — 单行坏数据不影响其他行
            _log(f"[skip-row] HF Papers: {exc}")
            continue
    return items


_HEADERS = {"User-Agent": "ai-news-aggregator/1.0 (+https://github.com/chen111111111112121/ai-news)"}


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _http_get_text(url: str) -> str:
    r = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text


def _http_get_json(url: str):
    r = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def fetch_source(cfg: dict, keywords: list, now_ts: int) -> List[Item]:
    """按源配置抓取并解析。任何异常都吞掉并返回 []，保证不影响其他源。"""
    name = cfg.get("name", "?")
    typ = cfg.get("type")
    category = cfg.get("category", "news")
    try:
        if typ == "rss":
            return parse_rss(_http_get_text(cfg["url"]), name, category)
        if typ == "hackernews":
            query = cfg.get("query", "AI")
            url = ("https://hn.algolia.com/api/v1/search_by_date"
                   f"?query={requests.utils.quote(query)}&tags=story&hitsPerPage=50")
            return parse_hackernews(_http_get_json(url), name, category)
        if typ == "github_trending":
            url = cfg.get("url", "https://github.com/trending?since=daily")
            # 使用源自己的 filter_keywords（如配置了），否则不过滤（返回全部 trending 仓库）。
            # 全局 keywords 是 policy 关键词，不应作为 trending 仓库的纳入过滤条件。
            filter_kw = cfg.get("filter_keywords", [])
            return parse_github_trending(
                _http_get_text(url), name, category, filter_kw, now_ts)
        if typ == "hf_papers":
            url = cfg.get("url", "https://huggingface.co/api/daily_papers")
            return parse_hf_papers(_http_get_json(url), name, category)
        _log(f"[skip] 未知源类型: {typ} ({name})")
        return []
    except Exception as exc:  # noqa: BLE001 — 故意吞掉，单源失败不影响整体
        _log(f"[error] 源抓取失败: {name} ({typ}): {exc}")
        return []
