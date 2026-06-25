import json
from datetime import datetime, timezone
import scripts.build as B
from scripts.models import Item


def test_build_data_assembles_and_processes(monkeypatch, tmp_path):
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)

    fake_sources = {
        "defaults": {"max_per_source": 2, "days_window": 7},
        "policy_keywords": ["监管"],
        "sources": [
            {"name": "S1", "type": "rss", "category": "news", "url": "u1"},
            {"name": "S2", "type": "rss", "category": "news", "url": "u2"},
        ],
    }

    def fake_fetch(cfg, keywords, now_ts):
        if cfg["name"] == "S1":
            return [
                Item("旧的 AI 监管 消息", "https://e.com/p1", "S1", "news",
                     datetime(2026, 6, 24, tzinfo=timezone.utc), ""),
                Item("dup", "https://e.com/dup", "S1", "news",
                     datetime(2026, 6, 23, tzinfo=timezone.utc), ""),
            ]
        return [
            Item("dup copy", "https://e.com/dup", "S2", "news",
                 datetime(2026, 6, 22, tzinfo=timezone.utc), ""),
            Item("太老了", "https://e.com/old", "S2", "news",
                 datetime(2026, 6, 1, tzinfo=timezone.utc), ""),
        ]

    monkeypatch.setattr(B, "fetch_source", fake_fetch)
    result = B.build_data(fake_sources, now=now)

    titles = [i["title"] for i in result["items"]]
    assert "太老了" not in titles
    assert titles.count("dup") + titles.count("dup copy") == 1
    assert result["items"][0]["title"] == "旧的 AI 监管 消息"
    assert result["items"][0]["is_policy"] is True
    assert "generated_at" in result
    assert set(result["categories"]) == {"news", "papers", "opensource", "community"}


def test_write_data_json_roundtrip(tmp_path, monkeypatch):
    now = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)
    fake_sources = {"defaults": {"max_per_source": 5, "days_window": 7},
                    "policy_keywords": [], "sources": []}
    monkeypatch.setattr(B, "fetch_source", lambda *a, **k: [])
    out = tmp_path / "data.json"
    B.run(fake_sources, out_path=str(out), now=now)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["items"] == []
    assert "generated_at" in loaded
