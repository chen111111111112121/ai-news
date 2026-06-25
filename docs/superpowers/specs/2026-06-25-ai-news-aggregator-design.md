# AI 资讯聚合站 — 设计文档

**日期**：2026-06-25
**状态**：已确认，待实现

## 1. 目标

每天自动聚合国内外最前沿的 AI 信息和资讯，汇总到一个个人静态网站，方便每天浏览。

## 2. 范围与约束

- **使用对象**：仅个人使用（无用户系统、无注册登录、无多用户考虑）
- **内容加工**：不做 AI 翻译/摘要/总结，只聚合原始标题 + 链接（零 API 费用）
- **托管**：GitHub Pages（静态托管）
- **更新方式**：GitHub Actions 定时任务，默认每 6 小时一次 + 支持手动触发
- **成本**：完全免费（公开仓库的 Actions + Pages）

## 3. 内容分类（5 类）

1. 新闻资讯
2. 论文 / 技术突破
3. 开源项目 / 工具
4. 社区讨论
5. 国内外 AI 政策

## 4. 架构

```
GitHub 仓库
├─ 抓取脚本 (Python)        ← 去各家 RSS/API 拉数据
├─ 数据文件 data.json       ← 脚本生成，存所有资讯条目
├─ 网页 index.html          ← 纯静态，读 data.json 渲染
└─ GitHub Actions 定时任务   ← 每6小时跑脚本→生成data.json→部署Pages
```

**数据流**：Actions 定时触发 → Python 脚本抓取所有源 → 去重/排序/截断 → 写入 `data.json` → 部署到 GitHub Pages → 浏览器打开网页读取 `data.json` 渲染。

**技术选型**：
- 抓取：Python + feedparser（处理 RSS 最成熟稳定）；HTML 解析用 requests + 标准库/轻量解析
- 前端：纯 HTML + 原生 JS + CSS，无构建步骤、无框架
- 自动化：GitHub Actions（cron + workflow_dispatch）

**关键好处**：Actions runner 在国外，抓 arXiv / GitHub / Hacker News / Reddit 不受国内网络限制。

## 5. 数据源清单

所有源集中在 `sources.yaml`，增删改一行即可。默认清单（优先选有稳定 RSS/API、无需密钥的源）：

### ① 新闻资讯
- 国外（原生 RSS，稳定）：TechCrunch AI、The Verge AI、VentureBeat AI、MIT Tech Review、OpenAI 博客、Google DeepMind 博客
- 国内：IT之家（原生 RSS，稳定）；机器之心、量子位（经 RSSHub，尽力而为）

### ② 论文 / 技术突破
- arXiv：cs.AI / cs.CL / cs.LG / cs.CV（官方 RSS）
- Hugging Face Papers（JSON 接口，每日热门论文）

### ③ 开源项目 / 工具
- GitHub Trending（脚本解析 trending 页，按 AI 关键词过滤）
- Papers with Code 最新（可选）

### ④ 社区讨论
- Hacker News（Algolia 接口按 AI/LLM 关键词搜，JSON）
- Reddit：r/MachineLearning、r/LocalLLaMA、r/artificial（.rss）

### ⑤ 国内外 AI 政策
- 无现成 RSS。做法：从所有抓到的条目中，按政策关键词（regulation / policy / act / 监管 / 政策 / 法案 / AI 安全 等）自动筛出「政策」板块。

### 已知限制
1. 国内源（机器之心 / 量子位）依赖公共 RSSHub，可能偶尔抓取失败——国内站普遍缺 RSS 的客观限制，不影响其他源。
2. 用户在国内点开 Twitter / Reddit / 部分国外链接可能需要代理，但标题聚合照常显示。

## 6. 抓取脚本行为

- **去重**：按链接/标题去重（同一新闻被多源收录时）
- **排序**：按发布时间倒序
- **截断**：每个源最多取最近 N 条（默认 30）
- **时间窗**：默认只保留最近 7 天的内容
- **容错**：单个源失败（超时/格式坏）→ 跳过 + 记日志，不影响其他源，不让整个任务崩溃
- **数据字段**：标题、链接、来源、分类、发布时间、（可选）摘要前 200 字

## 7. 前端网页

- **顶部**：标题 + 上次更新时间 + 5 个分类标签页切换
- **主体**：卡片列表，每张卡片显示 标题（点击跳原文）、来源、时间
- **筛选**：按来源筛选 + 关键词搜索（纯前端，秒响应）
- **样式**：简洁响应式，手机/电脑适配，支持深色模式
- 纯静态，无登录，打开即用

## 8. 仓库结构

```
ai-news/
├─ .github/workflows/update.yml   # 每6小时定时 + 手动触发
├─ scripts/fetch.py               # 抓取脚本
├─ sources.yaml                   # 数据源配置
├─ data.json                      # 脚本生成的数据
├─ index.html                     # 网页
├─ style.css                      # 样式
├─ app.js                         # 前端逻辑
└─ README.md
```

## 9. 自动化

- GitHub Actions：`schedule` (cron, 每 6 小时) + `workflow_dispatch`（手动触发）
- 流程：checkout → 装 Python 依赖 → 跑 `fetch.py` → 提交 `data.json` → 部署 Pages
- 频率可改：调整 cron 一行即可（每天 1 次 / 每 3 小时等）

## 10. 未来可选扩展（当前不做，YAGNI）

- AI 翻译/摘要/每日简报（需接入 Claude API）
- 自托管 RSSHub 提升国内源稳定性
- 邮件/微信每日推送
- 收藏/已读标记
