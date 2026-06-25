from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {"fbclid", "gclid", "ref", "source"}


def clean_url(url: str) -> str:
    """去掉常见跟踪参数，规范化 URL，用于去重与展示。"""
    parts = urlparse(url)
    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if not k.startswith(_TRACKING_PREFIXES) and k not in _TRACKING_KEYS
    ]
    query = urlencode(kept)
    return urlunparse(parts._replace(query=query, fragment=""))


@dataclass
class Item:
    title: str
    url: str
    source: str
    category: str          # news | papers | opensource | community
    published: datetime    # 必须是 tz-aware UTC
    summary: str = ""
    is_policy: bool = field(default=False)

    def __post_init__(self):
        self.title = (self.title or "").strip()
        self.url = clean_url((self.url or "").strip())
        self.summary = (self.summary or "").strip()[:200]

    def dedup_key(self) -> str:
        return self.url or self.title.lower()

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "category": self.category,
            "published": self.published.isoformat(),
            "summary": self.summary,
            "is_policy": self.is_policy,
        }
