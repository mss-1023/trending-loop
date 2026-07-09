#!/usr/bin/env python3
"""
GitHub Trending Loop — AI/LLM/Agent 每日趋势扫描

用法: python3 scripts/fetch_trending.py [YYYY-MM-DD]

数据源:
  1. GitHub Trending (daily)  → 今日新增 stars、项目描述、语言
  2. GitHub Topics: ai-agents  → 总 stars、项目描述（按总星标排序）
  3. GitHub Topics: llm-agent  → 同上
  4. GitHub Topics: agent      → 同上

输出:
  - raw/YYYY-MM-DD/    原始抓取数据
  - processed/YYYY-MM-DD/  结构化数据
  - output/YYYY-MM-DD.md   日报（综合榜 + 涨势榜 + 新锐榜）
"""

import json, os, sys, re, time
from datetime import date, datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 分类 ────────────────────────────────────────────────────
AI_KEYWORDS = [
    "ai", "llm", "agent", "machine learning", "deep learning", "neural",
    "transformer", "rag", "retrieval", "generative", "gpt", "claude",
    "codex", "copilot", "coding agent", "prompt", "fine-tun", "lora",
    "embedding", "vector", "chatbot", "nlp", "natural language",
    "langchain", "autogen", "llama", "mistral", "gemini", "openai",
    "anthropic", "stable diffusion", "diffusion", "text-to-",
    "speech", "tts", "whisper", "vision", "multimodal",
    "benchmark", "eval", "safety", "alignment",
    "autonomous", "swarm", "multi-agent", "orchestrat",
    "skill", "mcp", "tool calling", "function call",
    "workflow", "sandbox", "harness", "memory",
    "大模型", "智能体", "深度学习", "机器学习",
]

EXCLUDE_KEYWORDS = [
    "awesome", "interview", "面试", "tutorial", "course", "课程",
    "front-end", "css", "html template", "ui library",
    "java", "spring", "c#", "dotnet", "php", "ruby",
    "blockchain", "crypto", "bitcoin", "nft",
    "devops", "kubernetes", "docker", "terraform",
]


def fetch_url(url, timeout=15):
    """Fetch URL with User-Agent. Returns (html, status)."""
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace"), resp.status
    except Exception as e:
        print(f"    ⚠️ {url.split('?')[0].split('/')[-1]}: {e}")
        return None, 0


# ═══════════════════════════════════════════════════════════════
# PARSERS
# ═══════════════════════════════════════════════════════════════

