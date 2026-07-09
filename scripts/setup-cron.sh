#!/bin/bash
# 设置每日 8:00 定时任务
LOOP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CRON_ENTRY="0 8 * * * /bin/bash $LOOP_DIR/scripts/run-loop.sh >> $LOOP_DIR/cron.log 2>&1"

# 检查是否已存在
if crontab -l 2>/dev/null | grep -q "github-trending-loop"; then
    echo "⏭️  Cron 任务已存在，跳过"
    crontab -l 2>/dev/null | grep "github-trending-loop"
else
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "✅ Cron 任务已设置: 每天 8:00 自动运行"
    echo "   $CRON_ENTRY"
fi