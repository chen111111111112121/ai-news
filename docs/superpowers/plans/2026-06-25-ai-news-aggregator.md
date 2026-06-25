# AI 资讯聚合站 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个全自动的个人 AI 资讯聚合静态站，部署在 GitHub Pages，由 GitHub Actions 每 6 小时抓取国内外 AI 新闻/论文/开源/社区/政策并刷新。

**Architecture:** Python 抓取脚本（按 `sources.yaml` 配置）拉取各家 RSS/JSON/网页 → 去重/过滤/排序/截断 → 写出 `data.json`；纯静态前端（HTML+原生JS）读取 `data.json` 渲染分类卡片；GitHub Actions 定时跑脚本并部署 Pages。纯函数（数据处理）与网络抓取分离，保证可测试。

**Tech Stack:** Python 3.11、feedparser、requests、PyYAML、pytest（测试）；前端纯 HTML/CSS/原生 JS；GitHub Actions + GitHub Pages。

**部署目标:** 仓库 `https://github.com/chen111111111112121/ai-news`，站点 `https://chen111111111112121.github.io/ai-news/`。

---

## 文件结构

```
ai-news/
├─ scripts/
│  ├─ __init__.py
│  ├─ models.py        # Item 数据模型 + 规范化
│  ├─ process.py       # 去重 / 时间窗 / 排序 / 截断 / 政策标记
│  ├─ fetchers.py      # 各类型源的抓取 + 解析（解析逻辑与网络分离）
│  └─ build.py         # 入口：读 sources.yaml → 抓取 → 处理 → 写 data.json
├─ tests/
│  ├─ __init__.py
│  ├─ test_models.py
│  ├─ test_process.py
│  └─ test_fetchers.py # 用样本数据测试解析，不联网
├─ sources.yaml         # 数据源配置
├─ requirements.txt
├─ index.html
├─ style.css
├─ app.js
├─ .github/workflows/update.yml
├─ .gitignore
└─ README.md
```

**职责边界**：
- `models.py`：定义 `Item`，负责字段规范化（URL 去跟踪参数、时间转 UTC、to_dict）。纯逻辑。
- `process.py`：对 `Item` 列表做去重、时间窗过滤、排序、按源截断、政策关键词标记。纯逻辑。
- `fetchers.py`：每种源类型一个 `parse_*`（纯函数，吃原始文本/JSON 出 `Item`）+ 一个 `fetch_*`（联网包装）。
- `build.py`：编排，不含可复用逻辑。

---

## Task 1: 项目脚手架

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: 创建 requirements.txt**

```
feedparser==6.0.11
requests==2.32.3
PyYAML==6.0.2
pytest==8.3.3
```

- [ ] **Step 2: 创建 .gitignore**

```
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
.DS_Store
```

- [ ] **Step 3: 创建空包文件**

`scripts/__init__.py` 内容：
```python
```
`tests/__init__.py` 内容：
```python
```

- [ ] **Step 4: 安装依赖并验证 pytest 可用**

Run: `pip install -r requirements.txt && pytest --version`
Expected: 打印 pytest 版本号，无报错

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore scripts/__init__.py tests/__init__.py
git commit -m "chore: 项目脚手架与依赖"
```

---

## Task 2: Item 数据模型

**Files:**
- Create: `scripts/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_models.py
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_models.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'scripts.models'`

- [ ] **Step 3: 实现 models.py**

```python
# scripts/models.py
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
    return urlunparse(parts._replace(query=query))


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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_models.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/models.py tests/test_models.py
git commit -m "feat: Item 数据模型与 URL 规范化"
```

---

## Task 3: 数据处理（去重/时间窗/排序/截断/政策标记）

**Files:**
- Create: `scripts/process.py`
- Test: `tests/test_process.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_process.py
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_process.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'scripts.process'`

- [ ] **Step 3: 实现 process.py**

```python
# scripts/process.py
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
        it.is_policy = any(k in text for k in lowered)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_process.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/process.py tests/test_process.py
