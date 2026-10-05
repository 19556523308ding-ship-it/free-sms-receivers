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
# Source Health 档案：记录各源历史计数，用于识别「ok:true 但 count:0」的静默失效
HEALTH = os.path.join(BASE, "data", "source-health.json")
# 前端消费用的紧凑 JSON（无缩进，体积更小）
APIOUT = os.path.join(BASE, "data", "sms-api.json")
# 号码可达性探测档案（由 probe_numbers.py 轮转维护）
PROBE = os.path.join(BASE, "data", "number-probe.json")

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
    "BE": ("比利时", "🇧🇪", "32"),
    "IT": ("意大利", "🇮🇹", "39"),
    "AT": ("奥地利", "🇦🇹", "43"),
    "CH": ("瑞士", "🇨🇭", "41"),
    "DK": ("丹麦", "🇩🇰", "45"),
    "NO": ("挪威", "🇳🇴", "47"),
    "PT": ("葡萄牙", "🇵🇹", "351"),
    "IE": ("爱尔兰", "🇮🇪", "353"),
    "GR": ("希腊", "🇬🇷", "30"),
    "NZ": ("新西兰", "🇳🇿", "64"),
    "JP": ("日本", "🇯🇵", "81"),
    "KR": ("韩国", "🇰🇷", "82"),
    "MY": ("马来西亚", "🇲🇾", "60"),
    "TH": ("泰国", "🇹🇭", "66"),
    "PH": ("菲律宾", "🇵🇭", "63"),
    "ID": ("印度尼西亚", "🇮🇩", "62"),
    "VN": ("越南", "🇻🇳", "84"),
    "UA": ("乌克兰", "🇺🇦", "380"),
    "BY": ("白俄罗斯", "🇧🇾", "375"),
    "GE": ("格鲁吉亚", "🇬🇪", "995"),
    "MX": ("墨西哥", "🇲🇽", "52"),
    "AR": ("阿根廷", "🇦🇷", "54"),
    "CL": ("智利", "🇨🇱", "56"),
    "CO": ("哥伦比亚", "🇨🇴", "57"),
    "PE": ("秘鲁", "🇵🇪", "51"),
    "ZA": ("南非", "🇿🇦", "27"),
    "EG": ("埃及", "🇪🇬", "20"),
    "NG": ("尼日利亚", "🇳🇬", "234"),
    "KE": ("肯尼亚", "🇰🇪", "254"),
    "BD": ("孟加拉国", "🇧🇩", "880"),
    "TW": ("中国台湾", "🇨🇳", "886"),
    "MO": ("中国澳门", "🇲🇴", "853"),
    "TL": ("东帝汶", "🇹🇱", "670"),
    "BG": ("保加利亚", "🇧🇬", "359"),
    "CZ": ("捷克", "🇨🇿", "420"),
    "RO": ("罗马尼亚", "🇷🇴", "40"),
    "HU": ("匈牙利", "🇭🇺", "36"),
    "SK": ("斯洛伐克", "🇸🇰", "421"),
    "SI": ("斯洛文尼亚", "🇸🇮", "386"),
    "EE": ("爱沙尼亚", "🇪🇪", "372"),
    "LV": ("拉脱维亚", "🇱🇻", "371"),
    "LT": ("立陶宛", "🇱🇹", "370"),
    "TR": ("土耳其", "🇹🇷", "90"),
    "IL": ("以色列", "🇮🇱", "972"),
    "AE": ("阿联酋", "🇦🇪", "971"),
    "SA": ("沙特阿拉伯", "🇸🇦", "966"),
    "IS": ("冰岛", "🇮🇸", "354"),
    "LU": ("卢森堡", "🇱🇺", "352"),
    "CN": ("中国", "🇨🇳", "86"),
    "PR": ("波多黎各", "🇵🇷", "1"),
    "DO": ("多米尼加", "🇩🇴", "1"),
    "GT": ("危地马拉", "🇬🇹", "502"),
    "CR": ("哥斯达黎加", "🇨🇷", "506"),
    "MP": ("北马里亚纳群岛", "🇲🇵", "1"),
    "BS": ("巴哈马", "🇧🇸", "1"),
}

