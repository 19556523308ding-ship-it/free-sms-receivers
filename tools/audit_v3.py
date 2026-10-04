#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三轮：深挖两个已确认可用的源 —— sms-online.co 与 FreePhoneNum
目标：确认能否稳定结构化解析出「号码 + 短信正文 + 时间」，用于站内收码。
只读公开页面。
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
GAP = 1.4
_last = {}


def get(url, timeout=25, referer=None):
    host = urllib.parse.urlparse(url).netloc
    now = time.time()
    w = GAP - (now - _last.get(host, 0))
    if w > 0:
        time.sleep(w)
    _last[host] = time.time()
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", errors="replace"), dict(r.headers), r.geturl()


def absolutize(base, href):
    return urllib.parse.urljoin(base, href)


def norm(d):
    d = re.sub(r"\D", "", d or "")
    return d if 9 <= len(d) <= 15 else ""


def visible(html):
    b = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"[ \t]+", " ", re.sub(r"(?s)<[^>]+>", "\n", b))


# ============ A. FreePhoneNum 列表页结构 ============
def deep_freephonenum():
    print("=" * 84)
    print("[A] FreePhoneNum  —— 列表页结构分析")
    print("=" * 84)
    base = "https://freephonenum.com"
    try:
        st, html, _, _ = get(f"{base}/numbers")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return {}

    print(f"  状态 {st}, {len(html)} bytes")
    # 找号码链接的完整 href
    links = {}
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        href, inner = m.group(1), m.group(2)
        d = norm(re.sub(r"(?s)<[^>]+>", "", inner)) or norm(href.rstrip("/").split("/")[-1])
        if d and 9 <= len(d) <= 15:
            links.setdefault(d, absolutize(base, href))
    print(f"  号码链接: {len(links)} 个")
    for d, u in list(links.items())[:8]:
        print(f"    {d}  ->  {u}")

    # 找列表容器 class
    classes = re.findall(r'<div[^>]+class="([^"]*(?:number|phone|card|list|item)[^"]*)"', html, re.I)
    from collections import Counter
    print(f"  容器 class top: {Counter(classes).most_common(5)}")

    # 抽样测详情页
    print("\n  抽样 3 个详情页:")
    samples = list(links.items())[:3]
    out = []
    for d, u in samples:
        try:
            s2, h2, hd2, f2 = get(u, referer=f"{base}/numbers")
        except Exception as e:
            print(f"    {d}: ❌ {type(e).__name__}")
            out.append({"phone": d, "url": u, "error": type(e).__name__})
            continue
        guard = ""
        for p, l in [(r"(?i)captcha|recaptcha|hcaptcha|aliyuncaptcha|人机验证", "captcha"),
                     (r"(?i)need to (login|sign up)|please log ?in", "login_wall"),
                     (r"(?i)just a moment|checking your browser", "cf")]:
            if re.search(p, h2):
                guard = l
                break
        vis = visible(h2)
        kw = re.findall(r"(?i)verification code|your code|one[- ]time|passcode|security code|验证码", vis)
        # 尝试找短信块结构
        sblocks = re.findall(r'class="([^"]*(?:message|sms)[^"]*)"', h2, re.I)
        print(f"    {d}: {s2} guard={guard or '-'} kw={len(kw)} "
              f"xfo={hd2.get('X-Frame-Options', '-')} msgclass={len(sblocks)}")
        seg = re.sub(r"\n+", " | ", vis)[:300]
        print(f"       文本: {seg[:220]}")
        out.append({"phone": d, "url": u, "status": s2, "guard": guard, "kw": len(kw),
                    "xfo": hd2.get("X-Frame-Options", ""), "msgclass": len(sblocks),
                    "sample": seg[:400]})
        sys.stdout.flush()
        time.sleep(1.5)
    return {"list": f"{base}/numbers", "count": len(links), "samples": out}


# ============ B. sms-online.co 详情页正文结构 ============
def deep_smsonlineco():
    print("\n" + "=" * 84)
    print("[B] sms-online.co  —— 详情页短信正文结构")
    print("=" * 84)
    base = "https://www.sms-online.co"
    listurl = f"{base}/receive-free-sms"
    try:
        st, html, _, _ = get(listurl)
    except Exception as e:
        print(f"  ❌ 列表页 {type(e).__name__}")
        return {}

    links = {}
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        href, inner = m.group(1), m.group(2)
        d = norm(re.sub(r"(?s)<[^>]+>", "", inner)) or norm(href.rstrip("/").split("/")[-1])
        if d and 9 <= len(d) <= 15:
            links.setdefault(d, absolutize(listurl, href))
    print(f"  列表页 {st}, 号码 {len(links)} 个")
    for d, u in list(links.items())[:6]:
        print(f"    {d}  ->  {u}")

    print("\n  逐个测详情页（重点看正文结构）:")
    out = []
    for d, u in list(links.items())[:5]:
        try:
            s2, h2, hd2, f2 = get(u, referer=listurl)
        except Exception as e:
            print(f"    {d}: ❌ {type(e).__name__}")
            continue
        guard = ""
        for p, l in [(r"(?i)captcha|recaptcha|hcaptcha|aliyuncaptcha|人机验证|单击此处验证", "captcha"),
                     (r"(?i)need to (login|sign up)|please log ?in", "login_wall")]:
            if re.search(p, h2):
                guard = l
                break

        # 找短信容器：<table> 行 或 div.message
        rows = []
        for tm in re.finditer(r"<t[dh][^>]*>(.*?)</t[dh]>", h2, re.S | re.I):
            t = re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", tm.group(1))).strip()
            if t:
                rows.append(t)
        # 常见短信关键词行
        msgrows = [r for r in rows if re.search(
            r"(?i)verification|code|OTP|passcode|security|your|短信|验证码", r)]

        print(f"    {d}: {s2} guard={guard or '-'} 表格单元={len(rows)} 疑似短信行={len(msgrows)}")
        if msgrows:
            for r in msgrows[:3]:
                print(f"       ▸ {r[:150]}")
        elif rows:
            for r in rows[:5]:
                print(f"       · {r[:110]}")
        out.append({"phone": d, "url": u, "status": s2, "guard": guard,
                    "cells": len(rows), "msg_rows": msgrows[:6]})
        sys.stdout.flush()
        time.sleep(1.6)
    return {"list": listurl, "count": len(links), "samples": out}


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    data = {}
    if which in ("all", "fpn"):
        data["freephonenum"] = deep_freephonenum()
    if which in ("all", "soc"):
        data["sms_online_co"] = deep_smsonlineco()
    with open("/tmp/source_v3.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("\n已写入 /tmp/source_v3.json")
