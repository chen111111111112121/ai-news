import json
import sys
from datetime import datetime, timezone
import yaml

from scripts.fetchers import fetch_source
from scripts.process import dedup, within_days, sort_desc, truncate_per_source, mark_policy

CATEGORIES = ["news", "papers", "opensource", "community"]


def load_sources(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_data(sources_cfg: dict, now: datetime = None) -> dict:
    now = now or datetime.now(timezone.utc)
    now_ts = int(now.timestamp())
    defaults = sources_cfg.get("defaults", {})
    max_per_source = int(defaults.get("max_per_source", 30))
    days_window = int(defaults.get("days_window", 7))
    keywords = sources_cfg.get("policy_keywords", [])

    all_items = []
    for cfg in sources_cfg.get("sources", []):
        fetched = fetch_source(cfg, keywords=keywords, now_ts=now_ts)
        print(f"[ok] {cfg.get('name')}: {len(fetched)} 条", file=sys.stderr)
        all_items.extend(fetched)

    all_items = within_days(all_items, days_window, now=now)
    all_items = dedup(all_items)
    all_items = sort_desc(all_items)
    all_items = truncate_per_source(all_items, max_per_source)
    mark_policy(all_items, keywords)

    return {
        "generated_at": now.isoformat(),
        "categories": CATEGORIES,
        "items": [it.to_dict() for it in all_items],
    }


def run(sources_cfg: dict, out_path: str, now: datetime = None) -> dict:
    data = build_data(sources_cfg, now=now)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[done] 写入 {len(data['items'])} 条到 {out_path}", file=sys.stderr)
    return data


def main():
    cfg = load_sources("sources.yaml")
    run(cfg, out_path="data.json")


if __name__ == "__main__":
    main()
