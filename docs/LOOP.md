# GitHub Trending Loop — AI/LLM/Agent 每日趋势扫描

## 触发条件

| 方式 | 触发词 | 用途 |
|------|--------|------|
| 定时 | Linux cron: `0 9 * * *` | 每天 9:00 自动运行 |
| 手动 | "跑一圈" / "github loop" / "扫描趋势" | 手动触发 |

## 输入源（多源并行抓取，合并去重）

| 源 | 地址 | 方法 |
|----|------|------|
| GitHub Trending (daily) | `https://github.com/trending?since=daily` | WebFetch |
| GitHub Topics: ai-agents | `https://github.com/topics/ai-agents?o=desc&s=stars` | WebFetch |
| GitHub Topics: llm-agent | `https://github.com/topics/llm-agent?o=desc&s=stars` | WebFetch |
| GitHub Topics: agent | `https://github.com/topics/agent?o=desc&s=stars` | WebFetch |
| HackerNews | `https://news.ycombinator.com/` (AI/LLM 相关) | WebSearch |

## 数据持久化（三层归档）

每次运行产生的数据全部本地化存储，可审计、可回溯：

```
data/raw/YYYY-MM-DD/           # 原始抓取数据（不可变，审计用）
├── trending.json          # GitHub Trending 原始结果
├── topics-ai-agents.json  # Topics 页面结果
├── topics-llm-agent.json
├── topics-agent.json
├── hn-search.json         # HackerNews 搜索结果
└── readmes/               # 每个新项目的 README 原文
    ├── owner-repo.md
    └── ...

data/processed/YYYY-MM-DD/     # 结构化处理数据
├── candidates.json        # 过滤+分类+评分后的完整候选列表
└── top10.json             # Top 10 排行（含评分详情）

data/output/YYYY-MM-DD.md      # 最终日报（人类可读）
```

| 层级 | 内容 | 格式 | 保留策略 | 用途 |
|------|------|------|---------|------|
| `raw/` | 抓取原文 | JSON / Markdown | 永久 | 审计、回溯、调试、数据恢复 |
| `processed/` | 分类+评分+富化 | JSON | 永久 | 跨期趋势分析、统计 |
| `output/` | 日报 | Markdown | 永久 | 人类阅读、飞书发布 |

## 流水线（12 步）

### Phase 1: SCAN（扫描）
- 并行抓取 5 个源
- 合并去重（按 repo full_name 统一转小写）
- 目标: 30-50 个候选
- **💾 保存原始数据**: 每个源的结果写入 `raw/YYYY-MM-DD/`，JSON 格式

### Phase 2: FILTER（过滤）
只保留满足以下**任一**条件的项目：
- 描述含 AI/LLM/Agent/ML/深度学习/大模型/RAG/Transformer
- Topics 标签含 ai-artificial-intelligence/llm/agent/machine-learning
- 语言主要为 Python/TypeScript/Rust/Go（AI 生态主流）

排除：
- 教程合集、面试题、awesome-list、非英语项目
- 已归档/只读（`archived: true`）、超过 1 年未更新
- Fork 仓库（stars < 100 且标记为 fork）
- 纯前端 UI 库（除非与 AI 直接相关）

### Phase 3: DEDUP（去重）
- 读 `STATE.md`，repo 名统一转小写匹配
- 跳过 `archived` 状态的项目
- `seen` 状态的项目 → 仅更新 `last_seen`，不重新富化
- 新项目 → 进入 Phase 4
- 已有项目但别名不同 → 更新 STATE.md 别名列

### Phase 4: ENRICH（富化）
对每个新项目：
- Fetch README（GitHub raw）
- 提取: 一句话描述、核心功能、技术栈、星标信息
- 提取: 最近提交日期、issue 关闭率、LICENSE 类型
- 注意: 每个项目间隔 ≥ 2s，避免 GitHub API 限流
- **💾 保存 README 原文**: 写入 `raw/YYYY-MM-DD/readmes/owner-repo.md`

### Phase 5: CLASSIFY + SCORE（分类 + 质量评分）

**分类（8 种）**:
| 类型 | 判定 |
|------|------|
| Agent 框架 | 多 Agent 协作、自主 Agent、Agent 编排 |
| 模型 | 预训练模型、微调框架、模型部署 |
| RAG/检索 | 向量数据库、RAG 引擎、文档理解 |
| 推理/部署 | vLLM 类、推理优化、服务化 |
| 开发工具 | AI 编程助手、代码生成、Prompt 工程 |
| 多模态 | 视觉+语言、语音、视频生成 |
| 评估/安全 | Benchmark、红队测试、对齐 |
| 学术/教育 | 教程、论文复现、课程 |

