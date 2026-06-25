from datetime import datetime, timezone
from typing import List
from scripts.models import Item


def dedup(items: List[Item]) -> List[Item]:
    seen = set()
    out = []
    for it in items:
        k = it.dedup_key()
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def within_days(items: List[Item], days: int, now: datetime = None) -> List[Item]:
    now = now or datetime.now(timezone.utc)
    cutoff = now.timestamp() - days * 86400
    return [it for it in items if it.published.timestamp() >= cutoff]


def sort_desc(items: List[Item]) -> List[Item]:
    return sorted(items, key=lambda it: it.published, reverse=True)


def truncate_per_source(items: List[Item], n: int) -> List[Item]:
    counts = {}
    out = []
    for it in items:  # 假定已按时间倒序，先到的是较新的
        c = counts.get(it.source, 0)
        if c >= n:
            continue
        counts[it.source] = c + 1
        out.append(it)
    return out


def mark_policy(items: List[Item], keywords: List[str]) -> None:
    lowered = [k.lower() for k in keywords]
    for it in items:
        text = (it.title + " " + it.summary).lower()
        it.is_policy = it.is_policy or any(k in text for k in lowered)