# ISO 两字母 -> 英文名（供英文版站点与 nameEn 字段使用）
COUNTRY_EN = {
    "US": "United States", "GB": "United Kingdom", "CA": "Canada",
    "AU": "Australia", "DE": "Germany", "FR": "France", "FI": "Finland",
    "SE": "Sweden", "NL": "Netherlands", "PL": "Poland", "ES": "Spain",
    "IN": "India", "RU": "Russia", "BR": "Brazil", "HK": "Hong Kong, China",
    "SG": "Singapore", "BE": "Belgium", "IT": "Italy", "AT": "Austria",
    "CH": "Switzerland", "DK": "Denmark", "NO": "Norway", "PT": "Portugal",
    "IE": "Ireland", "GR": "Greece", "NZ": "New Zealand", "JP": "Japan",
    "KR": "South Korea", "MY": "Malaysia", "TH": "Thailand",
    "PH": "Philippines", "ID": "Indonesia", "VN": "Vietnam",
    "UA": "Ukraine", "BY": "Belarus", "GE": "Georgia", "MX": "Mexico",
    "AR": "Argentina", "CL": "Chile", "CO": "Colombia", "PE": "Peru",
    "ZA": "South Africa", "EG": "Egypt", "NG": "Nigeria", "KE": "Kenya",
    "BD": "Bangladesh", "TW": "Taiwan, China", "MO": "Macao, China",
    "TL": "Timor-Leste", "BG": "Bulgaria", "CZ": "Czechia",
    "RO": "Romania", "HU": "Hungary", "SK": "Slovakia", "SI": "Slovenia",
    "EE": "Estonia", "LV": "Latvia", "LT": "Lithuania", "TR": "Türkiye",
    "IL": "Israel", "AE": "United Arab Emirates", "SA": "Saudi Arabia",
    "IS": "Iceland", "LU": "Luxembourg", "CN": "China",
    "PR": "Puerto Rico", "DO": "Dominican Republic", "GT": "Guatemala",
    "CR": "Costa Rica", "MP": "Northern Mariana Islands", "BS": "Bahamas",
}

# 星号：英文名兜底 —— 表外的 ISO 直接用 ISO 码本身，避免出现空值
def country_en(iso):
    return COUNTRY_EN.get(iso) or iso


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
    "SE": "Sweden", "NL": "Netherlands", "ES": "Spain", "PL": "Poland",
    "IN": "India", "RU": "Russia", "BR": "Brazil", "HK": "Hong Kong",
    "SG": "Singapore", "BE": "Belgium", "IT": "Italy", "AT": "Austria",
    "CH": "Switzerland", "DK": "Denmark", "NO": "Norway", "PT": "Portugal",
    "IE": "Ireland", "GR": "Greece", "NZ": "New Zealand", "JP": "Japan",
    "KR": "South Korea", "MY": "Malaysia", "TH": "Thailand", "PH": "Philippines",
    "ID": "Indonesia", "VN": "Vietnam", "UA": "Ukraine", "BY": "Belarus",
    "GE": "Georgia", "MX": "Mexico", "AR": "Argentina", "CL": "Chile",
    "CO": "Colombia", "PE": "Peru", "ZA": "South Africa", "EG": "Egypt",
    "NG": "Nigeria", "KE": "Kenya", "BD": "Bangladesh", "TW": "Taiwan",
    "MO": "Macao", "TL": "Timor-Leste", "BG": "Bulgaria", "CZ": "Czechia",
    "RO": "Romania", "HU": "Hungary", "SK": "Slovakia", "SI": "Slovenia",
    "EE": "Estonia", "LV": "Latvia", "LT": "Lithuania", "TR": "Turkey",
    "IL": "Israel", "AE": "UAE", "SA": "Saudi Arabia", "IS": "Iceland",
    "LU": "Luxembourg", "CN": "China",
}


