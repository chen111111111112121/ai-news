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
- `github_trending`：GitHub Trending，可选 `url` 和 `filter_keywords`（仅纳入匹配这些 AI 关键词的仓库；为空则纳入全部热门仓库）
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

- 国内源（机器之心/量子位）依赖公共 RSSHub（rsshub.app），可能偶尔返回 403/超时，不影响其他源。
- 国内访问部分国外链接（Twitter/Reddit 等）可能需要代理，但标题聚合照常显示。
- Reddit 源在云端 IP 上可能被限流（429）；多数情况下仍能抓到部分子版块。
