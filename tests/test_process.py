from datetime import datetime, timedelta, timezone
from scripts.models import Item
from scripts.process import dedup, within_days, sort_desc, truncate_per_source, mark_policy

NOW = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)


def mk(title, url, source="s", days_ago=0, category="news"):
    return Item(title, url, source, category, NOW - timedelta(days=days_ago), "")


def test_dedup_removes_same_clean_url():
    items = [
        mk("A", "https://e.com/1?utm_source=rss"),
        mk("A dup", "https://e.com/1"),
        mk("B", "https://e.com/2"),
    ]
    out = dedup(items)
    assert len(out) == 2
    assert {i.url for i in out} == {"https://e.com/1", "https://e.com/2"}


def test_within_days_filters_old_items():
    items = [mk("new", "https://e.com/1", days_ago=2),
             mk("old", "https://e.com/2", days_ago=10)]
    out = within_days(items, 7, now=NOW)
    assert [i.title for i in out] == ["new"]


def test_sort_desc_newest_first():
    items = [mk("old", "https://e.com/1", days_ago=3),
             mk("new", "https://e.com/2", days_ago=1)]
    out = sort_desc(items)
    assert [i.title for i in out] == ["new", "old"]


def test_truncate_per_source_keeps_n_per_source():
    items = [mk(f"a{i}", f"https://e.com/a{i}", source="A") for i in range(5)]
    items += [mk(f"b{i}", f"https://e.com/b{i}", source="B") for i in range(2)]
    out = truncate_per_source(items, 3)
    assert sum(1 for i in out if i.source == "A") == 3
    assert sum(1 for i in out if i.source == "B") == 2


def test_mark_policy_sets_flag_on_keyword_match():
    items = [
        mk("New AI regulation passed", "https://e.com/1"),
        mk("某国出台 AI 监管 政策", "https://e.com/2"),
        mk("A faster GPU", "https://e.com/3"),
    ]
    mark_policy(items, ["regulation", "监管", "政策"])
    assert [i.is_policy for i in items] == [True, True, False]
