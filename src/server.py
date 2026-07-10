#!/usr/bin/env python3
"""
GitHub Trending Loop — 本地 Web 仪表盘

用法: python3 scripts/server.py [--port 8080]
然后浏览器打开 http://localhost:8080

零依赖，仅用 Python 标准库。
"""

import json, os, sys, re
from datetime import date, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")


class APIHandler(SimpleHTTPRequestHandler):
    """Serve dashboard HTML + JSON API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API routes
        if path == "/api/dates":
            self._json_response(self._get_available_dates())
        elif path == "/api/report":
            params = parse_qs(parsed.query)
            report_date = params.get("date", [date.today().isoformat()])[0]
            self._json_response(self._get_report(report_date))
        elif path == "/api/history":
            params = parse_qs(parsed.query)
            repo = params.get("repo", [""])[0]
            self._json_response(self._get_history(repo))
        elif path == "/api/overview":
            self._json_response(self._get_overview())
        elif path == "/" or path == "":
            # Serve index.html
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def _json_response(self, data):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_available_dates(self):
        out_dir = os.path.join(BASE_DIR, "data", "output")
        dates = []
        if os.path.exists(out_dir):
            for f in sorted(os.listdir(out_dir), reverse=True):
                if f.endswith(".md"):
                    dates.append(f.replace(".md", ""))
        return {"dates": dates, "latest": dates[0] if dates else None}

    def _get_report(self, report_date):
        proc_dir = os.path.join(BASE_DIR, "data", "processed", report_date)
        if not os.path.exists(proc_dir):
            return {"error": f"No data for {report_date}"}

        candidates_path = os.path.join(proc_dir, "candidates.json")
        top10_path = os.path.join(proc_dir, "top10.json")

        candidates = []
        if os.path.exists(candidates_path):
            with open(candidates_path) as f:
                candidates = json.load(f)

        # Enrich descriptions
        self._enrich_descriptions(candidates)

        # Build comprehensive report
        return {
            "date": report_date,
            "total": len(candidates),
            "candidates": candidates,
            "comprehensive": sorted(candidates, key=lambda x: max(x.get("stars_total", 0), x.get("stars_today", 0)), reverse=True)[:10],
            "rising": self._enrich_rising(candidates),
            "type_distribution": self._get_type_distribution(candidates),
            "lang_distribution": self._get_lang_distribution(candidates),
            "total_stars": sum(max(c.get("stars_total", 0), c.get("stars_today", 0)) for c in candidates),
            "total_today": sum(c.get("stars_today", 0) for c in candidates),
            "continuing": self._get_continuing(candidates, report_date),
            "weekly": self._get_weekly(report_date, candidates),
        }

    def _get_type_distribution(self, candidates):
        dist = {}
        for c in candidates:
            t = c.get("type", "Other")
            dist[t] = dist.get(t, 0) + 1
        return sorted(dist.items(), key=lambda x: -x[1])

    def _get_lang_distribution(self, candidates):
        dist = {}
        unknown = 0
        for c in candidates:
            lang = c.get("lang", "")
            if not lang or lang == "?":
                unknown += 1
            else:
                dist[lang] = dist.get(lang, 0) + 1
        result = sorted(dist.items(), key=lambda x: -x[1])
        if unknown > 0:
            result.append(("未知", unknown))
        return result

    def _enrich_descriptions(self, candidates):
        """Build richer descriptions from available data sources."""
        import re
        for c in candidates:
            desc = c.get("desc", "")
            about = (c.get("extra") or {}).get("about", "")
            readme = c.get("readme_intro", "")
            features = c.get("features", [])

            parts = []

            # Primary: GitHub description
            if desc and len(desc) > 10:
                parts.append(desc.strip())

            # Secondary: about (if different from desc)
            if about and about.strip() != desc.strip() and len(about) > 10:
                parts.append(about.strip())

            # Tertiary: clean README intro (first paragraph)
            if readme:
                # Strip markdown artifacts
                clean = re.sub(r'!\[.*?\]\(.*?\)', '', readme)  # images
                clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)  # links
                clean = re.sub(r'<[^>]+>', '', clean)  # HTML tags
                clean = re.sub(r'#{1,6}\s*', '', clean)  # headings
                clean = re.sub(r'\n{3,}', '\n\n', clean)  # excessive newlines
                clean = clean.strip()
                if clean and len(clean) > 20:
                    parts.append(clean)

            # Quaternary: features (meaningful bullets)
            for f in features[:3]:
                f_clean = re.sub(r'<[^>]+>', '', f)  # strip HTML tags
                f_clean = re.sub(r'[#*>\-\[\]()"]', '', f_clean).strip()
                if f_clean and len(f_clean) > 15 and len(f_clean) < 200:
                    parts.append(f_clean)

            # Build final description
            if parts:
                combined = " | ".join(parts)
                c["desc"] = combined[:600]
                c["readme_intro"] = combined[:600]

    def _get_desc(self, candidates, repo):
        for c in candidates:
            if c.get("full_name", c.get("repo", "")) == repo:
                return (c.get("readme_intro") or c.get("desc") or "")[:120]
        return ""

    def _enrich_rising(self, candidates):
        rising = sorted(candidates, key=lambda x: x.get("stars_today", 0), reverse=True)[:10]
        history_dir = os.path.join(BASE_DIR, "data", "processed", "history")
        for item in rising:
            if item.get("stars_total", 0) > 0:
                continue
            repo = item.get("full_name", item.get("repo", ""))
            fname = repo.replace("/", "__") + ".json"
            fpath = os.path.join(history_dir, fname)
            if os.path.exists(fpath):
                with open(fpath) as f:
                    data = json.load(f)
                total = sum(data.get("dates", {}).values())
                if total > 0:
                    item["stars_total"] = total
        return rising

    def _get_continuing(self, candidates, report_date):
        try:
            yesterday = (date.fromisoformat(report_date) - timedelta(days=1)).isoformat()
            history_dir = os.path.join(BASE_DIR, "data", "processed", "history")
            if not os.path.exists(history_dir):
                return []
            continuing = []
            for fname in os.listdir(history_dir):
                if not fname.endswith(".json"):
                    continue
                with open(os.path.join(history_dir, fname)) as f:
                    data = json.load(f)
                dates = data.get("dates", {})
                repo = fname.replace(".json", "").replace("__", "/")
                if yesterday in dates and report_date in dates:
                    increase = dates[report_date] - dates[yesterday]
                    if increase > 0:
                        continuing.append({
                            "repo": repo,
                            "name": data.get("name", repo),
                            "yesterday": dates[yesterday],
                            "today": dates[report_date],
                            "increase": increase,
                            "desc": self._get_desc(candidates, repo),
                        })
            continuing.sort(key=lambda x: x["increase"], reverse=True)
            return continuing[:10]
        except Exception:
            return []

    def _get_weekly(self, report_date, candidates):
        try:
            today = date.fromisoformat(report_date)
            week_ago = today - timedelta(days=7)
            history_dir = os.path.join(BASE_DIR, "data", "processed", "history")
            if not os.path.exists(history_dir):
                return []
            velocities = []
            for fname in os.listdir(history_dir):
                if not fname.endswith(".json"):
                    continue
                with open(os.path.join(history_dir, fname)) as f:
                    data = json.load(f)
                dates = data.get("dates", {})
                repo = fname.replace(".json", "").replace("__", "/")
                if report_date not in dates:
                    continue
                current = dates[report_date]
                past_dates = sorted(d for d in dates if d <= week_ago.isoformat())
                if past_dates:
                    past = dates[past_dates[-1]]
                else:
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
                        "desc": self._get_desc(candidates, repo),
                    })
            velocities.sort(key=lambda x: x["increase"], reverse=True)
            return velocities[:10]
        except Exception:
            return []

    def _get_history(self, repo):
        fname = repo.replace("/", "__") + ".json"
        fpath = os.path.join(BASE_DIR, "data", "processed", "history", fname)
        if not os.path.exists(fpath):
            return {"error": "No history for this repo"}
        with open(fpath) as f:
            return json.load(f)

    def _get_overview(self):
        history_dir = os.path.join(BASE_DIR, "data", "processed", "history")
        total_tracked = 0
        if os.path.exists(history_dir):
            total_tracked = len([f for f in os.listdir(history_dir) if f.endswith(".json")])
        return {
            "total_tracked": total_tracked,
            "available_dates": self._get_available_dates(),
        }


def main():
    port = 8080
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])

    server = HTTPServer(("0.0.0.0", port), APIHandler)
    print(f"""
╔══════════════════════════════════════════════════════╗
║   🚀 GitHub Trending Loop — 本地仪表盘               ║
║                                                      ║
║   打开浏览器访问: http://localhost:{port}              ║
║                                                      ║
║   按 Ctrl+C 停止服务                                  ║
╚══════════════════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()