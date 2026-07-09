#!/bin/bash
# github-trending-loop — cron 触发脚本
#
# 用法: 在 crontab 中添加:
#   Run: bash scripts/setup-cron.sh (auto-detects project path)

set -e

LOOP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="$LOOP_DIR/cron.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ========== Loop Start ==========" >> "$LOG_FILE"

cd "$LOOP_DIR"

# 使用 Python 自包含脚本，不依赖 Claude CLI
python3 src/fetch_trending.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Loop End (exit=$EXIT_CODE)" >> "$LOG_FILE"

exit $EXIT_CODE