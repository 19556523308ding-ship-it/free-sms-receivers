#!/bin/bash
# 接码号码聚合站 —— 数据刷新
# 采集 -> 同步到 web 目录。失败保留旧数据，不覆盖。
set -u

BASE=/opt/sms-hub
LOG=$BASE/logs/refresh.log
mkdir -p "$(dirname "$LOG")"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

echo "===== $(date '+%F %T') 开始刷新 =====" >> "$LOG"

cd "$BASE" || { echo "目录不存在" >> "$LOG"; exit 1; }

# 采集到临时文件，校验通过才替换正式数据
if python3 scrapers/collect.py >> "$LOG" 2>&1; then
    SRC="$BASE/scrapers/data/numbers.json"
    # 校验：必须是合法 JSON 且号码数量 > 0
    if python3 -c "
import json,sys
d=json.load(open('$SRC',encoding='utf-8'))
n=d.get('total',0)
assert n>0, '号码数为 0'
assert n==len(d.get('numbers',[])), 'total 与实际条数不符'
print(f'校验通过: {n} 个号码')
" >> "$LOG" 2>&1; then
        cp "$SRC" "$BASE/web/data/numbers.json"
        echo "已更新 web/data/numbers.json" >> "$LOG"
    else
        echo "校验失败，保留旧数据" >> "$LOG"
    fi
else
    echo "采集失败，保留旧数据" >> "$LOG"
fi

echo "===== $(date '+%F %T') 结束 =====" >> "$LOG"
