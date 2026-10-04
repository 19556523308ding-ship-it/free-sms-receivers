#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定位 receiveasmsonline.com 站点自己调用的公开数据接口。
思路：翻出 JS bundle 里的 fetch/axios 路径。这是站点用于公开展示的数据面，不涉及任何鉴权绕过。
"""
import re
import sys
import urllib.request
from collections import Counter

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://receiveasmsonline.com/",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", errors="replace"), r.headers


PAGE = "https://receiveasmsonline.com/united-states/12175285111/"

st, html, hdrs = get(PAGE)
print(f"页面 {st}, {len(html)} bytes\n")

# ---- 1. 页面内联的 API 线索 ----
print("=" * 78)
print("[1] 页面内联线索")
pats = [
    r'https?://[a-z0-9.\-]*api[a-z0-9.\-]*/[A-Za-z0-9/_\-{}$.?=&]*',
    r'["\'](/api/[A-Za-z0-9/_\-{}$.?=&]*)["\']',
    r'["\'](https?://[^"\']*?/api/[^"\']*)["\']',
    r'NEXT_PUBLIC_[A-Z_]+',
    r'REACT_APP_[A-Z_]+',
]
found = set()
for p in pats:
    for m in re.findall(p, html, re.I):
        if isinstance(m, tuple):
            m = m[0]
        found.add(m)
for f in sorted(found)[:40]:
    print(f"  {f}")
if not found:
    print("  (无)")

# ---- 2. JS bundle 里的接口路径 ----
print("\n" + "=" * 78)
print("[2] JS bundle 内的接口路径")
scripts = re.findall(r'<script[^>]+src="([^"]+\.js)"', html)
print(f"  脚本数量: {len(scripts)}")

api_pats = [
    r'["\'`](/api/[A-Za-z0-9/_\-{}$.?=&:]*)["\'`]',
    r'["\'`](/v[0-9]/[A-Za-z0-9/_\-{}$.?=&:]*)["\'`]',
    r'(?:fetch|axios\.(?:get|post))\(\s*["\'`]([^"\'`]{4,120})["\'`]',
    r'https?://[a-z0-9.\-]+\.[a-z]{2,}/[A-Za-z0-9/_\-{}$.?=&]*api[A-Za-z0-9/_\-{}$.?=&]*',
]

hits = Counter()
for s in scripts[:25]:
    url = s if s.startswith("http") else ("https://receiveasmsonline.com" + s if s.startswith("/") else None)
    if not url:
        continue
    try:
        sst, js, _ = get(url)
    except Exception as e:
        print(f"  [skip] {s[:60]}: {type(e).__name__}")
        continue
    if sst != 200 or len(js) < 200:
        continue
    for p in api_pats:
        for m in re.findall(p, js):
            if len(m) > 3 and not m.startswith("/static") and "sourcemap" not in m:
                hits[m] += 1
    print(f"  ✓ {s[:70]} ({len(js)} bytes)")

print(f"\n  汇总候选接口 ({len(hits)}):")
for h, c in hits.most_common(40):
    print(f"    [{c}次] {h}")

# ---- 3. 关键词定位：消息相关的取数函数 ----
print("\n" + "=" * 78)
print("[3] bundle 中与 messages/telephone 相关的取数片段")
kw = re.compile(r"(?i)(fetchMessages|getMessages|loadMessages|messagesUrl|/messages|messageList)",)
for s in scripts[:25]:
    url = s if s.startswith("http") else ("https://receiveasmsonline.com" + s if s.startswith("/") else None)
    if not url:
        continue
    try:
        sst, js, _ = get(url)
    except Exception:
        continue
    if sst != 200:
        continue
    for m in kw.finditer(js):
        seg = js[max(0, m.start() - 160):m.start() + 200]
        seg = re.sub(r"\s+", " ", seg)
        print(f"  [{s.split('/')[-1][:40]}] ...{seg}...")
        break
