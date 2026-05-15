#!/bin/bash
# B站爬虫定时运行脚本
# 每5分钟执行一次，读取最新配置

cd "$(dirname "$0")"

echo "========== $(date '%Y-%m-%d %H:%M:%S') ==========" >> spider.log
echo "开始运行爬虫..." >> spider.log

python3 bilibili_spider.py >> spider.log 2>&1

echo "运行完成" >> spider.log
echo "" >> spider.log