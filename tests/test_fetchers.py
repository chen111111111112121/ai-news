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
    assert first.url == "https://example.com/openai"
    assert first.source == "DemoSource"
    assert first.category == "news"
    assert first.published.year == 2026
    assert first.published.tzinfo is not None


def test_parse_rss_skips_entries_without_date():
    no_date = SAMPLE_RSS.replace("<pubDate>Wed, 24 Jun 2026 10:00:00 GMT</pubDate>", "")
    items = parse_rss(no_date, source="S", category="news")
    assert len(items) == 1
    assert items[0].title == "Second story"


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
    assert items[1].url == "https://news.ycombinator.com/item?id=222"
    assert items[0].published.tzinfo is not None


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