**标签（5 种）**:
| 标签 | 判定 |
|------|------|
| 🔥 爆火 | 当日新增 > 500 stars |
| 📈 上升 | 周增速 > 20% |
| 🆕 新兴 | 创建 < 3 个月 |
| 🏛️ 成熟 | stars > 50k 且持续维护 |
| 💎 小众精品 | stars < 5k 但技术独特 |

**质量评分（0-100）**:
| 维度 | 权重 | 数据来源 | 高分条件 | 低分条件 |
|------|------|---------|---------|---------|
| 活跃度 | 0.25 | 最近提交日期 | 7 天内 | > 6 个月 |
| 社区健康度 | 0.25 | issue 关闭率、PR 响应 | 关闭率 > 70% | 大量 open issues |
| 文档质量 | 0.15 | README 长度、LICENSE | 完整文档 + 示例 | 一句话描述 |
| 星标增速 | 0.20 | 当日/周增长 | 日增 > 500 | 停滞 |
| 团队背景 | 0.15 | 组织/个人、协作者数 | 知名组织、多协作者 | 个人仓库无协作者 |

扣分项:
- 无 LICENSE: -10
- 只有中文 README 无英文: -5
- 发现刷星迹象（一夜暴涨后长期停滞）: -20

### Phase 6: SUMMARIZE（总结）
每个项目输出：
- 1 段中文描述（50-100 字）
- 3 个关键特性（bullet points）
- 一句话判断: "为什么值得关注"（20 字以内）
- 质量评分（0-100）

### Phase 7: RANK（排序）
综合评分 = 质量评分 × 0.4 + 星标增速 × 0.3 + 新颖度 × 0.3
- 输出 Top 10 正式排行
- 额外 5 个 "值得关注"（Honorable Mentions）
- **💾 保存处理数据**: candidates.json + top10.json 写入 `processed/YYYY-MM-DD/`

### Phase 8: OUTPUT（输出）

**输出 1 — 飞书文档**（L2 阶段启用）:
- 使用 `feishu-doc-creator` skill 创建日报文档
- 标题: `GitHub AI 趋势日报 — YYYY-MM-DD`
- 文件夹: `NpbsfCzQCla14KdRqVUcHWC4nvc`

**输出 2 — 飞书消息推送**（L2 阶段启用）:
- 发送 Top 3 摘要到指定群聊/话题
- 附带文档链接

**输出 3 — 本地归档**:
- 保存到 `output/YYYY-MM-DD.md`

### Phase 9: ARCHIVE（归档）
- 更新 `STATE.md`: 所有新项目标记为 `seen`，记录日期和分类
- 更新 `STATE.md` 的每日验证清单
- 更新 `references/knowledge-base.md`:
  - 新项目追加到对应分类
  - 已有项目如有分类变化，更新
  - 统计本周趋势关键词

### Phase 10: VERIFY（验证）
每天运行后自动检查以下指标，发现异常立即告警:

| 检查项 | 预期 | 异常处理 |
|--------|------|---------|
| 扫描候选数 | ≥ 30 | 检查抓取源是否可访问 |
| AI 相关数 | ≥ 10 | 检查过滤规则是否过严 |
| 新发现数 | ≥ 3 | 连续 3 天 < 3 → 检查去重/抓取源 |
| 日报非空 | ✅ | 流水线可能断裂，检查日志 |
| STATE.md 已更新 | ✅ | 归档步骤可能失败 |
| raw/ 数据已保存 | ✅ | 检查磁盘空间 |
| 无重复项目 | ✅ | 检查去重逻辑 |

### Phase 11: CLEANUP（清理）
- 删除超过 30 天的 raw 目录（README 原文保留，仅删抓取 JSON）
- processed/ 和 output/ 永久保留
- 检查磁盘空间: 单次运行约 1-2MB，30 天约 30-60MB

## 安全边界

- 只读操作: 不修改任何外部仓库
- 请求间隔: GitHub 源 ≥ 2s，其他源 ≥ 1s
- 不认证: 使用 GitHub 公开页面，不走 API（避免限流）
- 失败重试: 单个源失败不阻塞其他源，最多重试 1 次

## 飞书配置

| 配置项 | 值 |
|--------|-----|
| 文档文件夹 | `NpbsfCzQCla14KdRqVUcHWC4nvc`（内核技术部小管家） |
| 群聊推送 | 待配置（用户提供 chat_id） |

## 渐进式上线

| 阶段 | 持续 | 内容 |
|------|------|------|
| L1 Report | Week 1-2 | 扫描 → 生成本地日报，不发布飞书 |
| L2 Publish | Week 3-4 | 日报自动发布飞书文档 + 消息推送 |
| L3 Enhanced | Week 5+ | 周报汇总、趋势洞察、自动标签"值得关注" |