---
name: github-trending-scanner
description: 每日 GitHub AI/LLM/Agent 趋势扫描。从 GitHub Trending、Topics、HackerNews 抓取，过滤、分类、总结，输出日报到飞书和本地。触发词：跑一圈、github loop、扫描趋势。
---

# GitHub Trending Scanner

## 触发
- 定时: Linux cron 每天 9:00
- 手动: "跑一圈" / "github loop" / "扫描趋势"

## 前置条件

运行前必须加载:
- 本 skill（github-trending-scanner）
- `feishu-doc-creator`（发布日报文档）
- 飞书 MCP 工具（消息推送）

## 执行流程

### Step 1: 读状态文件

读 `STATE.md`，获取已见项目列表和上次运行统计。

### Step 2: 并行扫描

同时抓取以下源（每个源独立，失败不阻塞其他）:

**GitHub Trending**:
```
WebFetch: https://github.com/trending?since=daily
提取: repo name, description, stars, language
```

**GitHub Topics**:
```
WebFetch: https://github.com/topics/ai-agents?o=desc&s=stars
WebFetch: https://github.com/topics/llm-agent?o=desc&s=stars
提取: repo name, stars, description
```

**HackerNews**:
```
WebSearch: "site:news.ycombinator.com AI agent LLM open source github"
提取: 被讨论的 GitHub 项目链接
```

### Step 3: 合并去重

- 按 repo full_name 合并
- 同一项目保留星标数最高的记录
- 与 STATE.md 中的已见项目交叉比对

### Step 4: AI 过滤

逐个项目判断:
- 是否 AI/LLM/Agent 相关？
- 是否排除类型（教程/面试题/awesome-list）？
- 是否纯前端/非英语？
- 去重: 是否已在 STATE.md 中？
- 标记每个项目的分类和标签

### Step 5: 富化新项目

仅对 STATE.md 中不存在的项目:
- 逐个 WebFetch 其 GitHub 页面，提取 README
- 生成: 一句话描述 + 3 个关键特性 + 为什么值得关注
- 每个项目间隔 ≥ 2s

### Step 6: 排序

综合评分: 星标增速(40%) + 主题相关性(30%) + 新颖度(30%)
- 输出 Top 10
- 额外 5 个 Honorable Mentions

### Step 7: 生成日报

输出格式:

```markdown
# GitHub AI/LLM/Agent 趋势日报 — YYYY-MM-DD

## 📊 概览
- 今日扫描: N 个候选 → M 个 AI 相关 → K 个新项目
- 趋势关键词: ...

## 🔥 Top 10

### 1. [owner/repo](url) ⭐stars (今日+Δ)
**类型**: xxx | **标签**: xxx
**一句话**: ...
**关键特性**:
- ...
- ...
- ...
**为什么值得关注**: ...

## 📋 Honorable Mentions
...

## 📈 本周趋势
...
```

### Step 8: 发布

**飞书文档**:
- 标题: `GitHub AI 趋势日报 — YYYY-MM-DD`
- 文件夹: `NpbsfCzQCla14KdRqVUcHWC4nvc`
- 使用 feishu-doc-creator skill

**飞书消息**（L2 阶段启用）:
- 发送 Top 3 摘要
- 附带文档链接
- 工具: feishu-im MCP

**本地归档**:
- 保存到 `output/YYYY-MM-DD.md`

### Step 9: 更新状态

更新 `STATE.md`:
- 新增项目: 追加到已见索引，状态 `seen`
- 已有项目: 更新 `last_seen`
- 更新统计: 扫描次数、累计发现、最后运行时间
- 追加运行日志

更新 `references/knowledge-base.md`:
- 新项目追加到对应分类
- 更新趋势关键词

## 注意事项

- 不修改外部仓库，只读
- GitHub 请求间隔 ≥ 2s
- 单个源失败不阻塞，跳过继续
- 日报中所有数据（星标、描述）必须来自实际抓取，禁止捏造
- 首次运行: 没有 STATE.md 的已见项目，Phase 3 跳过，全部视为新项目
- 告警: 如果连续 3 天无新项目发现，检查抓取源是否失效