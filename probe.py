#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""探测各接码平台的 HTML 结构，找出可稳定解析的号码选择器。"""
import re
import sys
import json
import urllib.request
import urllib.error

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")


def probe(name, url, patterns):
    print("=" * 70)
    print(f"### {name}  ->  {url}")
    try:
        html = fetch(url)
    except Exception as e:
        print(f"  !! 抓取失败: {type(e).__name__}: {e}")
        return None
    print(f"  HTML 长度: {len(html)}")
    for label, rx in patterns:
        hits = re.findall(rx, html, re.I)
        uniq = []
        seen = set()
        for h in hits:
            key = h if isinstance(h, str) else json.dumps(h)
            if key not in seen:
                seen.add(key)
                uniq.append(key)
        sample = uniq[:6]
        print(f"  [{label}] 命中 {len(hits)} / 去重 {len(uniq)}")
        for s in sample:
            print(f"      {s[:110]}")
    return html


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "all"

    if target in ("all", "wetalk"):
        probe("WeTalk", "https://wetalkapp.com/receive-sms/", [
            ("文章卡片", r'class="et_pb_post[^"]*post-(\d+)'),
            ("分类", r'category-([a-z\-]+)'),
            ("标题链接", r'<h\d[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>([^<]{3,80})'),
            ("正文内数字串", r'>\s*(\+?\d[\d\-\s()]{7,20}\d)\s*<'),
        ])

    if target in ("all", "rso"):
        probe("Receive-SMS-Online", "https://receive-sms-online.info/", [
            ("国家分栏", r'data-country="([^"]+)"'),
            ("号码块", r'class="[^"]*(?:number|phone)[^"]*"[^>]*>([^<]{5,30})<'),
            ("裸号", r'>\s*(\+\d{9,15})\s*<'),
            ("分页/国家链接", r'href="(/country-[a-z]+[^"]*)"'),
        ])

    if target in ("all", "quackr"):
        probe("Quackr", "http://quackr.io/", [
            ("Angular 数据岛", r'ng-state="([^"]{40,200})"'),
            ("script 中的号码", r'(\+\d{9,15})'),
            ("国家路径", r'"([a-z]{2}(?:-[a-z]{2})?)"'),
        ])
