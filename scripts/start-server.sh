#!/bin/bash
# 启动本地 Web 仪表盘
# 用法: bash scripts/start-server.sh [端口号]

PORT="${1:-8080}"
cd "$(dirname "$0")/.."

echo "🚀 启动 GitHub Trending Loop 仪表盘..."
echo "   打开浏览器访问: http://localhost:$PORT"
echo "   按 Ctrl+C 停止"
echo ""

python3 src/server.py --port "$PORT"