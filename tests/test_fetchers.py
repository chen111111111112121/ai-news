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
