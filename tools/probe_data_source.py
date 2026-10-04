#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定位 JS 渲染站点的数据来源：
1) 页面内联 JSON（__NEXT_DATA__ / window.__X__ = {...}）
2) JS bundle 里的 API 基址与请求路径
3) 试探常见 REST 路径
只读公开资源，不做任何鉴权绕过。
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
_last = {}


def get(url, timeout=25, referer=None, raw=False):
    host = urllib.parse.urlparse(url).netloc
    now = time.time()
    w = 1.2 - (now - _last.get(host, 0))
    if w > 0:
        time.sleep(w)
    _last[host] = time.time()
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9", "Accept": "*/*"}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read()
        return r.status, (b if raw else b.decode("utf-8", errors="replace")), dict(r.headers)


def analyze(name, page_url):
    print("=" * 84)
    print(f"[{name}] {page_url}")
    print("=" * 84)
    try:
        st, html, _ = get(page_url)
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return
    print(f"  状态 {st}, {len(html)} bytes")

    # 1) 内联 JSON
    print("\n  [1] 内联 JSON 数据")
    inl = []
    for pat, lbl in [
        (r'__NEXT_DATA__\s*=\s*(\{.*?\})\s*;?\s*</script>', "__NEXT_DATA__"),
        (r'window\.__NUXT__\s*=\s*(\{.*?\})\s*;?\s*</script>', "__NUXT__"),
        (r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?\s*</script>', "__INITIAL_STATE__"),
        (r'window\.__PRELOADED_STATE__\s*=\s*(\{.*?\})\s*;?\s*</script>', "__PRELOADED_STATE__"),
    ]:
        m = re.search(pat, html, re.S)
        if m:
            blob = m.group(1)
            inl.append((lbl, len(blob)))
            print(f"    ✅ {lbl}: {len(blob)} bytes")
            # 尝试提取短信样例
            for kw in ("message", "sms", "text", "body", "otp"):
                hits = re.findall(rf'"{kw}"\s*:\s*("(?:[^"\\]|\\.){{10,200}}")', blob)
                if hits:
                    print(f"       '{kw}' 字段样例: {hits[:3]}")
    if not inl:
        print("    (无常见内联状态)")

    # 2) JS bundle 里的 API 线索
    print("\n  [2] JS bundle API 线索")
    scripts = re.findall(r'<script[^>]+src="([^"]+\.js[^"]*)"', html)
    print(f"    脚本数: {len(scripts)}")
    api_hits = set()
    api_re = [
        r'https?://[a-z0-9.\-]+\.[a-z]{2,}/[A-Za-z0-9/_\-{}$.?=&%:]*(?:api|json|message|sms)[A-Za-z0-9/_\-{}$.?=&%:]*',
        r'["\'`](/(?:api|v\d)/[A-Za-z0-9/_\-{}$.?=&:]*)["\'`]',
        r'(?:fetch|axios(?:\.get|\.post)?)\(\s*[`"\']([^`"\']{5,140})[`"\']',
        r'baseURL\s*[:=]\s*[`"\']([^`"\']{6,120})[`"\']',
        r'axios\.create\(\{[^}]{0,200}baseURL[^}]{0,120}\}',
    ]
    for s in scripts[:20]:
        surl = urllib.parse.urljoin(page_url, s)
        try:
            sst, js, _ = get(surl, referer=page_url)
        except Exception:
            continue
        if sst != 200 or len(js) < 500:
            continue
        for p in api_re:
            for m in re.findall(p, js, re.I):
                if isinstance(m, tuple):
                    m = m[0]
                if len(m) > 4:
                    api_hits.add(m)
        print(f"    ✓ {s.split('/')[-1][:60]} ({len(js)}b)")
    for h in sorted(api_hits)[:25]:
        print(f"      → {h}")

    # 3) 试探 REST
    print("\n  [3] 常见 REST 路径试探")
    root = urllib.parse.urlparse(page_url)
    origin = f"{root.scheme}://{root.netloc}"
    seg = root.path.strip("/").split("/")
    tries = [
        f"{origin}/api/messages",
        f"{origin}/api/sms",
        f"{origin}/api/v1/messages",
        f"{origin}/api/phone/{seg[-1]}/messages",
        f"{origin}/api/messages?phone={seg[-1]}",
        f"{origin}/messages/{seg[-1]}.json",
    ]
    for t in tries:
        try:
            sst, body, hh = get(t, referer=page_url)
            ct = hh.get("Content-Type", "")[:40]
            print(f"    {sst} {t[len(origin):]}  [{ct}]  {str(body)[:110]}")
        except Exception as e:
            code = getattr(e, "code", type(e).__name__)
            print(f"    ✗ {code} {t[len(origin):]}")
        time.sleep(0.8)
    print()


if __name__ == "__main__":
    analyze("FreePhoneNum", "https://freephonenum.com/be/receive-sms/466900108")
    analyze("sms-online.co", "https://www.sms-online.co/receive-free-sms/447599512664")
    analyze("receiveasmsonline", "https://receiveasmsonline.com/united-states/12175285111/")
