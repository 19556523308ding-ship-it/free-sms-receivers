#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实测：receive-sms-free.cc 与 receiveasmsonline.com 的短信正文能否用纯 HTTP 抓到。
只读取页面上公开可见的内容，不绕登录、不破验证码。
"""
import re
import sys
import time
import urllib.request
import urllib.error
from html import unescape

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


def strip_tags(fragment):
    f = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", fragment)
    f = re.sub(r"(?s)<[^>]+>", "\x01", f)          # 保留单元格分隔
    f = unescape(f)
    return f


# ---- receive-sms-free.cc ----
# 列表页: /Free-USA-Phone-Number/  号码链接 li a[href] > h2 > span
RSO_LIST_RE = re.compile(
    r'<li[^>]*>\s*<a[^>]+href="(?P<href>[^"]+)"[^>]*>\s*<h2[^>]*>\s*<span[^>]*>(?P<num>[^<]+)</span>',
    re.S)
# 详情页短信行: .casetext > .row  每行 3+ 个 td
RSO_ROW_RE = re.compile(
    r'<div class="casetext"[^>]*>(.*?)</div>\s*</div>', re.S)
RSO_TR_RE = re.compile(r'<tr[^>]*>(.*?)</tr>', re.S)
RSO_TD_RE = re.compile(r'<t[dh][^>]*>(.*?)</t[dh]>', re.S)


def probe_rso():
    print("=" * 78)
    print("[receive-sms-free.cc]  列表页解析")
    base = "https://receive-sms-free.cc"
    try:
        st, html = get(f"{base}/Free-USA-Phone-Number/")
    except Exception as e:
        print(f"  ❌ 列表页失败: {type(e).__name__}: {e}")
        return
    print(f"  状态 {st}, {len(html)} bytes")

    items = RSO_LIST_RE.findall(html)
    print(f"  解析到号码链接: {len(items)} 个")
    for href, num in items[:5]:
        print(f"    {num.strip():>16}  ->  {href.strip()}")

    if not items:
        # 退化：任意含数字的 href
        cand = re.findall(r'href="(/Free-[^"]*?/\d{6,15}/)"', html)
        print(f"  [退化匹配] /Free-*/ 数字 形式的链接: {len(cand)} 个")
        for c in cand[:5]:
            print(f"    {c}")
        items = [(c, c) for c in cand]

    if not items:
        print("  ❌ 未能解析出任何号码，页面结构与源码不符")
        return

    # 详情页
    target = items[0][0]
    detail = target if target.startswith("http") else base + target
    print(f"\n  详情页探测: {detail}")
    try:
        st2, html2 = get(detail)
    except Exception as e:
        print(f"  ❌ 详情页失败: {type(e).__name__}: {e}")
        return
    print(f"  状态 {st2}, {len(html2)} bytes")

    for guard, label in [(r"(?i)need to (login|sign up)|please log ?in", "登录墙"),
                         (r"(?i)captcha|aliyuncaptcha|单击此处验证", "人机验证")]:
        if re.search(guard, html2):
            print(f"  ⛔ 命中{label}")
            return

    block = RSO_ROW_RE.search(html2)
    if not block:
        print("  ❌ 未找到 .casetext 容器")
        # 看看页面有哪些 class 提示结构变了
        classes = re.findall(r'class="([^"]*(?:case|message|sms|text)[^"]*)"', html2)[:12]
        print(f"  [调试] 含 case/message/sms 的 class: {classes}")
        return

    rows = RSO_TR_RE.findall(block.group(1))
    print(f"  ✅ 找到 .casetext，解析到 {len(rows)} 行短信")
    for tr in rows[:6]:
        tds = [strip_tags(td).replace("\x01", " ").strip() for td in RSO_TD_RE.findall(tr)]
        tds = [re.sub(r"\s+", " ", t) for t in tds]
        print(f"    {tds}")


# ---- receiveasmsonline.com ----
RAO_HREF_RE = re.compile(r'href="([^"]*(?:phone|number|sms)[^"]*/?)"[^>]*>\s*([^<]{4,30})', re.I)


def probe_rao():
    print("\n" + "=" * 78)
    print("[receiveasmsonline.com]  解析")
    base = "https://receiveasmsonline.com"
    try:
        st, html = get(f"{base}/")
    except Exception as e:
        print(f"  ❌ 失败: {type(e).__name__}: {e}")
        return
    print(f"  状态 {st}, {len(html)} bytes")

    # 国家 + 数量
    rows = re.findall(r'>\s*(\d+)\s*</[^>]+>\s*<[^>]+>\s*([A-Z][a-z]{2,})\s*<', html)
    print(f"  国家/数量候选: {len(rows)} 组")
    for n, c in rows[:8]:
        print(f"    {c}: {n}")

    if not rows:
        cands = re.findall(r'href="(/[a-z]{2,}(?:-[a-z]+)?/)"', html)
        uniq = sorted(set(cands))[:20]
        print(f"  [调试] 疑似国家路径 {len(uniq)} 个: {uniq}")

    # 找一个国家页
    m = re.search(r'href="(/usa/|/united-states/|/united-states)"', html)
    if not m:
        cands = re.findall(r'href="(/[a-z-]+/)"', html)
        m = re.match(r'./', cands[0]) if cands else None
        path = m.group(1) if m else None
    else:
        path = m.group(1)
    print(f"  进入国家页: {path}")
    if not path:
        return
    try:
        st2, html2 = get(base + path)
    except Exception as e:
        print(f"  ❌ 国家页失败: {e}")
        return
    print(f"  状态 {st2}, {len(html2)} bytes")

    phone_links = re.findall(r'href="([^"]*?/(\+?\d{7,15})/?)"', html2)
    print(f"  号码链接: {len(phone_links)} 个")
    for h, p in phone_links[:6]:
        print(f"    {p}  ->  {h}")

    if not phone_links:
        scripts = re.findall(r'src="([^"]*\.js[^"]*)"', html2)[:8]
        print(f"  [调试] 脚本: {scripts}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "rso"):
        probe_rso()
    if which in ("all", "rao"):
        probe_rao()
