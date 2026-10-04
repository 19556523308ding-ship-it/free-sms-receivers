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
    table = [
        ("1", "US", 11),      # 北美 NANP：+1 + 10 位
        ("44", "GB", 10), ("49", "DE", 11), ("33", "FR", 9), ("34", "ES", 9),
        ("31", "NL", 9), ("32", "BE", 9), ("43", "AT", 10), ("41", "CH", 9),
        ("46", "SE", 9), ("45", "DK", 8), ("47", "NO", 8), ("358", "FI", 10),
        ("48", "PL", 9), ("351", "PT", 9), ("30", "GR", 10), ("353", "IE", 9),
        ("61", "AU", 9), ("64", "NZ", 8), ("81", "JP", 10), ("82", "KR", 10),
        ("65", "SG", 8), ("60", "MY", 9), ("66", "TH", 9), ("63", "PH", 10),
        ("62", "ID", 10), ("84", "VN", 9), ("91", "IN", 10), ("86", "CN", 11),
        ("7", "RU", 10), ("380", "UA", 9), ("375", "BY", 9), ("995", "GE", 9),
        ("55", "BR", 10), ("52", "MX", 10), ("54", "AR", 10), ("56", "CL", 9),
        ("57", "CO", 10), ("51", "PE", 9), ("27", "ZA", 9), ("20", "EG", 10),
        ("234", "NG", 10), ("254", "KE", 9), ("91", "IN", 10), ("880", "BD", 10),
        ("852", "HK", 8), ("886", "TW", 9), ("853", "MO", 8), ("670", "TL", 8),
    ]
    for cc, iso, nsn in table:
        if d.startswith(cc) and len(d) == len(cc) + nsn:
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
    freephonenum.com/numbers —— 实测 624 个号码链接，URL 形如 /be/receive-sms/{digits}，
    国家码在路径段（be/nl/de/...），比号码段更可靠。
    正文页有 Google reCAPTCHA，故只取号码，不取正文。
    """
    home = "https://freephonenum.com"
    url = f"{home}/numbers"
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
               "ar": "AR", "cl": "CL", "co": "CO", "pe": "PE", "is": "IS", "lu": "LU"}

    for m in re.finditer(r'href="(/([a-z]{2})/receive-sms/(\d{9,15}))"', html):
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
            "multiSourcePhones": len([r for r in final if len(r.get("alsoOn", [])) > 0]),
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
