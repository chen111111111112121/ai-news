from datetime import datetime, timezone
from scripts.models import Item, clean_url


def test_clean_url_strips_tracking_params():
    url = "https://example.com/post?utm_source=rss&utm_medium=feed&id=5"
    assert clean_url(url) == "https://example.com/post?id=5"


def test_clean_url_removes_trailing_question_mark():
    assert clean_url("https://example.com/post?utm_source=x") == "https://example.com/post"


def test_item_to_dict_serializes_time_as_iso():
    dt = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    item = Item(
        title="Hello",
        url="https://example.com/a?utm_source=rss",
        source="TestSource",
        category="news",
        published=dt,
        summary="abc",
    )
    d = item.to_dict()
    assert d["title"] == "Hello"
    assert d["url"] == "https://example.com/a"
    assert d["source"] == "TestSource"
    assert d["category"] == "news"
    assert d["published"] == "2026-06-25T12:00:00+00:00"
    assert d["summary"] == "abc"
    assert d["is_policy"] is False


def test_item_dedup_key_uses_clean_url():
    item = Item("t", "https://e.com/x?utm_source=rss", "s", "news",
                datetime(2026, 6, 25, tzinfo=timezone.utc), "")
    assert item.dedup_key() == "https://e.com/x"


def test_clean_url_strips_fragment():
    assert clean_url("https://example.com/post#section2?utm_source=x") == "https://example.com/post"
    assert clean_url("https://example.com/a#anchor") == "https://example.com/a"


def test_clean_url_rejects_non_http_schemes():
    assert clean_url("javascript:alert(1)") == ""
    assert clean_url('https://x/"%20onmouseover="alert(1)'.split('"')[0]) == "https://x/"
    assert clean_url("data:text/html,<script>") == ""
    assert clean_url("http://example.com/ok") == "http://example.com/ok"
