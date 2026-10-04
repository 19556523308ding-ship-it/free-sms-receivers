#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sms-hub 采集器
聚合公开可访问的免费接码号码元数据。

合规原则：
1. 只抓取公开展示的号码列表页，不绕过任何登录墙 / 付费墙 / 反爬机制。
2. 不抓取短信正文（对方已设登录限制），只聚合号码元数据。
3. 串行请求 + 随机延迟，避免对目标站造成压力。
4. 每个源独立失败隔离，单源挂掉不影响整体产出。
"""

import json
import os
import random
import re
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "data", "numbers.json")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch(url, referer=None, timeout=25, retries=2):
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception as e:
            last = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1) + random.random())
    raise last


# ---------------------------------------------------------------- 国家映射
def _norm_key(s):
    """把国家名统一成小写空格分隔，作为映射键。"""
    s = (s or "").strip().lower()
    s = re.sub(r"[_\-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# 规范化后的国家映射： key -> (中文名, 国旗, 国家码)
COUNTRY_ZH = {
    "united states": ("美国", "🇺🇸", "1"),
    "usa": ("美国", "🇺🇸", "1"),
    "us": ("美国", "🇺🇸", "1"),
    "united kingdom": ("英国", "🇬🇧", "44"),
    "uk": ("英国", "🇬🇧", "44"),
    "canada": ("加拿大", "🇨🇦", "1"),
    "australia": ("澳大利亚", "🇦🇺", "61"),
    "germany": ("德国", "🇩🇪", "49"),
    "france": ("法国", "🇫🇷", "33"),
    "finland": ("芬兰", "🇫🇮", "358"),
    "sweden": ("瑞典", "🇸🇪", "46"),
    "netherlands": ("荷兰", "🇳🇱", "31"),
    "poland": ("波兰", "🇵🇱", "48"),
    "spain": ("西班牙", "🇪🇸", "34"),
    "india": ("印度", "🇮🇳", "91"),
    "russia": ("俄罗斯", "🇷🇺", "7"),
    "brazil": ("巴西", "🇧🇷", "55"),
    "hong kong": ("中国香港", "🇭🇰", "852"),
    "singapore": ("新加坡", "🇸🇬", "65"),
}


def country_meta(raw):
    key = _norm_key(raw)
    if key in COUNTRY_ZH:
        return COUNTRY_ZH[key]
    return (raw or "未知", "🏳️", "")


def normalize(raw_digits, cc=""):
    """把裸数字补成 E.164 格式。"""
    d = re.sub(r"\D", "", raw_digits or "")
    if not d:
        return None
    if cc and not d.startswith(cc):
        d = cc + d.lstrip("0")
    return "+" + d


# ---------------------------------------------------------------- 采集源
def scrape_receive_sms_online():
    """receive-sms-online.info —— 首页按国家分组列出公开号码。"""
    url = "https://receive-sms-online.info/"
    html = fetch(url)
    out = []
    seen = set()
    # <a href="{数字}-{国家}">+{数字}</a>  且前文有 flag alt="{国家}"
    for m in re.finditer(
        r'alt="([A-Za-z ]+)"[^>]*>.*?href="(\d{9,15})-([A-Za-z ]+)"', html, re.S
    ):
        flag_alt, digits, name = m.group(1).strip(), m.group(2), m.group(3).strip()
        if digits in seen:
            continue
        #取该号码块内的 Messages 计数
        tail = html[m.end(): m.end() + 700]
        cnt = re.search(r"Messages:\s*<span[^>]*>\s*(\d+)", tail)
        seen.add(digits)
        out.append({
            "number": normalize(digits),
            "country_raw": name or flag_alt,
            "platform": "Receive-SMS-Online",
            "platform_slug": "receive-sms-online",
            "messages": int(cnt.group(1)) if cnt else None,
            "online": None,
            "detail_url": f"https://receive-sms-online.info/{digits}-{name.replace(' ', '')}",
            "home": url,
            "needs_login_for_content": True,
        })
    return out


def scrape_quackr():
    """quackr.io —— 卡片链接里带完整号码和slug 国家。"""
    url = "http://quackr.io/"
    html = fetch(url)
    out = []
    seen = set()
    for m in re.finditer(r'href="/temporary-numbers/([a-z\-]+)/(\d{9,15})"', html):
        slug, digits = m.group(1), m.group(2)
        if digits in seen:
            continue
        # 该卡片附近判断在线状态
        window = html[max(0, m.start() - 400): m.end() + 400]
        online = True if 'aria-label="Online"' in window else None
        seen.add(digits)
        out.append({
            "number": normalize(digits),
            "country_raw": slug.replace("-", " "),
            "platform": "Quackr",
            "platform_slug": "quackr",
            "messages": None,
            "online": online,
            "detail_url": f"http://quackr.io/temporary-numbers/{slug}/{digits}",
            "home": url,
            "needs_login_for_content": True,
        })
    return out


def scrape_wetalk():
    """wetalkapp.com —— WordPress 博文，文章 permalink 里带号码。"""
    url = "https://wetalkapp.com/receive-sms/"
    html = fetch(url)
    out = []
    seen = set()
    for m in re.finditer(
        r'href="https://wetalkapp\.com/[^"]*?-usa-(\d{10,15})/"', html
    ):
        digits = m.group(1)
        if digits in seen:
            continue
        seen.add(digits)
        out.append({
            "number": normalize(digits, "1"),
            "country_raw": "united-states",
            "platform": "WeTalk",
            "platform_slug": "wetalk",
            "messages": None,
            "online": None,
            "detail_url": f"https://wetalkapp.com/receive-sms-online-usa-{digits}/",
            "home": url,
            "needs_login_for_content": False,
        })
    for m in re.finditer(
        r'href="https://wetalkapp\.com/[^"]*?-canada-(\d{10,15})/"', html
    ):
        digits = m.group(1)
        if digits in seen:
            continue
        seen.add(digits)
        out.append({
            "number": normalize(digits, "1"),
            "country_raw": "canada",
            "platform": "WeTalk",
            "platform_slug": "wetalk",
            "messages": None,
            "online": None,
            "detail_url": f"https://wetalkapp.com/receive-sms-online-canada-{digits}/",
            "home": url,
            "needs_login_for_content": False,
        })
    return out


SOURCES = [
    ("Receive-SMS-Online", scrape_receive_sms_online),
    ("Quackr", scrape_quackr),
    ("WeTalk", scrape_wetalk),
]


def run():
    all_rows = []
    report = []
    for name, fn in SOURCES:
        t0 = time.time()
        try:
            rows = fn()
            all_rows.extend(rows)
            report.append({"source": name, "ok": True, "count": len(rows),
                           "seconds": round(time.time() - t0, 1)})
            print(f"[OK]   {name}: {len(rows)} 个号码 ({round(time.time()-t0,1)}s)")
        except Exception as e:
            report.append({"source": name, "ok": False,
                           "error": f"{type(e).__name__}: {e}"})
            print(f"[FAIL] {name}: {type(e).__name__}: {e}")
        time.sleep(random.uniform(1.5, 3.0))

    # 补全国家信息 + 去重
    final, seen = [], set()
    for r in all_rows:
        num = r.get("number")
        if not num or num in seen:
            continue
        seen.add(num)
        zh, flag, cc = country_meta(r["country_raw"])
        r["country"] = zh
        r["flag"] = flag
        r["digits"] = num.lstrip("+")
        final.append(r)

    final.sort(key=lambda x: (x["country"], x["platform"], x["number"]))

    payload = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "total": len(final),
        "sources": report,
        "numbers": final,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    countries = sorted({r["country"] for r in final})
    print(f"\n总计 {len(final)} 个去重号码 / {len(countries)} 个国家: {', '.join(countries)}")
    print(f"已写入 {OUT}")
    return payload


if __name__ == "__main__":
    run()
