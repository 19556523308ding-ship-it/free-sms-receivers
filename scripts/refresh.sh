#!/bin/bash
# 接码号码聚合站 —— 数据刷新
# 采集 -> 同步到 web 目录。失败保留旧数据，不覆盖。
set -u

BASE=/opt/sms-hub
LOG=$BASE/logs/refresh.log
mkdir -p "$(dirname "$LOG")"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

echo "===== $(date '+%F %T') 开始刷新 =====" >> "$LOG"

# 连续失败计数（防「静默不更新」重演）：
# 之前采集与校验全程无异常提示，只有日志深处一行 AssertionError，
# 连续 5 次刷新失败也没人发现。超过 2 次就在日志顶部打醒目告警。
FAIL_STREAK_FILE=$BASE/logs/.refresh_fail_streak
streak=0
if [ -f "$FAIL_STREAK_FILE" ]; then
    streak=$(cat "$FAIL_STREAK_FILE" 2>/dev/null || echo 0)
    case "$streak" in ''|*[!0-9]*) streak=0 ;; esac
fi

cd "$BASE" || { echo "目录不存在" >> "$LOG"; exit 1; }

# 采集到临时文件，校验通过才替换正式数据
if python3 scrapers/collect.py >> "$LOG" 2>&1; then
    SRC="$BASE/scrapers/data/numbers.json"
    # 校验：必须是合法 JSON、号码数量 > 0、且与实际条数一致。
    #
    # 字段名不写死：曾因校验脚本读顶层 'total'，而采集器输出的是
    # 'totals' = {'records':N,'uniquePhones':N,'countries':N,'sources':N}，
    # 导致断言恒为 0 —— 定时刷新连续 5 次静默失败，线上数据悄悄停在
    # 旧版本而无人察觉。故改为「以 len(numbers) 为准」，
    # 再尝试从几种可能的声明位置取值做交叉核对，取不到就跳过核对（不误杀）。
    if python3 -c "
import json,sys
d=json.load(open('$SRC',encoding='utf-8'))
nums=d.get('numbers')
assert isinstance(nums,list), 'numbers 字段不是列表'
actual=len(nums)
assert actual>0, '号码数为 0'

# 交叉核对：顶层 total -> totals.records -> totals.numbers（兼容历史与将来改名）
declared=None
for path in (('total',), ('totals','records'), ('totals','numbers'), ('totals','total')):
    cur=d
    ok=True
    for k in path:
        if isinstance(cur,dict) and k in cur:
            cur=cur[k]
        else:
            ok=False; break
    if ok and isinstance(cur,int):
        declared=cur; break

assert declared is None or declared==actual, f'声明条数 {declared} 与实际 {actual} 不符'
print(f'校验通过: {actual} 个号码' + (f'（声明 {declared} 一致）' if declared is not None else '（无声明字段，仅校验非空）'))
" >> "$LOG" 2>&1; then
        cp "$SRC" "$BASE/web/data/numbers.json"
        echo "已更新 web/data/numbers.json ($(date '+%F %T'))" >> "$LOG"
        echo 0 > "$FAIL_STREAK_FILE"
    else
        echo "校验失败，保留旧数据（详见上方 AssertionError）" >> "$LOG"
        streak=$((streak+1)); echo "$streak" > "$FAIL_STREAK_FILE"
    fi
else
    echo "采集失败，保留旧数据" >> "$LOG"
    streak=$((streak+1)); echo "$streak" > "$FAIL_STREAK_FILE"
fi

if [ "$streak" -ge 2 ]; then
    echo "!!!!!!!! 告警：数据刷新已连续失败 $streak 次，线上号码数据可能已过期 !!!!!!!!" >> "$LOG"
fi

echo "===== $(date '+%F %T') 结束（本轮失败计数: $streak）=====" >> "$LOG"