git commit -m "feat: 去重/时间窗/排序/截断/政策标记"
```

---

## Task 4: RSS 解析（feedparser）

**Files:**
- Create: `scripts/fetchers.py`
- Test: `tests/test_fetchers.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_fetchers.py
from scripts.fetchers import parse_rss

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Demo</title>
<item>
  <title>OpenAI ships new model</title>
  <link>https://example.com/openai?utm_source=rss</link>
  <description>A long description about the model release and details.</description>
  <pubDate>Wed, 24 Jun 2026 10:00:00 GMT</pubDate>
</item>
<item>
  <title>Second story</title>
  <link>https://example.com/second</link>
  <description>desc two</description>
  <pubDate>Tue, 23 Jun 2026 08:00:00 GMT</pubDate>
</item>
</channel></rss>"""


def test_parse_rss_extracts_items():
    items = parse_rss(SAMPLE_RSS, source="DemoSource", category="news")
    assert len(items) == 2
    first = items[0]
    assert first.title == "OpenAI ships new model"
    assert first.url == "https://example.com/openai"   # 跟踪参数被清掉
    assert first.source == "DemoSource"
    assert first.category == "news"
    assert first.published.year == 2026
    assert first.published.tzinfo is not None           # tz-aware


def test_parse_rss_skips_entries_without_date():
    no_date = SAMPLE_RSS.replace("<pubDate>Wed, 24 Jun 2026 10:00:00 GMT</pubDate>", "")
    items = parse_rss(no_date, source="S", category="news")
    # 缺日期的条目被跳过，只剩第二条
    assert len(items) == 1
    assert items[0].title == "Second story"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_fetchers.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'scripts.fetchers'`

- [ ] **Step 3: 实现 fetchers.py 的 RSS 部分**

```python
# scripts/fetchers.py
from datetime import datetime, timezone
from typing import List
import calendar
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_fetchers.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/fetchers.py tests/test_fetchers.py
git commit -m "feat: RSS 解析"
```

---

## Task 5: Hacker News 解析（Algolia JSON）

**Files:**
- Modify: `scripts/fetchers.py`
- Test: `tests/test_fetchers.py`

- [ ] **Step 1: 追加失败测试**

在 `tests/test_fetchers.py` 末尾追加：

```python
from scripts.fetchers import parse_hackernews

SAMPLE_HN = {
    "hits": [
        {
            "title": "Show HN: An LLM tool",
            "url": "https://example.com/llm-tool",
            "objectID": "111",
            "created_at_i": 1782000000,
        },
        {
            "title": "Ask HN: best GPU?",
            "url": None,
            "objectID": "222",
            "created_at_i": 1782001000,
        },
    ]
}


def test_parse_hackernews_uses_url_or_falls_back_to_hn():
    items = parse_hackernews(SAMPLE_HN, source="HN", category="community")
    assert len(items) == 2
    assert items[0].url == "https://example.com/llm-tool"
    # 没有外链时退回 HN 讨论页
    assert items[1].url == "https://news.ycombinator.com/item?id=222"
    assert items[0].published.tzinfo is not None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_fetchers.py::test_parse_hackernews_uses_url_or_falls_back_to_hn -v`
Expected: FAIL，`ImportError: cannot import name 'parse_hackernews'`

- [ ] **Step 3: 在 fetchers.py 追加实现**

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_fetchers.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/fetchers.py tests/test_fetchers.py
git commit -m "feat: Hacker News 解析"
```

---

## Task 6: GitHub Trending 解析（HTML）

**Files:**
- Modify: `scripts/fetchers.py`
- Test: `tests/test_fetchers.py`

- [ ] **Step 1: 追加失败测试**

在 `tests/test_fetchers.py` 末尾追加：

```python
from scripts.fetchers import parse_github_trending

SAMPLE_TRENDING = """
<article class="Box-row">
  <h2 class="h3"><a href="/acme/llm-runner">acme / llm-runner</a></h2>
  <p class="col-9">Fast local LLM inference</p>
</article>
<article class="Box-row">
  <h2 class="h3"><a href="/foo/web-css">foo / web-css</a></h2>
  <p class="col-9">A CSS framework</p>
