# 知识库 — AI/LLM/Agent 项目长期追踪

> 本文件沉淀对 GitHub AI 项目的长期观察，包括趋势变化、项目兴衰、分类体系演进。
> 每次 Loop 运行后自动更新。

## 趋势关键词（本周 2026-W28）

- **Agent 框架持续主导**: 57 个 AI 项目中 53% 为 Agent 框架，生态持续火热
- **Claude 生态活跃**: system_prompts_leaks、claude-video、agent-skills、ai-job-search 等 Claude 相关项目霸榜
- **办公自动化涌现**: OfficeCLI、meetily 等 AI 办公工具快速增长
- **沙箱/安全执行**: CubeSandbox 等 AI 安全执行环境受关注
- **多模态扩展**: TTS、视频理解等多模态 AI 项目持续增长

## 项目分类体系

### Agent 框架
<!-- 多 Agent 协作、自主 Agent、Agent 编排 -->

**本周热点**:
- `MadsLorentzen/ai-job-search` (🔥 爆火, +2514 stars/day): 基于 Claude Code 的 AI 求职框架
- `Zackriya-Solutions/meetily` (🔥 爆火, +1777 stars/day): 隐私优先的 AI 会议助手
- `affaan-m/ECC` (227k stars): Agent harness 性能优化系统
- `lsdefine/GenericAgent`: 自进化 Agent，从 3.3K 行种子代码自举

### 模型训练/微调
<!-- 预训练、LoRA/QLoRA、RLHF -->

- `DietrichGebert/ponytail` (77k stars): 让 AI Agent 像最懒的高级开发一样思考
- `unslothai/unsloth`: 模型微调框架
- `hiyouga/LlamaFactory`: LLM 微调工厂

### RAG/检索增强
<!-- 向量数据库、RAG 引擎、文档解析 -->

- `thedotmack/claude-mem` (86k stars): 跨会话持久化上下文
- `infiniflow/ragflow`: RAG 引擎

### 推理/部署
<!-- vLLM 类、推理优化、模型服务化 -->

- `TencentCloud/CubeSandbox` (🔥 爆火): 即时并发安全 AI Agent 沙箱

### 开发工具
<!-- AI 编程助手、Prompt 工程、代码生成 -->

- `asgeirtj/system_prompts_leaks` (🔥 爆火, +1691 stars/day): 提取的 Claude/OpenAI 系统提示词
- `addyosmani/agent-skills` (72k stars, 🔥 爆火): AI 编程 Agent 的生产级工程技能
- `nexu-io/open-design` (76k stars): 开源 Claude Design 替代方案
- `bradautomates/claude-video` (🔥 爆火): 让 Claude 能看视频
- `steipete/CodexBar` (📈 上升): Codex/Claude Code 使用统计

### 多模态
<!-- 视觉+语言、语音、视频生成 -->

- `kyutai-labs/pocket-tts` (🔥 爆火): 适合 CPU 运行的 TTS
- `bytedance/UI-TARS-desktop`: 桌面 GUI Agent

### 评估/安全
<!-- Benchmark、红队测试、对齐研究 -->

- `THUDM/AgentBench`: Agent 评测基准

## 长期追踪项目

| 项目 | 首次收录 | 峰值 stars | 当前状态 | 备注 |
|------|---------|-----------|---------|------|
| affaan-m/ECC | 2026-07-07 | 227,075 | 持续活跃 | Agent harness 标杆 |
| langchain-ai/langchain | 2026-07-07 | ~200k | 成熟稳定 | Agent 框架鼻祖 |
| microsoft/autogen | 2026-07-07 | ~45k | 成熟稳定 | 微软多 Agent 框架 |
| addyosmani/agent-skills | 2026-07-07 | 72,184 | 🔥 爆火 | 日增 1317 stars |

## 已消亡/过气项目

<!-- 曾经热门但已停止维护或不再相关 -->
| 项目 | 活跃期 | 衰退原因 |
|------|--------|---------|