#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SMS Hub 采集器 V2
聚合公开第三方平台的临时号码索引。

字段口径（严格遵守，见设计方案第 6 节）：
  - 只写从源站真实抓到的字段，抓不到就写 null，绝不臆造。
  - lastMessageAt：列表页均未提供短信时间，一律 null。不用采集时间冒充。
  - availability：
      verified_online —— 需要真实核验机制，当前三个源均不满足，故不产出。
      recent_activity  —— 源站提供了短信条数（有信息量，但不等于能收短信）。
      unknown          —— 源站无任何可用状态信息。
  - statusEvidence：记录状态判断的文字依据，便于前端展示与后续审计。

合规：只抓公开列表页，不绕登录墙，不抓短信正文，串行+随机延迟，单源失败隔离。
"""

import json
import os
import random
import re
import ssl
import time
import urllib.request
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "data", "numbers.json")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# ISO 两字母 -> (中文名, 国旗, 数字区号)
COUNTRY_ISO = {
    "US": ("美国", "🇺🇸", "1"),
    "GB": ("英国", "🇬🇧", "44"),
    "CA": ("加拿大", "🇨🇦", "1"),
    "AU": ("澳大利亚", "🇦🇺", "61"),
    "DE": ("德国", "🇩🇪", "49"),
    "FR": ("法国", "🇫🇷", "33"),
    "FI": ("芬兰", "🇫🇮", "358"),
    "SE": ("瑞典", "🇸🇪", "46"),
    "NL": ("荷兰", "🇳🇱", "31"),
    "PL": ("波兰", "🇵🇱", "48"),
    "ES": ("西班牙", "🇪🇸", "34"),
    "IN": ("印度", "🇮🇳", "91"),
    "RU": ("俄罗斯", "🇷🇺", "7"),
    "BR": ("巴西", "🇧🇷", "55"),
    "HK": ("中国香港", "🇭🇰", "852"),
    "SG": ("新加坡", "🇸🇬", "65"),
}

# 源站国家名/URL slug -> ISO 两字母
NAME_TO_ISO = {
    "united states": "US", "usa": "US", "us": "US",
    "united kingdom": "GB", "uk": "GB", "great britain": "GB",
    "canada": "CA", "australia": "AU", "germany": "DE", "france": "FR",
    "finland": "FI", "sweden": "SE", "netherlands": "NL", "holland": "NL",
    "poland": "PL", "spain": "ES", "india": "IN", "russia": "RU",
    "brazil": "BR", "hong kong": "HK", "singapore": "SG",
}

ISO_EN = {
    "US": "United States", "GB": "United Kingdom", "CA": "Canada",
    "AU": "Australia", "DE": "Germany", "FR": "France", "FI": "Finland",
    "SE": "Sweden", "NL": "Netherlands", "PL": "Poland", "ES": "Spain",
    "IN": "India", "RU": "Russia", "BR": "Brazil", "HK": "Hong Kong",
    "SG": "Singapore",
}


def norm_key(s):
    s = (s or "").strip().lower()
    s = re.sub(r"[_\-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


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


def to_e164(digits, cc=""):
    d = re.sub(r"\D", "", digits or "")
    if not d:
        return None
    if cc and not d.startswith(cc):
        d = cc + d.lstrip("0")
    return "+" + d


def make_record(*, phone, country_raw, source_id, source_name, source_home,
                detail_url, message_count, availability, status_evidence,
                collected_at):
    key = norm_key(country_raw)
    iso = NAME_TO_ISO.get(key)
    zh, flag, cc = COUNTRY_ISO.get(iso, (country_raw or "未知", "🏳️", ""))
    return {
        "id": f"{source_id}:{(phone or '').lstrip('+')}",
        "phone": phone,
        "countryCode": iso or "XX",
        "countryNameZh": zh,
        "countryNameEn": ISO_EN.get(iso, country_raw or "Unknown"),
        "flag": flag,
        "callingCode": cc,
        "sourceId": source_id,
        "sourceName": source_name,
        "sourceUrl": detail_url,
        "sourceHome": source_home,
        "messageCount": message_count,
        "lastMessageAt": None,          # 列表页未提供，不用采集时间冒充
        "collectedAt": collected_at,
        "availability": availability,
        "statusCheckedAt": collected_at if availability != "unknown" else None,
        "statusEvidence": status_evidence,
        "sourceStatus": "ok",
    }


# ------------------------------------------------------------------ 采集源
def scrape_receive_sms_online(now):
    """
    receive-sms-online.info
    以卡片容器为解析单元（页面里同一个 href 出现两次：号码链接 + Open Messages 按钮，
    从锚点往后取固定长度会取不到状态，必须整卡匹配）。
    卡片含：国旗+国家名、完整号码、SMS 计数、Ready 状态词。
    三个源中唯一同时提供「短信数」和「状态」的。
    """
    url = "https://receive-sms-online.info/"
    html = fetch(url)
    out, seen = [], set()

    card_re = re.compile(
        r'<div class="bg-white rounded-2xl.*?Open Messages\s*</a>', re.S)

    for card in card_re.findall(html):
        num = re.search(r'href="(\d{9,15})-([A-Za-z ]+)"[^>]*>\s*\+(\d{9,15})', card)
        if not num:
            continue
        digits, name = num.group(1), num.group(2).strip()
        if digits in seen:
            continue

        # 页面混用两种计数标签：多数为 "Messages: <span>N</span>"，部分新卡片为 "SMS:" + 独立 span
        cnt = (re.search(r'Messages:\s*<span[^>]*>\s*(\d+)\s*</span>', card)
               or re.search(r'SMS:\s*</span>\s*<span[^>]*>\s*(\d+)\s*</span>', card))
        message_count = int(cnt.group(1)) if cnt else None

        # 状态词前有一个圆点 span：<span class="... bg-blue-500 ..."></span> Ready
        st = re.search(r'bg-(?:blue|green|yellow|red)-\d{3}[^"]*"[^>]*>\s*</span>\s*'
                       r'([A-Za-z][A-Za-z ]*?)\s*</div>', card)
        raw_status = st.group(1).strip() if st else None

        if raw_status and raw_status.lower() in ("ready", "online", "active") \
                and message_count is not None:
            availability = "recent_activity"
            evidence = f"源站列表页标注 {raw_status}，并显示短信 {message_count} 条"
        else:
            availability = "unknown"
            evidence = (f"源站列表页状态：{raw_status}" if raw_status else "源站未提供状态")

        seen.add(digits)
        out.append(make_record(
            phone=to_e164(digits),
            country_raw=name,
            source_id="receive-sms-online",
            source_name="Receive-SMS-Online",
            source_home=url,
            detail_url=f"https://receive-sms-online.info/{digits}-{name.replace(' ', '')}",
            message_count=message_count,
            availability=availability,
            status_evidence=evidence,
            collected_at=now,
        ))
    return out


def scrape_quackr(now):
    """
    quackr.io
    卡片有 aria-label="Online" 图标，完整号码在 permalink 中。
    不提供短信数 —— 在线图标不足以证明能收短信，故 availability=unknown。
    """
    url = "http://quackr.io/"
    html = fetch(url)
    out, seen = [], set()
    for m in re.finditer(r'href="/temporary-numbers/([a-z\-]+)/(\d{9,15})"', html):
        slug, digits = m.group(1), m.group(2)
        if digits in seen:
            continue
        window = html[max(0, m.start() - 500): m.end() + 500]
        if 'aria-label="Online"' in window:
            availability = "unknown"
            evidence = "源站列表页显示 Online 图标，但未提供短信条数"
        else:
            availability = "unknown"
            evidence = "源站未提供状态"
        seen.add(digits)
        out.append(make_record(
            phone=to_e164(digits),
            country_raw=slug.replace("-", " "),
            source_id="quackr",
            source_name="Quackr",
            source_home=url,
            detail_url=f"http://quackr.io/temporary-numbers/{slug}/{digits}",
            message_count=None,
            availability=availability,
            status_evidence=evidence,
            collected_at=now,
        ))
    return out


def scrape_wetalk(now):
    """wetalkapp.com：号码在文章 permalink 中，页面无状态也无短信数。"""
    url = "https://wetalkapp.com/receive-sms/"
    html = fetch(url)
    out, seen = [], set()
    for cc, slug in (("1", "usa"), ("1", "canada")):
        for m in re.finditer(
            rf'href="https://wetalkapp\.com/[^"]*?-{slug}-(\d{{10,15}})/"', html
        ):
            digits = m.group(1)
            if digits in seen:
                continue
            seen.add(digits)
            out.append(make_record(
                phone=to_e164(digits, cc),
                country_raw=slug,
                source_id="wetalk",
                source_name="WeTalk",
                source_home=url,
                detail_url=f"https://wetalkapp.com/receive-sms-online-{slug}-{digits}/",
                message_count=None,
                availability="unknown",
                status_evidence="源站页面未提供状态与短信数",
                collected_at=now,
            ))
    return out


SOURCES = [
    ("receive-sms-online", "Receive-SMS-Online", scrape_receive_sms_online),
    ("quackr", "Quackr", scrape_quackr),
    ("wetalk", "WeTalk", scrape_wetalk),
]


def run():
    now = datetime.now(timezone.utc).astimezone().isoformat()
    all_rows, report = [], []

    for sid, sname, fn in SOURCES:
        t0 = time.time()
        try:
            rows = fn(now)
            all_rows.extend(rows)
            report.append({
                "sourceId": sid, "sourceName": sname, "ok": True,
                "count": len(rows), "seconds": round(time.time() - t0, 1),
            })
            print(f"[OK]   {sname}: {len(rows)} 个号码 ({round(time.time()-t0,1)}s)")
        except Exception as e:
            report.append({
                "sourceId": sid, "sourceName": sname, "ok": False,
                "count": 0, "error": f"{type(e).__name__}: {e}",
            })
            print(f"[FAIL] {sname}: {type(e).__name__}: {e}")
        time.sleep(random.uniform(1.5, 3.0))

    final = [r for r in all_rows if r.get("phone")]
    final.sort(key=lambda x: (-(x["messageCount"] or 0), x["countryNameZh"], x["phone"]))

    unique_phones = {r["phone"] for r in final}
    countries = sorted({r["countryCode"] for r in final if r["countryCode"] != "XX"})

    payload = {
        "generatedAt": now,
        "scheduleNote": "计划每 30 分钟同步一次",
        "totals": {
            "records": len(final),
            "uniquePhones": len(unique_phones),
            "countries": len(countries),
            "sources": len([s for s in report if s["ok"]]),
        },
        "sources": report,
        "numbers": final,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    avail = {}
    for r in final:
        avail[r["availability"]] = avail.get(r["availability"], 0) + 1
    print(f"\n记录 {len(final)} 条 / 去重号码 {len(unique_phones)} 个 / {len(countries)} 个国家")
    print(f"状态分布: {avail}")
    print(f"已写入 {OUT}")
    return payload


if __name__ == "__main__":
    run()
