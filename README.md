# GitHub Trending Loop

每日自动追踪 GitHub AI/LLM/Agent 热门项目，生成本地日报 + Web 仪表盘。

## 功能

### 排行（当日快照）

- 🏆 **综合榜 Top 10**: 按总星标排名，项目卡片含描述、语言、分类、标签、元信息
- 🚀 **涨势榜 Top 10**: 按今日新增 Star 排名，发现最新热点

### 趋势（跨天/跨周动量）

- 👀 **持续关注**: 连续上榜项目，按日增排序，识别持续趋势
- 📈 **本周增速**: 7 天 Star 增量排名，过滤"一日游"
- 📊 **类型分布**: 今日追踪项目的分类统计，含可视化进度条
- 🔤 **语言分布**: 按编程语言统计

### 仪表盘

- 🌙 深色主题，响应式布局
- 📅 日期切换：下拉选择历史日报
- 🌐 一键翻译：项目描述英译中
- 🔗 直达 GitHub 项目页

## 截图

### 排行

![排行 Tab](docs/screenshots/rank-tab.png)

### 趋势

![趋势 Tab](docs/screenshots/trend-tab.png)

## 项目结构

```
github-trending-loop/
├── src/                    # 源代码
│   ├── fetch_trending.py   # 数据抓取 + 分类 + 评分 + 日报生成
│   └── server.py           # Web 仪表盘 API 服务
├── scripts/                # 脚本
│   ├── run-loop.sh         # cron 入口
│   ├── start-server.sh     # 启动 Web 服务
│   └── setup-cron.sh       # 设置定时任务
├── dashboard/              # Web 前端
│   └── index.html          # 仪表盘页面（深色主题，照片卡片）
├── docs/                   # 文档
│   ├── LOOP.md             # 循环规格（12 步流水线）
│   ├── STATE.md            # 状态文件（去重索引 + 验证清单）
│   ├── CLAUDE.md           # 项目规则
│   └── knowledge-base.md   # 长期知识沉淀
├── skills/                 # Claude Code Skills
│   └── github-trending-scanner/
├── tests/                  # 测试
└── data/                   # 运行时数据（gitignore）
    ├── raw/                # 原始抓取 JSON
    ├── processed/          # 结构化数据 + 星标历史
    └── output/             # 日报 Markdown
```

## 快速开始

### 1. 手动运行一次

```bash
cd github-trending-loop
python3 src/fetch_trending.py
```

### 2. 启动 Web 仪表盘

```bash
bash scripts/start-server.sh
# 打开 http://localhost:8080
```

### 3. 设置每天自动运行

```bash
bash scripts/setup-cron.sh
# 每天 8:00 自动抓取
```

## 数据流

```
GitHub Trending (日增Star) ──┐
Topics: ai-agents (总Star)  ─┤
Topics: llm-agent            ─┼─→ 合并去重 → AI过滤 → 详情抓取 → 分类评分
Topics: agent                ─┤                                    ↓
项目详情页                    ─┘                              日报 + Web
```

## 技术栈

- **Python 3** 标准库（零外部依赖）
- **HTML/CSS/JS** 原生（零框架）
- **Linux cron** 定时调度

## License

MIT