</article>
"""


def test_parse_github_trending_filters_by_keywords():
    items = parse_github_trending(
        SAMPLE_TRENDING, source="GitHub Trending", category="opensource",
        keywords=["llm", "ai", "model"], now_ts=1782000000,
    )
    assert len(items) == 1
    assert items[0].title == "acme / llm-runner"
    assert items[0].url == "https://github.com/acme/llm-runner"
    assert items[0].published.tzinfo is not None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_fetchers.py::test_parse_github_trending_filters_by_keywords -v`
Expected: FAIL，`ImportError: cannot import name 'parse_github_trending'`

- [ ] **Step 3: 在 fetchers.py 追加实现**

文件顶部 import 区追加：
```python
import re
import html as _html
```

追加函数：
```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_fetchers.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/fetchers.py tests/test_fetchers.py
git commit -m "feat: GitHub Trending 解析"
```

---

## Task 7: Hugging Face Papers 解析（JSON）

**Files:**
- Modify: `scripts/fetchers.py`
- Test: `tests/test_fetchers.py`

- [ ] **Step 1: 追加失败测试**

在 `tests/test_fetchers.py` 末尾追加：

```python
from scripts.fetchers import parse_hf_papers

SAMPLE_HF = [
    {
        "paper": {"id": "2506.01234", "title": "Scaling laws revisited",
                   "summary": "We study scaling laws."},
        "publishedAt": "2026-06-24T00:00:00.000Z",
    },
    {
        "paper": {"id": "2506.05678", "title": "Better tokenizers",
                   "summary": "Tokenizer tricks."},
        "publishedAt": "2026-06-23T00:00:00.000Z",
    },
]


def test_parse_hf_papers_builds_arxiv_links():
    items = parse_hf_papers(SAMPLE_HF, source="HF Papers", category="papers")
    assert len(items) == 2
    assert items[0].title == "Scaling laws revisited"
    assert items[0].url == "https://huggingface.co/papers/2506.01234"
    assert items[0].published.year == 2026
    assert items[0].published.tzinfo is not None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_fetchers.py::test_parse_hf_papers_builds_arxiv_links -v`
Expected: FAIL，`ImportError: cannot import name 'parse_hf_papers'`

- [ ] **Step 3: 在 fetchers.py 追加实现**

```python
def _parse_iso_utc(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_hf_papers(data: list, source: str, category: str) -> List[Item]:
    items = []
    for row in data:
        paper = row.get("paper", {})
        pid = paper.get("id")
        title = paper.get("title")
        ts = row.get("publishedAt")
        if not pid or not title or not ts:
            continue
        published = _parse_iso_utc(ts)
        url = f"https://huggingface.co/papers/{pid}"
        items.append(Item(title, url, source, category, published, paper.get("summary", "")))
    return items
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_fetchers.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/fetchers.py tests/test_fetchers.py
git commit -m "feat: Hugging Face Papers 解析"
```

---

## Task 8: 联网抓取包装 + 类型分发

**Files:**
- Modify: `scripts/fetchers.py`
- Test: `tests/test_fetchers.py`

说明：`fetch_source()` 按源 `type` 分发到对应 `parse_*`，联网失败时返回空列表并打日志（不抛异常）。测试用 monkeypatch 替换网络调用，验证分发与容错，不真正联网。

- [ ] **Step 1: 追加失败测试**

在 `tests/test_fetchers.py` 末尾追加：

```python
import scripts.fetchers as F


def test_fetch_source_dispatches_rss(monkeypatch):
    monkeypatch.setattr(F, "_http_get_text", lambda url: SAMPLE_RSS)
    cfg = {"name": "Demo", "type": "rss", "category": "news",
           "url": "https://example.com/feed"}
    items = F.fetch_source(cfg, keywords=[], now_ts=1782000000)
    assert len(items) == 2
    assert items[0].source == "Demo"


def test_fetch_source_returns_empty_on_network_error(monkeypatch):
    def boom(url):
        raise RuntimeError("network down")
    monkeypatch.setattr(F, "_http_get_text", boom)
    cfg = {"name": "Demo", "type": "rss", "category": "news",
           "url": "https://example.com/feed"}
    items = F.fetch_source(cfg, keywords=[], now_ts=1782000000)
    assert items == []


def test_fetch_source_unknown_type_returns_empty():
    cfg = {"name": "X", "type": "mystery", "category": "news"}
    assert F.fetch_source(cfg, keywords=[], now_ts=1782000000) == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_fetchers.py -k fetch_source -v`
Expected: FAIL，`AttributeError`/`ImportError`（`_http_get_text`/`fetch_source` 不存在）

- [ ] **Step 3: 在 fetchers.py 追加实现**

文件顶部 import 区追加：
```python
import sys
import json as _json
import requests
```

追加函数：
```python
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
            return parse_github_trending(
                _http_get_text(url), name, category, keywords, now_ts)
        if typ == "hf_papers":
            url = cfg.get("url", "https://huggingface.co/api/daily_papers")
            return parse_hf_papers(_http_get_json(url), name, category)
        _log(f"[skip] 未知源类型: {typ} ({name})")
        return []
    except Exception as exc:  # noqa: BLE001 — 故意吞掉，单源失败不影响整体
        _log(f"[error] 源抓取失败: {name} ({typ}): {exc}")
        return []
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_fetchers.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/fetchers.py tests/test_fetchers.py
git commit -m "feat: 联网抓取包装与类型分发（含容错）"
```

---

## Task 9: 数据源配置 sources.yaml

**Files:**
- Create: `sources.yaml`

- [ ] **Step 1: 创建 sources.yaml**

```yaml
defaults:
  max_per_source: 30
  days_window: 7

policy_keywords:
  - regulation
  - policy
  - governance
  - legislation
  - executive order
  - 监管
  - 政策
  - 法案
  - 立法
  - 治理
  - 合规
  - 安全治理

sources:
  # ① 新闻资讯 — 国外
  - name: TechCrunch AI
    type: rss
    category: news
    url: https://techcrunch.com/category/artificial-intelligence/feed/
  - name: The Verge AI
    type: rss
    category: news
    url: https://www.theverge.com/rss/ai-artificial-intelligence/index.xml
  - name: VentureBeat AI
    type: rss
    category: news
    url: https://venturebeat.com/category/ai/feed/
  - name: MIT Tech Review
    type: rss
    category: news
    url: https://www.technologyreview.com/feed/
  - name: OpenAI Blog
    type: rss
    category: news
    url: https://openai.com/blog/rss.xml
  - name: Google DeepMind
    type: rss
    category: news
    url: https://deepmind.google/blog/rss.xml

  # ① 新闻资讯 — 国内（IT之家原生 RSS 稳定；机器之心/量子位经 RSSHub，尽力而为）
  - name: IT之家
    type: rss
    category: news
    url: https://www.ithome.com/rss/
  - name: 机器之心
    type: rss
    category: news
    url: https://rsshub.app/jiqizhixin/category/ai
  - name: 量子位
    type: rss
    category: news
    url: https://rsshub.app/qbitai/category/资讯

  # ② 论文 / 技术突破
  - name: arXiv cs.AI
    type: rss
    category: papers
    url: http://export.arxiv.org/rss/cs.AI
  - name: arXiv cs.CL
    type: rss
    category: papers
    url: http://export.arxiv.org/rss/cs.CL
  - name: arXiv cs.LG
    type: rss
    category: papers
    url: http://export.arxiv.org/rss/cs.LG
  - name: arXiv cs.CV
    type: rss
    category: papers
    url: http://export.arxiv.org/rss/cs.CV
  - name: HF Papers
    type: hf_papers
    category: papers
    url: https://huggingface.co/api/daily_papers

  # ③ 开源项目 / 工具
  - name: GitHub Trending
    type: github_trending
    category: opensource
    url: https://github.com/trending?since=daily

  # ④ 社区讨论
  - name: Hacker News (AI)
    type: hackernews
    category: community
    query: AI OR LLM OR GPT OR "machine learning"
  - name: r/MachineLearning
    type: rss
    category: community
    url: https://www.reddit.com/r/MachineLearning/.rss
  - name: r/LocalLLaMA
    type: rss
    category: community
    url: https://www.reddit.com/r/LocalLLaMA/.rss
  - name: r/artificial
    type: rss
    category: community
    url: https://www.reddit.com/r/artificial/.rss
```

- [ ] **Step 2: 验证 YAML 可解析**

Run: `python -c "import yaml; d=yaml.safe_load(open('sources.yaml', encoding='utf-8')); print(len(d['sources']), 'sources')"`
Expected: 打印 `19 sources`，无报错

- [ ] **Step 3: Commit**

```bash
git add sources.yaml
git commit -m "feat: 数据源配置 sources.yaml"
```

---

## Task 10: 编排入口 build.py

**Files:**
- Create: `scripts/build.py`
- Test: `tests/test_build.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_build.py
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
    assert "太老了" not in titles                 # 超过时间窗被过滤
    assert titles.count("dup") + titles.count("dup copy") == 1  # 跨源去重
    assert result["items"][0]["title"] == "旧的 AI 监管 消息"     # 最新在前
    assert result["items"][0]["is_policy"] is True              # 政策关键词命中
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_build.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'scripts.build'`

- [ ] **Step 3: 实现 build.py**

```python
# scripts/build.py
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_build.py -v`
Expected: 2 passed

- [ ] **Step 5: 全量测试**

Run: `pytest -v`
Expected: 全部 passed（models 4 + process 5 + fetchers 8 + build 2）

- [ ] **Step 6: Commit**

```bash
git add scripts/build.py tests/test_build.py
git commit -m "feat: 编排入口 build.py"
```

---

## Task 11: 真实抓取冒烟测试（手动，非单测）

**Files:** 无（运行验证）

- [ ] **Step 1: 实跑脚本抓真实数据**

Run: `python -m scripts.build`
Expected: stderr 打印每个源的条数（部分国内源/RSSHub 可能 0 或报错，属正常），最后 `[done] 写入 N 条`，且 `N > 0`

- [ ] **Step 2: 检查 data.json 结构**

Run: `python -c "import json; d=json.load(open('data.json',encoding='utf-8')); print('items', len(d['items'])); print('sample', d['items'][0]['title'], '|', d['items'][0]['source'])"`
Expected: items 数 > 0，打印一条样本标题与来源

- [ ] **Step 3: 提交首份 data.json**

```bash
git add data.json
git commit -m "chore: 首份 data.json 快照"
```

---

## Task 12: 前端页面 index.html + style.css + app.js

**Files:**
- Create: `index.html`
- Create: `style.css`
- Create: `app.js`

说明：纯静态，`app.js` fetch 同目录 `data.json` 渲染；5 个标签页（新闻/论文/开源/社区/政策），来源下拉筛选 + 关键词搜索；深色模式跟随系统。本任务无单测，靠 Step 4 浏览器验证。

- [ ] **Step 1: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI 资讯聚合</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <h1>AI 资讯聚合</h1>
    <p class="updated">上次更新：<span id="updated">加载中…</span></p>
  </header>

  <nav id="tabs" class="tabs">
    <button class="tab active" data-cat="all">全部</button>
    <button class="tab" data-cat="news">新闻</button>
    <button class="tab" data-cat="papers">论文</button>
    <button class="tab" data-cat="opensource">开源</button>
    <button class="tab" data-cat="community">社区</button>
    <button class="tab" data-cat="policy">政策</button>
  </nav>

  <div class="filters">
    <input id="search" type="search" placeholder="关键词搜索标题…">
    <select id="source-filter"><option value="">全部来源</option></select>
  </div>

  <main id="list" class="list"></main>
  <footer><p id="count"></p></footer>

  <script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: 创建 style.css**

```css
:root {
  --bg: #ffffff; --fg: #1a1a1a; --muted: #6b7280;
  --card: #f7f7f8; --border: #e5e7eb; --accent: #2563eb;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f1115; --fg: #e6e6e6; --muted: #9aa0a6;
    --card: #181b20; --border: #2a2e35; --accent: #60a5fa;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
  background: var(--bg); color: var(--fg); line-height: 1.5;
}
header { padding: 24px 16px 8px; max-width: 880px; margin: 0 auto; }
header h1 { margin: 0; font-size: 1.6rem; }
.updated { color: var(--muted); font-size: .85rem; margin: 4px 0 0; }
.tabs { display: flex; flex-wrap: wrap; gap: 8px; max-width: 880px;
        margin: 12px auto; padding: 0 16px; }
.tab { border: 1px solid var(--border); background: var(--card); color: var(--fg);
       padding: 6px 14px; border-radius: 999px; cursor: pointer; font-size: .9rem; }
.tab.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.filters { display: flex; gap: 8px; max-width: 880px; margin: 0 auto 12px;
           padding: 0 16px; flex-wrap: wrap; }
.filters input, .filters select {
  padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px;
  background: var(--bg); color: var(--fg); font-size: .9rem; }
.filters input { flex: 1; min-width: 180px; }
.list { max-width: 880px; margin: 0 auto; padding: 0 16px 40px; }
.card { background: var(--card); border: 1px solid var(--border);
        border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; }
.card a { color: var(--fg); text-decoration: none; font-weight: 600;
          font-size: 1.02rem; }
.card a:hover { color: var(--accent); }
.meta { color: var(--muted); font-size: .8rem; margin-top: 6px;
        display: flex; gap: 10px; flex-wrap: wrap; }
.badge { background: var(--accent); color: #fff; border-radius: 4px;
         padding: 1px 6px; font-size: .72rem; }
footer { text-align: center; color: var(--muted); font-size: .8rem;
         padding-bottom: 30px; }
```

- [ ] **Step 3: 创建 app.js**

```javascript
const CAT_LABEL = { news: "新闻", papers: "论文", opensource: "开源", community: "社区" };
let DATA = { items: [] };
let activeCat = "all";

function fmtTime(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return d.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit" });
}

function matchesCat(item, cat) {
  if (cat === "all") return true;
  if (cat === "policy") return item.is_policy === true;
  return item.category === cat;
}

function render() {
  const search = document.getElementById("search").value.trim().toLowerCase();
  const src = document.getElementById("source-filter").value;
  const list = document.getElementById("list");
  const items = DATA.items.filter(it =>
    matchesCat(it, activeCat) &&
    (!src || it.source === src) &&
    (!search || it.title.toLowerCase().includes(search))
  );
  list.innerHTML = items.map(it => `
    <div class="card">
      <a href="${it.url}" target="_blank" rel="noopener">${escapeHtml(it.title)}</a>
      <div class="meta">
        <span class="badge">${CAT_LABEL[it.category] || it.category}</span>
        <span>${escapeHtml(it.source)}</span>
        <span>${fmtTime(it.published)}</span>
        ${it.is_policy ? '<span class="badge">政策</span>' : ''}
      </div>
    </div>`).join("");
  document.getElementById("count").textContent = `共 ${items.length} 条`;
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function initSources() {
  const sel = document.getElementById("source-filter");
  const names = [...new Set(DATA.items.map(i => i.source))].sort();
  for (const n of names) {
    const o = document.createElement("option");
    o.value = n; o.textContent = n; sel.appendChild(o);
  }
}

function bind() {
  document.querySelectorAll(".tab").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeCat = btn.dataset.cat;
      render();
    });
  });
  document.getElementById("search").addEventListener("input", render);
  document.getElementById("source-filter").addEventListener("change", render);
}

async function main() {
  try {
    const res = await fetch("data.json?t=" + Date.now());
    DATA = await res.json();
  } catch (e) {
    document.getElementById("list").innerHTML =
      '<p style="color:var(--muted)">加载 data.json 失败。</p>';
    return;
  }
  document.getElementById("updated").textContent = fmtTime(DATA.generated_at);
  initSources();
  bind();
  render();
}

main();
```

- [ ] **Step 4: 本地浏览器验证**

Run: `python -m http.server 8000`
然后浏览器打开 `http://localhost:8000/` 验证：
- 顶部显示"上次更新"时间
- 点击各标签页能切换（新闻/论文/开源/社区/政策/全部）
- 搜索框输入关键词能实时过滤
- 来源下拉能筛选
- 卡片标题点击能在新标签打开原文
Expected: 全部正常；按 Ctrl+C 停止服务器

- [ ] **Step 5: Commit**

```bash
git add index.html style.css app.js
git commit -m "feat: 前端聚合页面（分类/搜索/来源筛选/深色模式）"
```

---

## Task 13: GitHub Actions 自动化 workflow

**Files:**
- Create: `.github/workflows/update.yml`

说明：每 6 小时定时 + 手动触发；跑 `scripts.build` 生成 `data.json`，提交回仓库，再部署 Pages。使用官方 Pages 部署 action，整站作为 artifact 上传。

- [ ] **Step 1: 创建 .github/workflows/update.yml**

```yaml
name: Update AI News

on:
  schedule:
    - cron: "0 */6 * * *"     # 每 6 小时（UTC）
  workflow_dispatch: {}        # 支持手动触发
  push:
    branches: [main]

permissions:
  contents: write              # 提交 data.json
  pages: write                 # 部署 Pages
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install deps
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest -q

      - name: Fetch news
        run: python -m scripts.build

      - name: Commit data.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data.json
          git commit -m "chore: 自动更新 data.json [skip ci]" || echo "无变化，跳过提交"
          git push || echo "推送失败或无变化"

      - name: Setup Pages
        uses: actions/configure-pages@v5

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: .

      - name: Deploy to Pages
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: 校验 YAML 语法**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/update.yml', encoding='utf-8')); print('workflow yaml ok')"`
Expected: 打印 `workflow yaml ok`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/update.yml
git commit -m "ci: GitHub Actions 每6小时抓取并部署 Pages"
```

---

## Task 14: README 与首次部署说明

**Files:**
- Create: `README.md`

- [ ] **Step 1: 创建 README.md**

```markdown
# AI 资讯聚合

每天自动聚合国内外 AI 新闻 / 论文 / 开源 / 社区 / 政策的个人静态站。
GitHub Actions 每 6 小时抓取一次并部署到 GitHub Pages。

**站点**：https://chen111111111112121.github.io/ai-news/

## 本地运行

```bash
pip install -r requirements.txt
python -m scripts.build      # 生成 data.json
python -m http.server 8000   # 打开 http://localhost:8000/
pytest -q                    # 跑测试
```

## 增删数据源

编辑 `sources.yaml` 的 `sources` 列表即可。支持的 `type`：
- `rss`：任何 RSS/Atom 源，需 `url`
- `hackernews`：Hacker News，需 `query`
- `github_trending`：GitHub Trending，可选 `url`
- `hf_papers`：Hugging Face 每日论文

改抓取频率：编辑 `.github/workflows/update.yml` 的 `cron`。

## 首次部署

1. 在 GitHub 新建仓库 `ai-news`（公开）。
2. 本地关联并推送：
   ```bash
   git remote add origin https://github.com/chen111111111112121/ai-news.git
   git branch -M main
   git push -u origin main
   ```
3. 仓库 Settings → Pages → Build and deployment → Source 选 **GitHub Actions**。
4. Actions 标签页手动触发一次 "Update AI News" 验证。
5. 等绿勾后访问站点 URL。

## 已知限制

- 国内源（机器之心/量子位）依赖公共 RSSHub，可能偶尔抓取失败，不影响其他源。
- 国内访问部分国外链接（Twitter/Reddit 等）可能需要代理，但标题聚合照常显示。
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README 与部署说明"
```

---

## Task 15: 推送上线（手动）

**Files:** 无

- [ ] **Step 1: 关联远程并推送**

```bash
git remote add origin https://github.com/chen111111111112121/ai-news.git
git branch -M main
git push -u origin main
```
Expected: 推送成功（首次会要求 GitHub 登录/令牌）

- [ ] **Step 2: 开启 Pages**

在 GitHub 仓库 Settings → Pages → Source 选 **GitHub Actions**。

- [ ] **Step 3: 手动触发并验证**

Actions 标签页 → "Update AI News" → Run workflow。
Expected: 任务全绿；访问 `https://chen111111111112121.github.io/ai-news/` 能看到资讯卡片。

---

## 完成标准

- [ ] `pytest -q` 全绿
- [ ] `python -m scripts.build` 能生成非空 `data.json`
- [ ] 本地 `http.server` 打开页面，5 个分类切换、搜索、来源筛选都正常
- [ ] GitHub Actions 手动触发成功并部署
- [ ] 线上站点 URL 可访问且显示资讯
- [ ] 等到下一个 6 小时整点，确认定时任务自动跑过一次
