# GitHub Trending Loop — 项目规则

> 本项目是 Loop Engineering 实践项目，用于每日追踪 GitHub AI/LLM/Agent 趋势。

## 核心规则

1. **读 LOOP.md 优先**: 任何操作前，先读 LOOP.md 了解当前阶段（L1/L2/L3）和 12 步流水线规格
2. **所有数据来自实际抓取**: 禁止捏造星标数、项目描述、趋势数据
3. **所有数据本地化存储**: 每次运行的原始数据、处理数据、日报全部保存到本地
4. **更新 STATE.md**: 每次运行后必须更新状态文件、运行日志、验证清单
5. **L1 阶段不发布**: 当前阶段仅本地归档，不发布飞书文档/消息

## 文件结构

```
src/fetch_trending.py             # 数据抓取 + 分类 + 评分 + 日报生成
src/server.py                     # Web 仪表盘 API 服务
scripts/run-loop.sh               # cron 触发脚本
scripts/start-server.sh           # 启动 Web 仪表盘
scripts/setup-cron.sh             # 设置定时任务
dashboard/index.html              # Web 仪表盘前端
docs/LOOP.md                      # 循环规格 — 12 步流水线
docs/STATE.md                     # 状态文件 — 去重索引 + 验证清单 + 运行日志
docs/CLAUDE.md                    # 本文件
docs/knowledge-base.md            # 长期知识沉淀
skills/github-trending-scanner/   # 核心扫描 skill
data/raw/YYYY-MM-DD/              # 原始抓取数据（不可变，审计用）
data/processed/YYYY-MM-DD/        # 结构化处理数据（分类+评分）
data/output/YYYY-MM-DD.md         # 最终日报（人类可读）
```

## 数据持久化规则

| 层级 | 目录 | 保留策略 | 不可变 |
|------|------|---------|--------|
| 原始数据 | `data/raw/YYYY-MM-DD/` | 30 天自动清理 | ✅ |
| 处理数据 | `data/processed/YYYY-MM-DD/` | 永久保留 | - |
| 日报 | `data/output/YYYY-MM-DD.md` | 永久保留 | - |

## 手动触发

在 Claude Code 中说:
- "跑一圈" / "github loop" / "扫描趋势"

## 当前阶段

**L1 Report-only** — 仅扫描并生成本地日报，不发布飞书。