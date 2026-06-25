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

# Mirrors the real GitHub Trending HTML structure: h2.h3.lh-condensed with a nested
# span.text-normal for the owner and the repo name as a trailing text node, plus
# p.col-9.color-fg-muted for the description.
SAMPLE_TRENDING = """
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a data-hydro-click="{}" href="/acme/llm-runner" data-view-component="true" class="Link">
      <svg aria-hidden="true"></svg>
      <span data-view-component="true" class="text-normal">
        acme /
      </span>
      llm-runner</a>
  </h2>
  <p class="col-9 color-fg-muted my-1 tmp-pr-4">Fast local LLM inference</p>
</article>
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a data-hydro-click="{}" href="/foo/web-css" data-view-component="true" class="Link">
      <svg aria-hidden="true"></svg>
      <span data-view-component="true" class="text-normal">
        foo /
      </span>
      web-css</a>
  </h2>
  <p class="col-9 color-fg-muted my-1 tmp-pr-4">A CSS framework</p>
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


# --- Fix 1: trending desc alignment ---

def test_parse_github_trending_desc_alignment_ignores_noise_outside_articles():
    html = """
    <p class="col-9 color-fg-muted my-1 tmp-pr-4">UNRELATED SIDEBAR TEXT</p>
    <article class="Box-row">
      <h2 class="h3 lh-condensed">
        <a data-hydro-click="{}" href="/acme/ai-kit" data-view-component="true" class="Link">
          <svg aria-hidden="true"></svg>
          <span data-view-component="true" class="text-normal">
            acme /
          </span>
          ai-kit</a>
      </h2>
      <p class="col-9 color-fg-muted my-1 tmp-pr-4">An AI toolkit</p>
    </article>
    """
    items = parse_github_trending(html, "GitHub Trending", "opensource",
                                  keywords=["ai"], now_ts=1782000000)
    assert len(items) == 1
    assert items[0].title == "acme / ai-kit"
    assert items[0].summary == "An AI toolkit"   # correct desc, not the sidebar noise


# --- Fix 3: real GitHub HTML structure ---

# Trimmed snippets taken from the actual https://github.com/trending page (2026-06-25).
# The h2 uses class="h3 lh-condensed", the anchor carries all data-hydro attributes,
# the owner lives in a nested span.text-normal, and the description class includes
# extra Primer utility classes beyond "col-9".
REAL_TRENDING_SNIPPET = """
<article class="Box-row">
  <div class="float-right d-flex"></div>
  <h2 class="h3 lh-condensed">
    <a data-hydro-click="{&quot;event_type&quot;:&quot;explore.click&quot;}" data-hydro-click-hmac="abc123" href="/interviewstreet/hiring-agent" data-view-component="true" class="Link"><svg aria-hidden="true" data-component="Octicon" height="16" viewBox="0 0 16 16" version="1.1" width="16" data-view-component="true" class="octicon octicon-repo mr-1 color-fg-muted">
    <path d="M2 2.5z"></path>
</svg>

      <span data-view-component="true" class="text-normal">
        interviewstreet /
</span>
      hiring-agent</a>  </h2>

    <p class="col-9 color-fg-muted my-1 tmp-pr-4">
      AI agent to evaluate and score resumes.
    </p>
</article>
<article class="Box-row">
  <div class="float-right d-flex"></div>
  <h2 class="h3 lh-condensed">
    <a data-hydro-click="{&quot;event_type&quot;:&quot;explore.click&quot;}" data-hydro-click-hmac="def456" href="/andreknieriem/headunit-revived" data-view-component="true" class="Link"><svg aria-hidden="true" data-component="Octicon" height="16" viewBox="0 0 16 16" version="1.1" width="16" data-view-component="true" class="octicon octicon-repo mr-1 color-fg-muted">
    <path d="M2 2.5z"></path>
</svg>

      <span data-view-component="true" class="text-normal">
        andreknieriem /
</span>
      headunit-revived</a>  </h2>

    <p class="col-9 color-fg-muted my-1 tmp-pr-4">
      Headunit App for displaying Android Auto
    </p>
</article>
"""


def test_parse_github_trending_real_html_structure():
    """Verify parser handles the actual GitHub Trending markup (nested span, extra classes)."""
    # With AI keyword: only hiring-agent should match
    items = parse_github_trending(
        REAL_TRENDING_SNIPPET, source="GitHub Trending", category="opensource",
        keywords=["ai", "agent", "llm"], now_ts=1782000000,
    )
    assert len(items) == 1
    assert items[0].title == "interviewstreet / hiring-agent"
    assert items[0].url == "https://github.com/interviewstreet/hiring-agent"
    assert "AI agent" in items[0].summary

    # headunit-revived has no AI keywords → filtered out
    titles = [it.title for it in items]
    assert not any("headunit" in t for t in titles)

    # With empty keywords: both repos returned (no filter)
    all_items = parse_github_trending(
        REAL_TRENDING_SNIPPET, source="GitHub Trending", category="opensource",
        keywords=[], now_ts=1782000000,
    )
    assert len(all_items) == 2


# --- Fix 2: per-row try/except ---

def test_parse_hf_papers_skips_malformed_row():
    data = [
        {"paper": {"id": "1", "title": "Good"}, "publishedAt": "2026-06-24T00:00:00Z"},
        {"paper": {"id": "2", "title": "Bad date"}, "publishedAt": "not-a-date"},
        {"paper": {"id": "3", "title": "Also good"}, "publishedAt": "2026-06-23T00:00:00Z"},
    ]
    items = parse_hf_papers(data, "HF", "papers")
    titles = [i.title for i in items]
    assert "Good" in titles and "Also good" in titles
    assert "Bad date" not in titles


def test_parse_hackernews_skips_hit_with_no_url_and_no_objectid():
    data = {"hits": [
        {"title": "No link", "url": None, "objectID": None, "created_at_i": 1782000000},
        {"title": "Has link", "url": "https://e.com/x", "objectID": "9", "created_at_i": 1782000001},
    ]}
    items = parse_hackernews(data, "HN", "community")
    assert len(items) == 1
    assert items[0].title == "Has link"