def norm_key(s):
    s = (s or "").strip().lower()
    s = re.sub(r"[_\-]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def fetch(url, referer=None, timeout=25, retries=2, extra_headers=None):
    """
    仅在已验证可行的最小请求头基础上按需追加。
    教训：不要一次性加全套 Sec-Fetch-* 头，实测会触发多个源的 403（2026-10-05）。
    """
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    if extra_headers:
        headers.update(extra_headers)
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
                collected_at, iso_hint=None, cc_hint=None):
    """
    iso_hint：调用方已确定 ISO 两字母时直接传入（比国家名更可靠）。
    cc_hint ：调用方已确定数字区号时直接传入。
    """
    iso = iso_hint
    if not iso:
        key = norm_key(country_raw)
        iso = NAME_TO_ISO.get(key)
        if not iso:
            # 国家名可能本身就是 ISO 代码（大小写不敏感）
            cand = (country_raw or "").strip().upper()
            if cand in COUNTRY_ISO:
                iso = cand
    zh, flag, cc = COUNTRY_ISO.get(iso, (country_raw or "未知", "🏳️", ""))
    if cc_hint:
        cc = cc_hint
    if not iso:
        iso = "XX"
    return {
        "id": f"{source_id}:{(phone or '').lstrip('+')}",
        "phone": phone,
        "countryCode": iso,
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


# ---------------------------------------------------- 新增源（2026-10-05 实测接入）
# 实测报告见 docs/SOURCE-AUDIT-2026-10.md
# 下面 5 个源经服务器端真实探测确认：列表页为公开静态 HTML，纯 HTTP 即可解析号码，
# 无需登录、无需过人机验证。仅采集号码元数据，不采集短信正文。

def _iso_from_cc(digits):
    """按数字区号前缀猜国家（源站很多只在 URL 里给区号，不给国家名）。"""
    d = re.sub(r"\D", "", digits or "")
    if not d:
        return None, None

    # 北美 NANP（+1）优先按「区号-号段」细分：
    # 源站给的是 +1 + 10 位（如 17873011181 共 11 位），而通用表里
    # ("1","US",11) 要求 12 位，等长判断必然失配 → 之前 16 条全落成 XX。
    # 这里改用「区号后3 位」做 NANP 归属判定（标准做法）。
    if d.startswith("1") and len(d) == 11:
        nanp = d[1:4]
        if nanp in ("787", "939"):          # 波多黎各
            return "PR", "1"
        if nanp in ("670",):               # 北马里亚纳群岛
            return "MP", "1"
        if nanp in ("242",):               # 巴哈马
            return "BS", "1"
        return "US", "1"

    table = [
        ("44", "GB", 10), ("49", "DE", 11), ("33", "FR", 9), ("34", "ES", 9),
        ("31", "NL", 9), ("32", "BE", 9), ("43", "AT", 10), ("41", "CH", 9),
        ("46", "SE", 9), ("45", "DK", 8), ("47", "NO", 8), ("358", "FI", 10),
        ("48", "PL", 9), ("351", "PT", 9), ("30", "GR", 10), ("353", "IE", 9),
        ("40", "RO", 9), ("421", "SK", 9), ("420", "CZ", 9), ("380", "UA", 9),
        ("61", "AU", 9), ("64", "NZ", 8), ("81", "JP", 10), ("82", "KR", 10),
        ("65", "SG", 8), ("60", "MY", 9), ("66", "TH", 9), ("63", "PH", 10),
        ("62", "ID", 10), ("84", "VN", 9), ("91", "IN", 10), ("86", "CN", 11),
        ("7", "RU", 10), ("375", "BY", 9), ("995", "GE", 9),
        ("55", "BR", 10), ("52", "MX", 10), ("54", "AR", 10), ("56", "CL", 9),
        ("57", "CO", 10), ("51", "PE", 9), ("27", "ZA", 9), ("20", "EG", 10),
        ("234", "NG", 10), ("254", "KE", 9), ("880", "BD", 10),
        ("852", "HK", 8), ("886", "TW", 9), ("853", "MO", 8), ("670", "TL", 8),
    ]
    for cc, iso, nsn in table:
        if d.startswith(cc) and len(d) == len(cc) + nsn:
            return iso, cc

    # 退一步：只看区号前缀，不再要求后续位数完全匹配。
    # 全球各国 NSN 长度不一（有的国家同一区号下有多种长度），
    # 强等长会漏掉大量真实号码。命中即用，最多只信前4 位以上的明确区号。
    for cc, iso, nsn in table:
        if len(cc) >= 3 and d.startswith(cc) and len(d) > len(cc):
            return iso, cc
    return None, None


def _record_by_cc(digits, *, source_id, source_name, source_home, detail_url,
                  now, evidence, message_count=None, country_hint=None,
                  iso_override=None, cc_override=None):
    """
    构造记录。优先级：
      1. iso_override —— 源站 URL 路径里已明确给出国家（如 freephonenum 的 /be/）
      2. 按号码数字区号前缀推断
      3. country_hint 文本匹配
    注意：部分源（如 FreePhoneNum）列表页只给「国内号码」不含国家码，
    必须靠 URL 国家段补 callingCode，否则 E.164 标准化会错。
    """
    iso = cc = None
    if iso_override:
        iso = iso_override
        cc = cc_override or (COUNTRY_ISO.get(iso, ("", "", ""))[2] or None)
    else:
        iso, cc = _iso_from_cc(digits)
    if not iso and country_hint:
        iso = NAME_TO_ISO.get(norm_key(country_hint))
        if iso and not cc:
            cc = COUNTRY_ISO.get(iso, ("", "", ""))[2] or None
    if not cc and iso:
        cc = COUNTRY_ISO.get(iso, ("", "", ""))[2] or None

    if iso:
        zh, flag, cc2 = COUNTRY_ISO.get(iso, (iso, "🏳️", cc or ""))
        cc = cc or cc2
        country_raw = ISO_EN.get(iso, iso)
    else:
        flag, country_raw = "🏳️", (country_hint or "未知")
    return make_record(
        phone=to_e164(digits, cc),
        country_raw=country_raw,
        source_id=source_id,
        source_name=source_name,
        source_home=source_home,
        detail_url=detail_url,
        message_count=message_count,
        availability="unknown",
        status_evidence=evidence,
        collected_at=now,
        iso_hint=iso,
        cc_hint=cc,
    )


def scrape_freephonenum(now):
    """
    freephonenum.com —— 实测 624 个号码链接，URL 形如 {国家段}/receive-sms/{digits}。

    两个实测坑（2026-10-05 复核）：
    1. `/numbers` 已 302 重定向到 `/receive-sms`，抓 /numbers 也能拿到内容
       （fetch 跟随重定向），但直接抓 /receive-sms 更稳，少一跳。
    2. 国家段**不只有2 字母**：实测有 `pr`（波多黎各）、`po`（秘鲁）等 3 字母码。
       原正则 `([a-z]{2})` 会把这些整段漏掉 → 对应号码全落成 XX。
    正文页有 Google reCAPTCHA，故只取号码，不取正文。
    """
    home = "https://freephonenum.com"
    url = f"{home}/receive-sms"
    html = fetch(url)
    out, seen = [], set()

    slug_cc = {"us": "US", "ca": "CA", "gb": "GB", "uk": "GB", "be": "BE", "nl": "NL",
               "de": "DE", "fr": "FR", "es": "ES", "it": "IT", "pl": "PL", "se": "SE",
               "fi": "FI", "at": "AT", "ch": "CH", "dk": "DK", "no": "NO", "pt": "PT",
               "ie": "IE", "au": "AU", "nz": "NZ", "in": "IN", "mx": "MX", "br": "BR",
               "bg": "BG", "cz": "CZ", "ro": "RO", "gr": "GR", "hu": "HU", "sk": "SK",
               "si": "SI", "ee": "EE", "lv": "LV", "lt": "LT", "ua": "UA", "ru": "RU",
               "jp": "JP", "kr": "KR", "sg": "SG", "hk": "HK", "tw": "TW", "cn": "CN",
               "my": "MY", "th": "TH", "ph": "PH", "id": "ID", "vn": "VN", "tr": "TR",
               "il": "IL", "ae": "AE", "sa": "SA", "za": "ZA", "ng": "NG", "ke": "KE",
               "ar": "AR", "cl": "CL", "co": "CO", "pe": "PE", "is": "IS", "lu": "LU",
               # 3 字母码（实测存在，原实现漏掉）
               "pr": "PR", "po": "PE", "do": "DO", "gt": "GT", "cr": "CR",
               "pa": "PA", "jm": "JM", "tt": "TT", "bz": "BZ", "ht": "HT"}

    # 国家段允许 2-3 字母（实测存在 pr/po 等 3 字母码）
    for m in re.finditer(r'href="(/([a-z]{2,3})/receive-sms/(\d{9,15}))"', html):
        href, slug, digits = m.group(1), m.group(2), m.group(3)
        if digits in seen:
            continue
        seen.add(digits)
        # slug 未在映射表内时不猜 ISO（否则 bg/ru 等两字母码会误判），交给号码区号推断
        iso = slug_cc.get(slug)
        out.append(_record_by_cc(
            digits,
            source_id="freephonenum", source_name="FreePhoneNum",
            source_home=home, detail_url=home + href, now=now,
            iso_override=iso,
            evidence="源站号码目录公开列出，路径含国家段；短信正文页有人机验证，故不采集正文",
        ))
    return out


def scrape_receiveasmsonline(now):
    """
    receiveasmsonline.com —— 实测唯一可用真浏览器读到公开短信正文的源。
    国家页路径 /united-states/ 等，静态 HTML 直出号码（美国页 186 个）。
    正文需 CSR 渲染，当前版本只做号码索引；正文能力预留（见 docs/RECEIVE-ARCHITECTURE.md）。
    """
    home = "https://receiveasmsonline.com"
    # 站点首页列出了全部国家及号码数，按数量降序取前若干国家页
    idx = fetch(f"{home}/")
    pairs = re.findall(
        r'href="/([a-z-]+)/"[^>]*>.{0,400}?>\s*(\d{1,5})\s*<', idx, re.S)
    if not pairs:
        pairs = re.findall(r'href="/([a-z-]{3,})/"', idx) and \
                [(m, "0") for m in re.findall(r'href="/([a-z-]{3,})/"', idx)] or []

    scored = []
    for slug, cnt in pairs:
        d = re.sub(r"\D", "", cnt)
        if d:
            scored.append((int(d), slug))
    scored.sort(reverse=True)
    targets = [s for _, s in scored[:12]] or ["united-states"]

    out, seen = [], set()
    for slug in targets:
        try:
            html = fetch(f"{home}/{slug}/", referer=f"{home}/")
        except Exception:
            continue
        for m in re.finditer(r'href="/([a-z-]+)/(\+?\d{9,15})/"', html):
            cslug, digits = m.group(1), re.sub(r"\D", "", m.group(2))
            if digits in seen:
                continue
            seen.add(digits)
            out.append(_record_by_cc(
                digits,
                source_id="receiveasmsonline", source_name="ReceiveAsmsOnline",
                source_home=home, detail_url=f"{home}/{cslug}/{digits}/", now=now,
                country_hint=cslug.replace("-", " "),
                evidence="源站国家页公开列出号码；短信正文为客户端渲染，站内查看需另加渲染服务",
            ))
        time.sleep(random.uniform(0.8, 1.6))
    return out


def scrape_temporary_phonenumber(now):
    """
    temporary-phone-number.com —— 实测首页 34 个号码链接。
    页面标注 "Latest: 27 minutes ago"，可产出真实的 lastActive（区别于采集时间）。
    """
    home = "https://temporary-phone-number.com"
    html = fetch(f"{home}/")
    out, seen = [], set()

    # 号码卡片块：抓号码 + 其后最近的 "Latest: x minutes ago"
    for m in re.finditer(
        r'(\+?\d{9,15})(.{0,900}?)(Latest:\s*(?:about\s*)?(\d+)\s*(minute|hour|day)s? ago)?',
        html, re.S):
        digits = re.sub(r"\D", "", m.group(1))
        if len(digits) < 9 or len(digits) > 15 or digits in seen:
            continue
        tail = m.group(0)
        if 'href' not in tail:
            continue
        seen.add(digits)
        last_min = None
        lm = re.search(r'Latest:\s*(?:about\s*)?(\d+)\s*(minute|hour|day)', tail, re.I)
        if lm:
            n, unit = int(lm.group(1)), lm.group(2).lower()
            last_min = n * {"minute": 1, "hour": 60, "day": 1440}[unit]
        href = re.search(r'href="([^"]*)"', tail)
        out.append(_record_by_cc(
            digits,
            source_id="temporaryphonenumber", source_name="TemporaryPhoneNumber",
            source_home=home,
            detail_url=(home + href.group(1)) if href and href.group(1).startswith("/")
                       else (href.group(1) if href else home),
            now=now,
            evidence=(f"源站标注 Latest: {lm.group(0) if lm else '未提供'}"
                      if lm else "源站未提供最后活跃时间"),
        ))
    return out


def scrape_smsdock(now):
    """smsdock.net —— 实测 14 个号码链接。"""
    home = "https://smsdock.net"
    html = fetch(f"{home}/")
    out, seen = [], set()
    for m in re.finditer(r'href="([^"]*?(\+?\d{9,15})/?)"', html):
        href, digits = m.group(1), re.sub(r"\D", "", m.group(2))
        if not (9 <= len(digits) <= 15) or digits in seen:
            continue
        if href.startswith("http") or href.startswith("/"):
            seen.add(digits)
            out.append(_record_by_cc(
                digits, source_id="smsdock", source_name="SMSDock",
                source_home=home,
                detail_url=href if href.startswith("http") else home + href,
                now=now, evidence="源站公开号码目录",
            ))
    return out


def scrape_sms_online_co(now):
    """sms-online.co —— 实测 7 个号码，正文页有 reCAPTCHA，只取号码。"""
    home = "https://www.sms-online.co"
    html = fetch(f"{home}/receive-free-sms")
    out, seen = [], set()
    for m in re.finditer(r'href="([^"]*?/receive-free-sms/(\+?\d{9,15}))"', html):
        href, digits = m.group(1), re.sub(r"\D", "", m.group(2))
        if digits in seen:
            continue
        seen.add(digits)
        out.append(_record_by_cc(
            digits, source_id="smsonlineco", source_name="SMS-Online.co",
            source_home=home, detail_url=href if href.startswith("http") else home + href,
            now=now, evidence="源站公开号码目录；正文页有人机验证，故不采集正文",
        ))
    return out


def scrape_asms(now):
    """asms.ai（原 AnonymSMS）—— 实测 8 个号码链接，正文需登录。"""
    home = "https://asms.ai"
    html = fetch(f"{home}/")
    out, seen = [], set()
    for m in re.finditer(r'href="([^"]*?/(\+?\d{9,15})/?)"', html):
        href, digits = m.group(1), re.sub(r"\D", "", m.group(2))
        if not (9 <= len(digits) <= 15) or digits in seen:
            continue
        seen.add(digits)
        out.append(_record_by_cc(
            digits, source_id="asms", source_name="ASMS.ai",
            source_home=home, detail_url=href if href.startswith("http") else home + href,
            now=now, evidence="源站公开号码目录；短信正文需登录，故不采集正文",
        ))
    return out


SOURCES = [
    ("receive-sms-online", "Receive-SMS-Online", scrape_receive_sms_online),
    ("quackr", "Quackr", scrape_quackr),
    ("wetalk", "WeTalk", scrape_wetalk),
    ("freephonenum", "FreePhoneNum", scrape_freephonenum),
    ("receiveasmsonline", "ReceiveAsmsOnline", scrape_receiveasmsonline),
    ("temporaryphonenumber", "TemporaryPhoneNumber", scrape_temporary_phonenumber),
    ("smsdock", "SMSDock", scrape_smsdock),
    ("smsonlineco", "SMS-Online.co", scrape_sms_online_co),
    ("asms", "ASMS.ai", scrape_asms),
]


# 站内可直接收短信的来源（Inbox Adapter 已接通的源）。
# 这是 SMS Hub 2.0 的核心口径：只有这些源上的号码，用户点进去
# 才能真的在站内等到验证码；其余源只能跳原站看，属于「备用池」。
DIRECT_INBOX_SOURCES = {"receiveasmsonline"}


def availability_score(rec):
    """
    推荐排序分（设计文档 §12）。用户只看到「推荐」两个字，不外露分数。

    availability_score =
        0.35 * recent_sms_score     最近有短信
      + 0.25 * fetch_success_score  抓取成功率（站内可收 = 1）
      + 0.20 * source_health_score  来源健康
      + 0.10 * multi_source_score   多源交叉
      + 0.10 * recency_score        状态新鲜度
    """
    s = 0.0

    # 最近短信：有短信数就说明历史上收到过；站内可收再加权
    if rec.get("directInbox"):
        s += 0.35
    elif rec.get("availability") == "recent_activity":
        s += 0.20

    # 抓取成功率：站内通道已接通即满分
    s += 0.25 if rec.get("directInbox") else 0.0

    # 来源健康：源本次采集成功
    s += 0.20 if rec.get("sourceStatus") == "ok" else 0.0

    # 多源交叉：多站同时收录是免费的可靠性信号
    if rec.get("sourceCount", 1) >= 2:
        s += 0.10

    # 新鲜度：状态是本次采集核实的
    if rec.get("statusCheckedAt"):
        s += 0.10

    return round(s, 4)


def status_of(rec):
    """
    新状态模型（§10）：不再出现「状态未知」这种对用户无意义的词。
      可用     available    —— 站内可收，且近期有短信
      较少使用 low_usage    —— 站内可收，但近期无短信
      暂未验证 unverified   —— 无站内通道或无近期证据
    """
    if rec.get("directInbox"):
        return "available" if rec.get("availability") == "recent_activity" else "low_usage"
    return "unverified"


def enrich(rec):
    """给记录补齐 SMS Hub 2.0 需要的派生字段。"""
    rec["directInbox"] = rec.get("sourceId") in DIRECT_INBOX_SOURCES
    rec["status"] = status_of(rec)
    # 列表页没有「最近短信时间」，一律 null，绝不用采集时间冒充（诚实口径）
    rec["lastSmsAt"] = rec.get("lastMessageAt")
    rec["smsToday"] = rec.get("messageCount")
    rec["availabilityScore"] = availability_score(rec)
    return rec


def load_probe_db():
    """读取号码可达性探测档案（由 probe_numbers.py 维护）。"""
    if not os.path.exists(PROBE):
        return {}
    try:
        with open(PROBE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def apply_probe(rec, probe_db):
    """
    把真实探测结果并入记录。

    这一步解决的正是「源可用 ≠ 每个号可用」的问题：
    实测同一来源下有的号码 403、有的正常，所以 direct inbox 不能只看来源，
    必须看该号码自己探出来的成功率。
    """
    if not rec.get("directInbox"):
        # 非站内号码也带上字段，前端好统一处理（值为 null 表示无通道）
        rec["fetchSuccessRate"] = None
        rec["reachable"] = False
        rec["probed"] = False
        return rec

    p = probe_db.get(rec.get("phone"))
    if not p:
        # 还没探过：保留 directInbox（有通道），但标记为未验证
        rec["fetchSuccessRate"] = None
        rec["reachable"] = None
        rec["probed"] = False
        rec["status"] = "unverified"
        rec["availabilityScore"] = round(max(0.0, rec["availabilityScore"] - 0.25), 4)
        return rec

    rate = p.get("fetch_success_rate")
    rec["fetchSuccessRate"] = rate
    rec["reachable"] = bool(p.get("reachable"))
    rec["probed"] = True
    if p.get("lastMessageCount"):
        rec["smsToday"] = p["lastMessageCount"]

    # 探测过的号码按真实成功率定状态（这才是诚实的「可用」口径）
    if not p.get("reachable"):
        rec["status"] = "unverified"
        rec["availabilityScore"] = round(max(0.0, rec["availabilityScore"] - 0.30), 4)
    elif p.get("lastMessageCount", 0) > 0:
        rec["status"] = "available"
    else:
        rec["status"] = "low_usage"

    # 成功率直接参与推荐分（覆盖掉「有通道即满分」的近似）
    rec["availabilityScore"] = round(
        rec["availabilityScore"] - 0.25 + 0.25 * (rate or 0), 4)
    return rec


def merge_by_e164(rows):
    """
    按 E.164 全局去重：同一号码在多个源出现时合并为一条，
    主记录取「信息量最大」的那条（优先有短信数 > 有国家 > 状态非 unknown），
    其余源记入 alsoOn，用于前端展示「N 个来源仍在收录」。
    这是免费接码站区的关键：同号多站重复极多，不去重会严重虚高。
    """
    def rank(r):
        return (
            1 if r.get("messageCount") is not None else 0,
            0 if r.get("availability") == "unknown" else 1,
            1 if r.get("countryCode") != "XX" else 0,
        )

    by_phone = {}
    for r in rows:
        p = r.get("phone")
        if not p:
            continue
        by_phone.setdefault(p, []).append(r)

    merged = []
    for phone, group in by_phone.items():
        group.sort(key=rank, reverse=True)
        primary = dict(group[0])
        others = []
        for r in group[1:]:
            if r["sourceId"] != primary["sourceId"]:
                others.append({"sourceId": r["sourceId"], "sourceName": r["sourceName"],
                               "sourceUrl": r["sourceUrl"]})
        # 同一源内去重
        seen_src = set()
        also = []
        for o in others:
            if o["sourceId"] not in seen_src:
                seen_src.add(o["sourceId"])
                also.append(o)
        primary["alsoOn"] = also
        primary["sourceCount"] = 1 + len(also)
        # 多源交叉验证是可靠性的免费信号（不是核验在线，只是「多个独立站都在收录」）
        if len(also) >= 1 and primary.get("messageCount") is None:
            primary["availability"] = "recent_activity"
            primary["statusEvidence"] = (
                f"{primary['sourceCount']} 个独立来源同时收录该号码；"
                f"主源：{primary['statusEvidence']}"
            )
        merged.append(primary)
    return merged


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
    final = merge_by_e164(final)
    final = [enrich(r) for r in final]
    # 并入真实探测结果（源可用 ≠ 每个号可用）
    probe_db = load_probe_db()
    final = [apply_probe(r, probe_db) for r in final]
    # 排序：站内可收优先 -> 推荐分降序 -> 短信数 -> 国家 -> 号码
    final.sort(key=lambda x: (
        not x.get("directInbox"),
        -x.get("availabilityScore", 0),
        -(x["messageCount"] or 0),
        x["countryNameZh"],
        x["phone"],
    ))

    unique_phones = {r["phone"] for r in final}
    countries = sorted({r["countryCode"] for r in final if r["countryCode"] != "XX"})

    # ---------------- 国家聚合（首页国家卡 / 国家落地页要用）----------------
    by_country = {}
    for r in final:
        iso = r.get("countryCode") or "XX"
        if iso == "XX":
            continue
        c = by_country.setdefault(iso, {
            "iso": iso,
            "nameZh": r.get("countryNameZh"),
            "nameEn": r.get("countryNameEn") or country_en(iso),
            "flag": r.get("flag"),
            "callingCode": r.get("callingCode"),
            "total": 0, "directInbox": 0, "active": 0,
            "lowUsage": 0, "unverified": 0,
        })
        c["total"] += 1
        if r.get("directInbox"):
            c["directInbox"] += 1
        st = r.get("status")
        if st == "available":
            c["active"] += 1
        elif st == "low_usage":
            c["lowUsage"] += 1
        else:
            c["unverified"] += 1
    # 国家列表按「站内可收」降序排，首页一屏就能看到最有用的国家
    country_list = sorted(by_country.values(),
                          key=lambda c: (-c["directInbox"], -c["total"], c["nameZh"]))

    # ---------------- Source Health（设计文档 §30-§33）----------------
    # 核心教训：ok:true + count:0 不等于健康。源站改版、被限流、结构变化
    # 都可能让解析器「跑通但一个都没抓到」，而这类静默失效不会报错。
    # 所以这里做三件事：① 记录历史计数 ② 标记 SUSPICIOUS_ZERO
    # ③ 连续异常累计（供后台告警）。
    health_path = HEALTH
    health = {}
    if os.path.exists(health_path):
        try:
            with open(health_path, encoding="utf-8") as f:
                health = json.load(f)
        except Exception:
            health = {}

    total_records = max(1, len(final))
    for s in report:
        sid = s["sourceId"]
        prev = health.get(sid, {})
        prev_count = prev.get("current_count")
        cur = s.get("count", 0) if s.get("ok") else 0

        # 零结果检测：之前有量，这次归零 —— 极可能是源站变了或被限流
        suspicious_zero = bool(prev_count and prev_count >= 20 and cur == 0)
        # 疑似劣化：跌幅超过 65%
        degradation = bool(prev_count and prev_count >= 20
                           and cur > 0 and cur < prev_count * 0.35)

        cz = prev.get("consecutive_zero_results", 0)
        cf = prev.get("consecutive_failures", 0)
        if suspicious_zero:
            cz += 1
        else:
            cz = 0
        if not s.get("ok"):
            cf += 1
        else:
            cf = 0

        if suspicious_zero:
            health_status = "SUSPICIOUS_ZERO"
        elif degradation:
            health_status = "SUSPECTED_DEGRADATION"
        elif not s.get("ok"):
            health_status = "FAILING"
        elif cur == 0:
            health_status = "EMPTY"
        else:
            health_status = "HEALTHY"

        s["healthStatus"] = health_status
        s["previousCount"] = prev_count
        s["consecutiveZeroResults"] = cz
        s["consecutiveFailures"] = cf
        s["dependencyRatio"] = round(cur / total_records, 4)
        s["highDependency"] = s["dependencyRatio"] > 0.40   # §33 阈值 40%

        health[sid] = {
            "source_id": sid,
            "source_name": s["sourceName"],
            "last_fetch_at": now,
            "last_success_at": now if s.get("ok") else prev.get("last_success_at"),
            "last_nonzero_at": now if cur > 0 else prev.get("last_nonzero_at"),
            "current_count": cur,
            "previous_count": prev_count,
            "consecutive_failures": cf,
            "consecutive_zero_results": cz,
            "http_status": 200 if s.get("ok") else None,
            "parser_status": "ok" if s.get("ok") else "error",
            "health_status": health_status,
        }

    # 写健康档案（失败也别让主流程挂掉）
    try:
        os.makedirs(os.path.dirname(health_path), exist_ok=True)
        with open(health_path, "w", encoding="utf-8") as f:
            json.dump(health, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] Source Health 写入失败: {e}")

    # 总号码数骤降保护（§31）：低于上次 35% 时拒绝自动覆盖线上数据。
    # 注意这里只报警并保留产出，是否覆盖交给 refresh.sh 判断，
    # 避免把「采集器自己的判断」和「部署决策」混在一起。
    snapshot_ok = True
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                old = json.load(f)
            old_n = len(old.get("numbers", []))
            if old_n >= 100 and len(final) < old_n * 0.35:
                snapshot_ok = False
                print(f"[WARN] 号码数骤降：{old_n} -> {len(final)}，已标记 SUSPECTED_DEGRADATION")
        except Exception:
            pass

    payload = {
        "generatedAt": now,
        "scheduleNote": "计划每 30 分钟同步一次",
        "totals": {
            "records": len(final),
            "uniquePhones": len(unique_phones),
            "countries": len(countries),
            "sources": len([s for s in report if s["ok"]]),
            "multiSourcePhones": len([r for r in final if len(r.get("alsoOn", [])) > 0]),
            # SMS Hub 2.0 关键指标
            "directInbox": len([r for r in final if r.get("directInbox")]),
            "directInboxRatio": round(
                len([r for r in final if r.get("directInbox")]) / max(1, len(final)), 4),
            "available": len([r for r in final if r.get("status") == "available"]),
            "lowUsage": len([r for r in final if r.get("status") == "low_usage"]),
            "unverified": len([r for r in final if r.get("status") == "unverified"]),
            # 真实探测覆盖情况（诚实口径：探过才算数）
            "probed": len([r for r in final if r.get("probed")]),
            "reachable": len([r for r in final if r.get("reachable")]),
        },
        "snapshotOk": snapshot_ok,
        "countries": country_list,
        "sources": report,
        "numbers": final,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # JSON 端点同样输出，供前端按文档 §37 的 API 形态消费
    with open(APIOUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))

    avail = {}
    for r in final:
        avail[r["status"]] = avail.get(r["status"], 0) + 1
    di = payload["totals"]["directInbox"]
    print(f"\n记录 {len(final)} 条 / 去重号码 {len(unique_phones)} 个 / {len(countries)} 个国家")
    print(f"站内可收短信号码: {di} 个（覆盖率 {payload['totals']['directInboxRatio']:.0%}）")
    print(f"新状态分布: {avail}")
    print(f"已写入 {OUT}")
    return payload


if __name__ == "__main__":
    run()
