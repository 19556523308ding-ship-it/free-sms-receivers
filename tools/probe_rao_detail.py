#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决定性验证：receiveasmsonline.com 号码详情页的短信正文是否公开可读（纯 HTTP）。
只读公开页面内容。
"""
import re
import sys
import time
import urllib.request
from html import unescape

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://receiveasmsonline.com/",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", errors="replace")


def text_of(fragment):
    f = re.sub(r"(?s)<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", unescape(f)).strip()


GUARDS = [
    (r"(?i)need to (login|sign up|log in)|please log ?in|create (an )?account to view", "登录墙"),
    (r"(?i)captcha|recaptcha|hcaptcha|turnstile|aliyuncaptcha|verify you are human|单击此处验证", "人机验证"),
    (r"(?i)just a moment|checking your browser", "Cloudflare 拦截"),
]


def check_guards(html):
    for pat, label in GUARDS:
        if re.search(pat, html):
            return label
    return None


def probe_detail(phone, path):
    url = f"https://receiveasmsonline.com{path}"
    print("-" * 78)
    print(f"号码 {phone}")
    print(f"URL  {url}")
    try:
        st, html = get(url)
    except Exception as e:
        print(f"  ❌ 请求失败: {type(e).__name__}: {e}")
        return False

    print(f"  状态 {st}, {len(html)} bytes")

    blocked = check_guards(html)
    if blocked:
        print(f"  ⛔ 命中{blocked} —— 不可用")
        return False
    print(f"  ✅ 无登录墙 / 无人机验证")

    # 找正文容器：常见的 message/sms 列表 class
    containers = re.findall(
        r'<div[^>]+class="([^"]*(?:message|sms|msg|inbox|chat)[^"]*)"[^>]*>', html, re.I)
    from collections import Counter
    top = Counter(containers).most_common(6)
    print(f"  正文候选容器 class: {top}")

    # 提取页面可见文本，找验证码/短信样本
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    visible = re.sub(r"\s+", " ", text_of(body))

    # 短信常见词
    sms_hits = re.findall(
        r"(?i)(?:verification code|your code|one[- ]time|OTP|passcode|security code|"
        r"is your \w+ code|验证码|短信)", visible)
    otp = re.findall(r"\b(\d{4,8})\b", visible)

    print(f"  短信特征词命中: {len(sms_hits)} -> {Counter(sms_hits).most_common(4)}")
    print(f"  4-8位数字候选: {len(otp)} -> {otp[:12]}")

    # 打印号码页的核心可见文本片段（避开导航噪音）
    m = re.search(r"(?i)(?:latest messages|messages|sms)", visible)
    if m:
        seg = visible[m.start():m.start() + 700]
        print(f"  文本片段: {seg}")
    else:
        print(f"  文本前 400: {visible[:400]}")

    return len(sms_hits) > 0 or len(otp) > 3


if __name__ == "__main__":
    # 先取美国页号码列表，再逐个探详情
    st, html = get("https://receiveasmsonline.com/united-states/")
    phones = re.findall(r'href="/united-states/(\+?\d{7,15})/"', html)
    seen, uniq = set(), []
    for p in phones:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    print(f"美国页可用号码: {len(uniq)} 个，抽样 4 个测详情页\n")

    ok = 0
    for p in uniq[:4]:
        if probe_detail(p, f"/united-states/{p}/"):
            ok += 1
        time.sleep(2)

    print("\n" + "=" * 78)
    print(f"结论: {ok}/4 个号码详情页成功读到短信正文特征")
