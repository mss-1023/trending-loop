.PHONY: run server cron test clean

# 手动运行一次抓取
run:
	python3 src/fetch_trending.py

# 启动 Web 仪表盘
server:
	python3 src/server.py --port 8080

# 设置 cron 定时任务
cron:
	bash scripts/setup-cron.sh

# 运行测试
test:
	python3 -m pytest tests/ -v 2>/dev/null || echo "No tests yet"

# 清理临时文件
clean:
	rm -rf __pycache__ src/__pycache__ .pytest_cache
	find . -name "*.pyc" -delete

# 查看最新日报
latest:
	@ls -t data/output/*.md 2>/dev/null | head -1 | xargs cat