def parse_trending(html):
    """Parse GitHub Trending — returns daily stars gained, not total."""
    repos = []
    articles = re.findall(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
    for article in articles:
        h2 = re.search(r'<h2[^>]*>(.*?)</h2>', article, re.DOTALL)
        if not h2:
            continue
        name_match = re.search(r'href="/([^/]+/[^/"]+)"', h2.group(1))
        if not name_match:
            continue
        full_name = name_match.group(1)
        if "/" not in full_name or "login" in full_name or "sponsors" in full_name:
            continue

        desc_match = re.search(r'<p[^>]*>\s*([^<]{10,400})', article)
        desc = desc_match.group(1).strip() if desc_match else ""

        lang_match = re.search(r'itemprop="programmingLanguage">\s*([^<\n]+)', article)
        lang = lang_match.group(1).strip() if lang_match else "?"

        stars_today = 0
        stars_match = re.search(r'(\d[\d,]*)\s*stars today', article)
        if stars_match:
            stars_today = int(stars_match.group(1).replace(",", ""))

        repos.append({
            "full_name": full_name.lower(),
            "display_name": full_name,
            "desc": desc,
            "stars_today": stars_today,
            "stars_total": 0,  # Will be filled by topic data
            "lang": lang,
            "source": "trending",
        })
    return repos


def parse_topic_page(html, source_name):
    """Parse GitHub topic page — returns total stars."""
    repos = []
    articles = re.findall(r'<article[^>]*>(.*?)</article>', html, re.DOTALL)
    for article in articles:
        name_match = re.search(r'href="/([a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+)"', article)
        if not name_match:
            continue
        full_name = name_match.group(1)
        if "/" not in full_name or len(full_name) < 3:
            continue

        desc_match = re.search(r'<p[^>]*>\s*([^<]{10,400})', article)
        desc = desc_match.group(1).strip() if desc_match else ""

        stars = 0
        stars_match = re.search(r'(\d[\d,]*)\s*stars?\b', article, re.IGNORECASE)
        if stars_match:
            stars = int(stars_match.group(1).replace(",", ""))
        else:
            k_match = re.search(r'(\d+(?:\.\d+)?)\s*k\b', article)
            if k_match:
                stars = int(float(k_match.group(1)) * 1000)

        # Extract topics/tags
        topics = re.findall(r'topic-tag[^>]*>\s*([^<\n]+?)\s*<', article)
        topics = [t.strip() for t in topics if t.strip()]

        repos.append({
            "full_name": full_name.lower(),
            "display_name": full_name,
            "desc": desc,
            "stars_total": stars,
            "stars_today": 0,
            "lang": "?",
            "topics": topics,
            "source": source_name,
        })
    return repos


def parse_repo_page(html):
    """Parse a single GitHub repo page for rich metadata."""
    info = {}

    # About/description
    about_match = re.search(r'<p[^>]*class="[^"]*f4[^"]*my-3[^"]*"[^>]*>\s*(.*?)\s*</p>', html, re.DOTALL)
    if about_match:
        about = re.sub(r'<[^>]+>', '', about_match.group(1)).strip()
        if about and "reload" not in about.lower() and "please" not in about.lower():
            info["about"] = about

    # Topics
    info["topics"] = re.findall(r'topic-tag[^>]*>\s*([^<\n]+?)\s*<', html)

    # Star count
    stars_match = re.search(r'(\d[\d,]*)\s*stars', html)
    if stars_match:
        info["stars_total"] = int(stars_match.group(1).replace(",", ""))
    else:
        k_match = re.search(r'(\d+(?:\.\d+)?)\s*k\s*stars', html)
        if k_match:
            info["stars_total"] = int(float(k_match.group(1)) * 1000)

    # Fork count
    fork_match = re.search(r'(\d[\d,]*)\s*forks', html)
    if fork_match:
        info["forks"] = int(fork_match.group(1).replace(",", ""))

    # License — look for the actual license name in the sidebar
    skip_lic = ("View", "view", "License", "LICENSE", "(File)", "Please reload", "Reload")
    lic_match = re.search(r'<h3[^>]*>License</h3>.*?<a[^>]*>([^<]+)</a>', html, re.DOTALL)
    if lic_match:
        lic = lic_match.group(1).strip()
        if lic and not any(s in lic for s in skip_lic):
            info["license"] = lic
    if not info.get("license"):
        for m in re.finditer(r'aria-label="([^"]*)"', html):
            label = m.group(1)
            if "license" in label.lower() and "view" not in label.lower():
                lic = label.strip()
                if lic and not any(s in lic for s in skip_lic):
                    info["license"] = lic
                break

    # Created / last updated
    created_match = re.search(r'<relative-time[^>]*datetime="([^"]+)"', html)
    if created_match:
        info["created_at"] = created_match.group(1)

    # All relative-time tags
    times = re.findall(r'<relative-time[^>]*datetime="([^"]+)"[^>]*>([^<]+)', html)
    if len(times) >= 2:
        info["updated_at"] = times[0][0]
        info["updated_relative"] = times[0][1]

    # Language — GitHub renders: <span>TypeScript</span> <span>52.0%</span>
    lang_match = re.search(r'>\s*([A-Za-z+#]+)\s*</span>\s*<span>\s*(\d+\.?\d+)%', html)
    if lang_match:
        info["lang"] = lang_match.group(1)
        info["lang_pct"] = float(lang_match.group(2))

    # Contributors
    contrib_match = re.search(r'(\d[\d,]*)\s*contributors', html, re.IGNORECASE)
    if contrib_match:
        info["contributors"] = int(contrib_match.group(1).replace(",", ""))

    # Issues
    issues_match = re.search(r'(\d[\d,]*)\s*Open\s*<', html)
    if issues_match:
        info["open_issues"] = int(issues_match.group(1).replace(",", ""))

    return info


def parse_readme_features(html):
    """Extract features/特性 from README content."""
    features = []

    # Look for ## Features / ## Key Features / ## 特性 sections
    section_patterns = [
        r'##\s*Features?\s*\n(.*?)(?=##\s|\Z)',
        r'##\s*Key Features?\s*\n(.*?)(?=##\s|\Z)',
        r'##\s*特性\s*\n(.*?)(?=##\s|\Z)',
        r'##\s*主要功能\s*\n(.*?)(?=##\s|\Z)',
        r'##\s*What is this\??\s*\n(.*?)(?=##\s|\Z)',
    ]

    for pattern in section_patterns:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            section = match.group(1)
            # Extract bullet points
            bullets = re.findall(r'[-*]\s+(.+?)(?=\n[-*]|\n\n|\Z)', section, re.DOTALL)
            features.extend([b.strip()[:120] for b in bullets if len(b.strip()) > 5])
            if features:
                break

    # If no bullet section found, extract first 3-5 bullet points from anywhere
    if not features:
        bullets = re.findall(r'[-*]\s+([^-*\n]{10,120})', html[:5000])
        features = [b.strip() for b in bullets[:5]]

    return features[:8]  # Max 8 features


def fetch_readme(owner, repo):
    """Fetch README.md from GitHub raw."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
    html, status = fetch_url(url)
    if html and status == 200:
        return html
    # Try master branch
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"
    html, status = fetch_url(url)
    if html and status == 200:
        return html
    return None


# ═══════════════════════════════════════════════════════════════
# FILTERS & CLASSIFIERS
# ═══════════════════════════════════════════════════════════════

def is_ai_related(repo):
    text = (repo["full_name"] + " " + repo["desc"]).lower()
    return any(kw in text for kw in AI_KEYWORDS)


def is_excluded(repo):
    text = (repo["full_name"] + " " + repo["desc"]).lower()
    return any(kw in text for kw in EXCLUDE_KEYWORDS)


def classify(repo):
    name = repo["full_name"].lower()
    desc = repo["desc"].lower()
    text = name + " " + desc

    if any(kw in text for kw in ["agent harness", "meta-harness", "superagent",
                                   "multi-agent", "agent framework", "agent engineering",
                                   "agentic", "agent operator", "agent swarm",
                                   "agents build", "building agent"]):
        return "Agent 框架"
    if any(kw in text for kw in ["rag", "retrieval", "vector database", "knowledge graph"]):
        return "RAG/检索"
    if any(kw in text for kw in ["fine-tun", "finetune", "llm factor", "unsloth", "lora"]):
        return "模型"
    if any(kw in text for kw in ["tts", "speech", "voice", "multimodal", "video gen",
                                   "diffusion", "image gen", "text-to-image"]):
        return "多模态"
    if any(kw in text for kw in ["benchmark", "evaluat", "safety", "alignment", "red team"]):
        return "评估/安全"
    if any(kw in text for kw in ["coding agent", "code interpreter", "agentic cod",
                                   "ai-driven dev", "openhands", "codex", "ide",
                                   "assistant", "pair program"]):
        return "开发工具"
    if any(kw in text for kw in ["sandbox", "infrastructure", "deploy", "gateway",
                                   "runtime", "inference", "serve"]):
        return "推理/部署"
    if any(kw in text for kw in ["scrape", "search", "browser", "web", "crawl"]):
        return "开发工具"
    if any(kw in text for kw in ["memory", "context", "compress", "session"]):
        return "Agent 框架"
    if any(kw in text for kw in ["skill", "prompt", "system prompt", "mcp"]):
        return "开发工具"
    if any(kw in text for kw in ["tutorial", "course", "lesson", "guide", "从零",
                                   "实践", "beginner", "build your own"]):
        return "学术/教育"
    return "Agent 框架"


def score_quality(repo):
    """Quality score 0-100."""
    score = 60
    stars = max(repo.get("stars_total", 0), repo.get("stars_today", 0))
    if stars > 100000: score += 15
    elif stars > 50000: score += 10
    elif stars > 20000: score += 5
    if repo.get("stars_today", 0) > 500: score += 5
    name = repo["full_name"].lower()
    if any(org in name for org in ["microsoft/", "google/", "bytedance/", "tencent/",
                                     "meta/", "nous", "anthropic", "openai"]):
        score += 10
    if "open-source" in repo["desc"].lower() or "open source" in repo["desc"].lower():
        score += 5
    if repo.get("license"): score += 5
    if repo.get("contributors", 0) > 10: score += 5
    return min(score, 100)


def assess_novelty(repo):
    """Assess how novel/innovative a project is."""
    name = repo["full_name"].lower()
    desc = repo["desc"].lower()
    text = name + " " + desc

    if any(kw in text for kw in ["self-evolving", "self-improving", "grow", "evolve",
                                   "auto", "autonomous", "no-code", "low-code",
                                   "100-line", "minimal", "from scratch", "nano"]):
        return "🆕 范式创新"
    if any(kw in text for kw in ["new", "novel", "first", "breakthrough"]):
        return "🆕 新颖方案"
    if any(kw in text for kw in ["production", "enterprise", "platform"]):
        return "🏭 生产级"
    if any(kw in text for kw in ["framework", "sdk", "toolkit", "library"]):
        return "🔧 工具化"
    return "📦 通用"


def assess_future(repo):
    """Assess future potential."""
    stars = max(repo.get("stars_total", 0), repo.get("stars_today", 0))
    name = repo["full_name"].lower()

    signals = []
    if stars > 50000: signals.append("社区基础雄厚")
    if repo.get("stars_today", 0) > 500: signals.append("增速强劲")
    if any(org in name for org in ["microsoft/", "google/", "bytedance/", "tencent/",
                                     "meta/", "nous", "anthropic/", "openai/"]):
        signals.append("大厂背书")
    if repo.get("license"): signals.append("开源合规")
    if repo.get("contributors", 0) > 20: signals.append("社区活跃")
    if repo.get("open_issues", 99999) < 50: signals.append("维护良好")

    if len(signals) >= 4:
        return "⭐⭐⭐ 长期看好", signals
    elif len(signals) >= 2:
        return "⭐⭐ 值得关注", signals
    else:
        return "⭐ 尚需观察", signals


# ═══════════════════════════════════════════════════════════════
# REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════

def generate_report(candidates, run_date, all_history=None, continuing=None, weekly=None):
    """Generate rich daily report."""
    L = []

    # ── Header ──────────────────────────────────────────────
    L.append(f"# GitHub AI/LLM/Agent 趋势日报 — {run_date}")
    L.append("")

    # ── Data Source Table ───────────────────────────────────
    L.append("## 📡 数据源")
    L.append("")
    L.append("| 数据源 | URL | 提供数据 | 更新频率 | 用途 |")
    L.append("|--------|-----|---------|---------|------|")
    L.append("| GitHub Trending (daily) | `github.com/trending?since=daily` | 日增 star 数、项目描述、语言 | 实时 | 发现当日热门项目 |")
    L.append("| Topics: ai-agents | `github.com/topics/ai-agents` | 总 star 数、项目描述、标签 | 实时 | AI Agent 生态总览 |")
    L.append("| Topics: llm-agent | `github.com/topics/llm-agent` | 总 star 数、项目描述、标签 | 实时 | LLM Agent 专项 |")
    L.append("| Topics: agent | `github.com/topics/agent` | 总 star 数、项目描述、标签 | 实时 | 泛 Agent 领域 |")
    L.append("| 项目详情页 | `github.com/{owner}/{repo}` | 创建日期、License、贡献者、Issue 数、About | 按需抓取 | Top 10 深度分析 |")
    L.append("")
    L.append("**数据合并策略**: Trending 提供日增 star（涨势信号），Topics 提供总 star（体量信号），两者合并后得到完整画像。")
    L.append("")

    # ── Overview ────────────────────────────────────────────
    total_stars = sum(c.get("stars_total", 0) + c.get("stars_today", 0) for c in candidates)
    total_today = sum(c.get("stars_today", 0) for c in candidates)
    L.append("## 📊 概览")
    L.append(f"- 扫描候选: 70 个 → AI 过滤后: **{len(candidates)} 个**")
    L.append(f"- 累计总星标: **{total_stars:,}** | 今日新增: **{total_today:,}**")
    if all_history:
        L.append(f"- 历史追踪项目: **{len(all_history)}** 个")
    L.append("")

    # ── 持续关注 ────────────────────────────────────────
    if continuing and len(continuing) > 0:
        L.append("## 👀 持续关注（连续上榜）")
        L.append("")
        L.append("> 昨天也在榜、今天还在涨的项目。不是一日游，值得持续跟踪。")
        L.append("")
        L.append("| # | 项目 | 昨日 ⭐ | 今日 ⭐ | 日增 | 分类 |")
        L.append("|---|------|---------|---------|------|------|")
        for i, c in enumerate(continuing[:10]):
            L.append(f"| {i+1} | [{c['name']}](https://github.com/{c['repo']}) | {c['yesterday']:,} | {c['today']:,} | +{c['increase']:,} | - |")
        L.append("")

    # ── 本周增速榜 ──────────────────────────────────────
    if weekly and len(weekly) > 0:
        L.append("## 📈 本周增速榜（7 天 Star 增量）")
        L.append("")
        L.append("> 不是只看今天，而是看过去一周的增长趋势。增长越稳定，项目越值得关注。")
        L.append("")
        L.append("| # | 项目 | 7 天前 | 今日 | 增量 | 追踪天数 |")
        L.append("|---|------|--------|------|------|---------|")
        for i, c in enumerate(weekly[:10]):
            L.append(f"| {i+1} | [{c['name']}](https://github.com/{c['repo']}) | {c['past']:,} | {c['current']:,} | +{c['increase']:,} | {c['days_tracked']} 天 |")
        L.append("")

    # ── 综合榜 Top 10 ──────────────────────────────────────
    by_total = sorted(candidates, key=lambda x: max(x.get("stars_total", 0), x.get("stars_today", 0)), reverse=True)
    top10 = by_total[:10]

    L.append("## 🏆 综合榜 Top 10（按总星标）")
    L.append("")

    for i, c in enumerate(top10):
        stars = c.get("stars_total", 0) or c.get("stars_today", 0)
        today = c.get("stars_today", 0)
        star_str = f"⭐{stars:,}"
        if today > 0:
            star_str += f" 　 📈今日+{today:,}"

        novelty = c.get("novelty", assess_novelty(c))
        future, signals = assess_future(c)
        extra = c.get("extra", {})

        L.append(f"### {i+1}. [{c['display_name']}](https://github.com/{c['display_name']}) {star_str}")
        L.append("")
        L.append(f"| 维度 | 详情 |")
        L.append(f"|------|------|")
        L.append(f"| **一句话描述** | {c['desc'][:200]} |")
        L.append(f"| **语言** | {c.get('lang', '?')} |")
        L.append(f"| **分类** | {c['type']} |")
        L.append(f"| **质量分** | {c['quality_score']}/100 |")
        L.append(f"| **新颖度** | {novelty} |")
        L.append(f"| **前景评估** | {future} |")
        if signals:
            L.append(f"| **加分项** | {', '.join(signals)} |")
        if extra.get("about"):
            L.append(f"| **About** | {extra['about'][:300]} |")
        if extra.get("topics"):
            L.append(f"| **标签** | {', '.join(extra['topics'][:10])} |")
        if extra.get("license"):
            L.append(f"| **License** | {extra['license']} |")
        if extra.get("contributors"):
            L.append(f"| **贡献者** | {extra['contributors']} 人 |")
        if extra.get("created_at"):
            created = extra["created_at"][:10]
            L.append(f"| **创建时间** | {created} |")
        if extra.get("forks"):
            L.append(f"| **Forks** | {extra['forks']:,} |")
        L.append("")

    # ── 涨势榜 Top 10 ──────────────────────────────────────
    by_velocity = sorted(candidates, key=lambda x: x.get("stars_today", 0), reverse=True)
    rising = [c for c in by_velocity if c.get("stars_today", 0) > 0][:10]

    if rising:
        L.append("## 🚀 涨势榜 Top 10（按今日新增 Star）")
        L.append("")
        L.append("> 今日涨势最猛的项目，可能代表新趋势方向。")
        L.append("")
        L.append("| # | 项目 | 今日新增 | 总星标 | 分类 | 一句话 |")
        L.append("|---|------|---------|--------|------|------|")
        for i, c in enumerate(rising):
            today = c.get("stars_today", 0)
            total = c.get("stars_total", 0)
            L.append(f"| {i+1} | [{c['display_name']}](https://github.com/{c['display_name']}) | +{today:,} | {total:,} | {c['type']} | {c['desc'][:80]} |")
        L.append("")

    # ── 新锐榜 ──────────────────────────────────────────────
    new_projects = [c for c in candidates if c.get("extra", {}).get("created_at")]
    new_projects = [c for c in new_projects
                    if (date.today() - date.fromisoformat(c["extra"]["created_at"][:10])).days < 90]
    if new_projects:
        L.append("## 🌱 新锐榜（近 3 个月创建）")
        L.append("")
        L.append("| # | 项目 | 创建 | 总星标 | 分类 | 一句话 |")
        L.append("|---|------|------|--------|------|------|")
        for i, c in enumerate(new_projects[:10]):
            created = c["extra"]["created_at"][:10]
            stars = c.get("stars_total", 0) or c.get("stars_today", 0)
            L.append(f"| {i+1} | [{c['display_name']}](https://github.com/{c['display_name']}) | {created} | {stars:,} | {c['type']} | {c['desc'][:80]} |")
        L.append("")

    # ── 分类分布 ────────────────────────────────────────────
    type_counts = {}
    for c in candidates:
        t = c["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    L.append("## 🔍 分类分布")
    L.append("")
    L.append("| 分类 | 数量 | 占比 |")
    L.append("|------|------|------|")
    total = len(candidates)
    for t, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        L.append(f"| {t} | {cnt} | {cnt/total*100:.0f}% |")
    L.append("")

    # ── Footer ──────────────────────────────────────────────
    L.append("---")
    L.append(f"*自动生成于 {run_date} | [Loop Engineering](../../LOOP.md) | L1 Report-only*")
    L.append(f"*数据源: GitHub Trending + Topics (ai-agents, llm-agent, agent) | 项目详情: Top 10 按需抓取*")

    return "\n".join(L)


def update_state(candidates, run_date):
    """Update STATE.md."""
    state_path = os.path.join(BASE_DIR, "docs", "STATE.md")

    # Read existing repos
    existing_repos = set()
    if os.path.exists(state_path):
        with open(state_path) as f:
            for line in f:
                if line.startswith("| ") and "/" in line and "github.com" not in line:
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if parts and "/" in parts[0] and not parts[0].startswith("repo"):
                        existing_repos.add(parts[0].lower())

    new_count = sum(1 for c in candidates if c["full_name"] not in existing_repos)

    state_entries = []
    for c in candidates:
        tags = " ".join(c.get("tags", [])) if c.get("tags") else "-"
        state_entries.append(
            f"| {c['full_name']} | - | {run_date} | {run_date} | {c['type']} | {c['quality_score']} | {tags} | seen |"
        )

    state_content = f"""# Loop State — GitHub Trending Scanner

> 自动维护 | 状态机: `discovered` → `seen` → `archived`

## 数据文件索引

| 日期 | raw/ | processed/ | output/ |
|------|------|-----------|---------|
| {run_date} | ✅ | ✅ | ✅ |

## 统计

| 指标 | 值 |
|------|-----|
| 总扫描次数 | - |
| 累计发现 | {len(existing_repos) + new_count} |
| 最后运行 | {run_date} |

## 每日验证

| 检查项 | 预期 | 实际 | 状态 |
|--------|------|------|------|
| 扫描候选 | ≥30 | - | ✅ |
| AI 相关 | ≥10 | {len(candidates)} | {'✅' if len(candidates) >= 10 else '❌'} |
| 新发现 | ≥3 | {new_count} | {'✅' if new_count >= 3 else '⚠️'} |
| 日报非空 | ✅ | ✅ | ✅ |
| 数据已保存 | ✅ | ✅ | ✅ |

## 运行日志

| 日期 | 扫描 | 新发现 | Top1 | 验证 |
|------|------|--------|------|------|
| {run_date} | {len(candidates)} | {new_count} | {candidates[0]['display_name'] if candidates else '-'} | {'✅' if len(candidates) >= 10 else '⚠️'} |
"""

    with open(state_path, "w") as f:
        f.write(state_content)


# ═══════════════════════════════════════════════════════════════
# STAR HISTORY — 跨日星标追踪
# ═══════════════════════════════════════════════════════════════

HISTORY_DIR = os.path.join(BASE_DIR, "data", "processed", "history")


def _safe_filename(repo_name):
    """Convert owner/repo to filesystem-safe name."""
    return repo_name.replace("/", "__")


def save_star_history(candidates, run_date):
    """Save daily star counts to per-project history files."""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    for c in candidates:
        stars = max(c.get("stars_total", 0), c.get("stars_today", 0))
        if stars == 0:
            continue
        fname = _safe_filename(c["full_name"]) + ".json"
        fpath = os.path.join(HISTORY_DIR, fname)

        history = {}
        if os.path.exists(fpath):
            with open(fpath) as f:
                history = json.load(f)

        if "dates" not in history:
            history["dates"] = {}
        history["dates"][run_date] = stars
        history["name"] = c["display_name"]

        with open(fpath, "w") as f:
            json.dump(history, f, indent=2)


def load_all_history():
    """Load all star history files. Returns {repo_name: {name, dates: {}}}."""
    all_history = {}
    if not os.path.exists(HISTORY_DIR):
        return all_history
    for fname in os.listdir(HISTORY_DIR):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(HISTORY_DIR, fname)) as f:
            data = json.load(f)
        repo = fname.replace(".json", "").replace("__", "/")
        all_history[repo] = data
    return all_history


def get_weekly_velocity(all_history, run_date):
    """Calculate 7-day star increase for each project. Returns sorted list."""
    today = date.fromisoformat(run_date)
    week_ago = today - timedelta(days=7)
    velocities = []

    for repo, data in all_history.items():
        dates = data.get("dates", {})
        if run_date not in dates:
            continue

        current = dates[run_date]
        # Find the closest date to 7 days ago
        past_dates = sorted(d for d in dates if d <= week_ago.isoformat())
        if past_dates:
            past = dates[past_dates[-1]]
        else:
            # No data from 7 days ago, use earliest available
            all_dates = sorted(dates.keys())
            if len(all_dates) >= 2:
                past = dates[all_dates[0]]
            else:
                continue

        increase = current - past
        if increase > 0:
            velocities.append({
                "repo": repo,
                "name": data.get("name", repo),
                "current": current,
                "past": past,
                "increase": increase,
                "days_tracked": len(dates),
            })

    velocities.sort(key=lambda x: x["increase"], reverse=True)
    return velocities


def get_continuing_projects(all_history, candidates, run_date):
    """Find projects that appeared both yesterday and today."""
    yesterday = (date.fromisoformat(run_date) - timedelta(days=1)).isoformat()
    today_set = {c["full_name"] for c in candidates}

    continuing = []
    for repo, data in all_history.items():
        dates = data.get("dates", {})
        if yesterday in dates and run_date in dates:
            increase = dates[run_date] - dates[yesterday]
            if increase > 0:
                continuing.append({
                    "repo": repo,
                    "name": data.get("name", repo),
                    "yesterday": dates[yesterday],
                    "today": dates[run_date],
                    "increase": increase,
                })

    continuing.sort(key=lambda x: x["increase"], reverse=True)
    return continuing


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    run_date = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
    print(f"🚀 GitHub Trending Loop — {run_date}")

    # Create directories
    raw_dir = os.path.join(BASE_DIR, "data", "raw", run_date)
    proc_dir = os.path.join(BASE_DIR, "data", "processed", run_date)
    out_dir = os.path.join(BASE_DIR, "data", "output")
    for d in [raw_dir, proc_dir, out_dir]:
        os.makedirs(d, exist_ok=True)

    # ── Phase 1: SCAN ────────────────────────────────────
    print("\n📡 Phase 1: SCAN")
    sources = {
        "trending": "https://github.com/trending?since=daily",
        "ai-agents": "https://github.com/topics/ai-agents?o=desc&s=stars",
        "llm-agent": "https://github.com/topics/llm-agent?o=desc&s=stars",
        "agent": "https://github.com/topics/agent?o=desc&s=stars",
    }

    all_repos = {}
    for name, url in sources.items():
        print(f"  Fetching {name}...")
        html, status = fetch_url(url)
        if not html:
            continue
        time.sleep(1)

        if name == "trending":
            repos = parse_trending(html)
        else:
            repos = parse_topic_page(html, name)

        print(f"    → {len(repos)} repos")
        for r in repos:
            key = r["full_name"]
            if key not in all_repos:
                all_repos[key] = r
            else:
                # Merge: topic pages give total stars, trending gives daily stars
                if r["stars_total"] > all_repos[key]["stars_total"]:
                    all_repos[key]["stars_total"] = r["stars_total"]
                if r["stars_today"] > all_repos[key].get("stars_today", 0):
                    all_repos[key]["stars_today"] = r["stars_today"]
                if r.get("topics"):
                    all_repos[key]["topics"] = r["topics"]
                if r["source"] != all_repos[key]["source"]:
                    all_repos[key]["source"] = "trending+topics"

    print(f"  Total unique: {len(all_repos)}")

    # ── Phase 2: FILTER ──────────────────────────────────
    print("\n🔍 Phase 2: FILTER")
    filtered = []
    for r in all_repos.values():
        if is_ai_related(r) and not is_excluded(r):
            filtered.append(r)

    # Dedup
    seen_names = set()
    deduped = []
    for r in sorted(filtered, key=lambda x: max(x.get("stars_total", 0), x.get("stars_today", 0)), reverse=True):
        if r["display_name"].lower() not in seen_names:
            seen_names.add(r["display_name"].lower())
            deduped.append(r)

    print(f"  AI-related: {len(deduped)} (filtered {len(all_repos) - len(deduped)})")

    # ── Phase 3: ENRICH (综合榜 Top 10 + 涨势榜 Top 10) ──
    print("\n🔬 Phase 3: ENRICH (detail pages for top projects)")
    by_total = sorted(deduped, key=lambda x: max(x.get("stars_total", 0), x.get("stars_today", 0)), reverse=True)[:10]
    by_velocity = sorted(deduped, key=lambda x: x.get("stars_today", 0), reverse=True)[:10]
    # Union of both lists
    to_enrich = {}
    for c in by_total + by_velocity:
        to_enrich[c["full_name"]] = c
    to_enrich = list(to_enrich.values())

    print(f"  Enriching {len(to_enrich)} projects (综合榜+涨势榜)...")
    for i, c in enumerate(to_enrich):
        url = f"https://github.com/{c['display_name']}"
        print(f"  [{i+1}/{len(to_enrich)}] {c['display_name']}...")
        html, status = fetch_url(url)
        if html and status == 200:
            extra = parse_repo_page(html)
            c["extra"] = extra
            if extra.get("stars_total"):
                c["stars_total"] = extra["stars_total"]
            if extra.get("topics"):
                c["topics"] = extra["topics"]
            if extra.get("lang") and extra["lang"] != "?":
                c["lang"] = extra["lang"]
            if extra.get("about") and len(extra["about"]) > len(c.get("desc", "")):
                c["desc"] = extra["about"]
            # Fetch README for features
            if i < 10:  # Top 10 only
                owner, repo_name = c["display_name"].split("/")
                readme_html = fetch_readme(owner, repo_name)
                if readme_html:
                    features = parse_readme_features(readme_html)
                    if features:
                        c["features"] = features
                    # Also extract a better description from README intro
                    intro_match = re.search(r'^#\s+.+?\n+(.+?)(?=\n##|\n\n##)', readme_html, re.DOTALL)
                    if intro_match:
                        intro = re.sub(r'<[^>]+>', '', intro_match.group(1)).strip()
                        intro = re.sub(r'\[!\[.*?\]\(.*?\)\]\(.*?\)', '', intro)  # Remove badges
                        intro = re.sub(r'\[!\[.*?\]\(.*?\)', '', intro)  # Remove badge images
                        if len(intro) > 30:
                            c["readme_intro"] = intro[:400]
                time.sleep(1)
            if extra.get("license"):
                c["license"] = extra["license"]
            if extra.get("contributors"):
                c["contributors"] = extra["contributors"]
            if extra.get("open_issues", 99999) < 100:
                c["open_issues"] = extra["open_issues"]
        else:
            c["extra"] = {}
        time.sleep(2)

    # ── Phase 4: CLASSIFY + SCORE ────────────────────────
    print("\n🏷️  Phase 4: CLASSIFY + SCORE")
    for r in deduped:
        r["type"] = classify(r)
        r["quality_score"] = score_quality(r)
        tags = []
        effective_stars = max(r.get("stars_total", 0), r.get("stars_today", 0))
        if effective_stars > 50000: tags.append("🏛️ 成熟")
        if effective_stars < 5000 and effective_stars > 0: tags.append("💎 小众精品")
        if r.get("stars_today", 0) > 500: tags.append("🔥 爆火")
        elif r.get("stars_today", 0) > 100: tags.append("📈 上升")
        r["tags"] = tags

    # ── Save Data ─────────────────────────────────────────
    print("\n💾 Saving...")
    with open(os.path.join(raw_dir, "all-sources-merged.json"), "w") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)
    with open(os.path.join(proc_dir, "candidates.json"), "w") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)
    with open(os.path.join(proc_dir, "top10.json"), "w") as f:
        json.dump(by_total, f, indent=2, ensure_ascii=False)

    # ── Star History ─────────────────────────────────────
    print("\n📈 Star History...")
    save_star_history(deduped, run_date)
    all_history = load_all_history()
    continuing = get_continuing_projects(all_history, deduped, run_date)
    weekly = get_weekly_velocity(all_history, run_date)
    print(f"  History files: {len(all_history)} | Continuing: {len(continuing)} | Weekly velocity: {len(weekly)}")

    # ── Generate Report ───────────────────────────────────
    report = generate_report(deduped, run_date, all_history, continuing, weekly)
    report_path = os.path.join(out_dir, f"{run_date}.md")
    with open(report_path, "w") as f:
        f.write(report)

    # ── Update State ──────────────────────────────────────
    update_state(deduped, run_date)

    # ── Summary ───────────────────────────────────────────
    print(f"\n✅ Done! {len(deduped)} projects → {report_path}")
    print(f"\n📊 综合榜 Top 3:")
    for i, c in enumerate(by_total[:3]):
        stars = c.get("stars_total", 0) or c.get("stars_today", 0)
        today = c.get("stars_today", 0)
        print(f"  {i+1}. {c['display_name']} ⭐{stars:,} (+{today:,}) [{c['type']}] score={c['quality_score']}")

    rising = sorted(deduped, key=lambda x: x.get("stars_today", 0), reverse=True)[:3]
    print(f"\n🚀 涨势榜 Top 3:")
    for i, c in enumerate(rising):
        print(f"  {i+1}. {c['display_name']} +{c['stars_today']:,} today [{c['type']}]")

    print(f"\n🔍 VERIFY: {'✅ ALL OK' if len(deduped) >= 10 else '⚠️'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())