#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
探测各免费接码平台的「短信正文是否公开可见（无需登录 / 无人机验证）」
只做只读探测，不绕任何登录墙或人机验证。
"""
import re
import sys
import time
import urllib.request
import urllib.error

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

OPENER = urllib.request.build_opener()
OPENER.addheaders = [("User-Agent", UA),
                     ("Accept-Language", "en-US,en;q=0.9")]


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Language": "en-US,en;q=0.9"})
    with OPENER.open(req, timeout=timeout) as r:
        raw = r.read()
        enc = r.headers.get_content_charset() or "utf-8"
        try:
            html = raw.decode(enc, errors="replace")
        except LookupError:
            html = raw.decode("utf-8", errors="replace")
        return r.status, dict(r.headers), html, url


def strip_tags(h):
    h = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?s)<[^>]+>", "\n", h)
    h = re.sub(r"&nbsp;?", " ", h)
    h = re.sub(r"&amp;", "&", h)
    h = re.sub(r"\n{2,}", "\n", h)
    return h.strip()


# 登录墙 / 人机验证 / 空壳 CSR 的特征词
BLOCK_SIGNS = [
    ("login_wall", r"(?i)need to (login|sign up|log in)|you need to be logged|"
                   r"please\s*(login|sign in)|register to view|create an account to"),
    ("captcha", r"(?i)captcha|recaptcha|hcaptcha|turnstile|aliyuncaptcha|"
                r"verify you are (a )?human|单击此处验证|人机验证"),
    ("csrf_only", r"(?i)cf-browser-verification|checking your browser|"
                  r"just a moment|ddos protection"),
]

# 短信正文的特征：otp 码 / 短信常见词
SMS_SIGNS = [
    ("otp_code", r"\b\d{4,8}\b"),
    ("sms_words", r"(?i)verification code|your code|one-time|OTP|"
                  r"is your|passcode|security code|短信验证码|验证码"),
]


def probe(name, url, extract_hint=None):
    row = {"name": name, "url": url}
    try:
        st, hdrs, html, final = fetch(url)
    except urllib.error.HTTPError as e:
        row["status"] = f"HTTP {e.code}"
        row["verdict"] = "❌ HTTP 错误"
        return row
    except Exception as e:
        row["status"] = "ERR"
        row["verdict"] = f"❌ {type(e).__name__}: {str(e)[:60]}"
        return row

    row["status"] = st
    row["bytes"] = len(html)
    row["final_url"] = final
    text = strip_tags(html)

    # 阻断信号
    for label, pat in BLOCK_SIGNS:
        if re.search(pat, html):
            row["block"] = label
            break

    # 头部安全/渲染策略
    flags = []
    xfo = hdrs.get("X-Frame-Options", "")
    csp = hdrs.get("Content-Security-Policy", "") or ""
    if xfo:
        flags.append(f"XFO={xfo}")
    if "frame-ancestors" in csp:
        flags.append("CSP:frame-ancestors")
    row["headers"] = ",".join(flags) or "-"

    # 渲染方式
    if re.search(r"(?i)ng-version|ng-state=|<app-root", html):
        row["render"] = "Angular CSR"
    elif re.search(r"(?i)__NEXT_DATA__|_next/static", html):
        row["render"] = "Next.js"
    elif re.search(r"(?i)window\.__NUXT|__vite__client", html):
        row["render"] = "Vue/Nuxt"
    else:
        row["render"] = "静态 HTML"

    # 是否含号码
    phone = re.search(r"\+?\d{9,14}", text)
    row["has_phone"] = bool(phone)

    # 是否含短信正文特征
    hits = [lbl for lbl, pat in SMS_SIGNS if re.search(pat, text)]
    row["sms_signals"] = ",".join(hits) or "-"

    # 取一段可见文本样本（判断是号码列表页还是短信详情页）
    sample = re.sub(r"[ \t]+", " ", text)[:600]
    row["sample"] = sample
    return row


TARGETS = [
    ("smstome", "https://smstome.com/"),
    ("receive-sms-free", "https://receive-sms-free.cc/"),
    ("anonymsms", "https://anonymsms.com/"),
    ("receivesms", "https://receivesms.co/"),
    ("receiveasmsonline", "https://receiveasmsonline.com/"),
    ("receive-smss-online", "https://receive-smss-online.com/"),
    ("quackr", "https://quackr.io/"),
]

if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name, url in TARGETS:
        if only and only not in name:
            continue
        r = probe(name, url)
        print("=" * 78)
        print(f"[{r['name']}]  {r['url']}")
        print(f"  状态      : {r['status']}  ({r.get('bytes', 0)} bytes)")
        print(f"  最终URL   : {r.get('final_url', '-')}")
        print(f"  渲染方式  : {r.get('render', '-')}")
        print(f"  安全头    : {r.get('headers', '-')}")
        print(f"  阻断信号  : {r.get('block', '✅ 无')}")
        print(f"  含号码    : {r.get('has_phone', '-')}")
        print(f"  短信特征  : {r.get('sms_signals', '-')}")
        print(f"  可见文本  : {r.get('sample', '-')[:400]}")
        sys.stdout.flush()
        time.sleep(1.5)
