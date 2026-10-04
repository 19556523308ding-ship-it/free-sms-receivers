#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMS Hub 数据源实测审计 —— 服务器端执行
对每个源输出：HTTP状态 / 反爬拦截 / 渲染方式 / 号码可解析数 / 详情页正文可读性 / robots许可
只读公开页面，不绕登录墙、不破验证码、不做高频请求。
产出：source_audit.json
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# 全局节流：同域最小间隔，避免把人家站点打挂
_MIN_GAP = {"_last": {}}
_GAP = 1.2


def _throttle(host):
    now = time.time()
    last = _MIN_GAP["_last"].get(host, 0)
    wait = _GAP - (now - last)
    if wait > 0:
        time.sleep(wait)
    _MIN_GAP["_last"][host] = time.time()


def get(url, timeout=25, referer=None):
    host = urllib.request.urlparse(url).netloc if hasattr(urllib.request, "urlparse") else \
        re.sub(r"https?://([^/]+).*", r"\1", url)
    _throttle(host)
    h = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", errors="replace"), dict(r.headers)


GUARDS = [
    (r"(?i)just a moment|checking your browser|attention required|cloudflare ray id", "cf_challenge"),
    (r"(?i)need to (login|sign up|log in)|please log ?in|create (an )?account to view|"
     r"register to view|you must be logged", "login_wall"),
    (r"(?i)captcha|recaptcha|hcaptcha|turnstile|aliyuncaptcha|verify you are (a )?human|"
     r"单击此处验证|人机验证|安全验证", "captcha"),
    (r"(?i)enable javascript and cookies to continue", "js_required"),
]

# 每个源：主页 + 号码链接正则 + 详情页URL构造
SOURCES = [
    # key,          name,                          homepage,                                   list_re
    ("sms24",       "SMS24.me",        "https://sms24.me/en/",
     r'href="(/en/[^"]*?/(\+?\d{7,15})/?)"'),
    ("mytempsms",   "MyTempSMS",       "https://mytempsms.com/",
     r'href="[^"]*?/number/(\+?\d{7,15})'),
    ("quackr",      "Quackr",          "https://quackr.io/temporary-numbers",
     r'/temporary-numbers/[^"]*?/(\d{7,15})'),
    ("tempnumber",  "Temp-Number.com", "https://temp-number.com/en/countries",
     r'href="[^"]*?/(\+?\d{7,15})"'),
    ("sevsim",      "7sim.net",        "https://7sim.net/",
     r'/number/(\d{7,15})'),
    ("freephonenum","FreePhoneNum",    "https://freephonenum.com/",
     r'href="[^"]*?/(\+?\d{7,15})"'),
    ("smsonlineco", "sms-online.co",   "https://www.sms-online.co/receive-free-sms",
     r'href="[^"]*?/(\+?\d{7,15})"'),
    ("tmpnumber",   "temporary-phone-number.com", "https://temporary-phone-number.com/",
     r'href="[^"]*?/(\+?\d{7,15})"'),
    ("asms",        "asms.ai",         "https://asms.ai/",
     r'href="[^"]*?/(\+?\d{7,15})"'),
    ("smssnet",     "SMSS.net",        "https://smss.net/",
     r'href="[^"]*?/(\+?\d{7,15})"'),
    ("smstome",     "SMSToMe",         "https://smstome.com/",
     r'href="[^"]*?/(\+?\d{7,15})"'),
    ("receivetmp",  "ReceiveTmpSMS",   "https://receive-temp-sms.com/",
     r'href="[^"]*?/(\+?\d{7,15})"'),
    ("instantnum",  "InstantNum",      "https://instantnum.com/",
     r'href="[^"]*?/(\+?\d{7,15})"'),
    ("smsrecvonline","SMSReceiverOnline","https://smsreceiveronline.com/",
     r'href="[^"]*?/(\+?\d{7,15})"'),
    ("smsdock",     "SMSDock",         "https://smsdock.net/",
     r'href="[^"]*?/(\+?\d{7,15})"'),
    ("getsmsuk",    "GetSMS.uk",       "https://getsms.uk/",
     r'href="[^"]*?/(\+?\d{7,15})"'),
    # 已接入的三个源，做对照
    ("rso",         "ReceiveSMSOnline","https://receive-sms-online.info/",
     r'href="[^"]*?-(\d{9,15})-[A-Za-z]+"'),
    ("wetalk",      "WeTalk",          "https://wetalkapp.com/receive-sms-online-usa-12542492894/",
     r'receive-sms-online-[a-z]+-(\d{9,15})'),
    ("receiveasms", "ReceiveAsmsOnline","https://receiveasmsonline.com/united-states/",
     r'href="/united-states/(\+?\d{7,15})/"'),
    ("receivesms",  "ReceiveSMS.co",   "https://receivesms.co/",
     r'href="[^"]*?/(\+?\d{7,15})"'),
]

# 通用号码兜底正则
LOOSE_RE = re.compile(r"\+?\d{9,15}")


def guard_of(html):
    for pat, label in GUARDS:
        if re.search(pat, html):
            return label
    return None


def render_of(html):
    if re.search(r"(?i)ng-version|ng-state=|<app-root", html):
        return "Angular"
    if re.search(r"(?i)__NEXT_DATA__|_next/static", html):
        return "Next.js"
    if re.search(r"(?i)window\.__NUXT", html):
        return "Nuxt"
    # webpack chunk 名
    if re.search(r"/static/js/[a-z0-9.]+\.chunk\.js|webpack-runtime", html, re.I):
        return "React/CRA"
    if re.search(r"(?i)styled-components", html):
        return "React/other"
    return "static"


def audit(item):
    key, name, home, list_re = item
    row = {"key": key, "name": name, "home": home}
    try:
        st, html, hdrs = get(home)
        row["status"] = st
        row["bytes"] = len(html)
    except urllib.error.HTTPError as e:
        row["status"] = f"HTTP {e.code}"
        row["verdict"] = "blocked"
        return row
    except Exception as e:
        row["status"] = "ERR"
        row["error"] = f"{type(e).__name__}: {str(e)[:80]}"
        row["verdict"] = "unreachable"
        return row

    row["guard"] = guard_of(html) or ""
    row["render"] = render_of(html)
    xfo = hdrs.get("X-Frame-Options", "")
    row["xfo"] = xfo
    row["embeddable"] = "no" if xfo and "SAMEORIGIN" in xfo.upper() else "yes"

    # 号码解析
    found = []
    try:
        for m in re.findall(list_re, html, re.I):
            if isinstance(m, tuple):
                m = m[0] if m[0] else m[1]
            d = re.sub(r"\D", "", m)
            if 9 <= len(d) <= 15:
                found.append(d)
    except Exception:
        pass
    if not found:
        loose = [re.sub(r"\D", "", x) for x in LOOSE_RE.findall(html)]
        loose = [x for x in loose if 10 <= len(x) <= 15]
        row["phones_loose"] = len(set(loose))
        row["phones"] = 0
    else:
        row["phones"] = len(set(found))
        row["sample"] = sorted(set(found))[:5]

    # robots
    try:
        rst, rhtml, _ = get(home.rstrip("/") + "/robots.txt", timeout=12)
        dis = re.findall(r"(?im)^\s*disallow:\s*(\S+)", rhtml)
        row["robots"] = "ok" if rst == 200 else f"HTTP {rst}"
        row["robots_disallow"] = dis[:6]
    except Exception as e:
        row["robots"] = f"none ({type(e).__name__})"
        row["robots_disallow"] = []

    # 判定
    if row["status"] != 200:
        row["verdict"] = "blocked"
    elif row["guard"] in ("login_wall",):
        row["verdict"] = "needs_login"
    elif row["guard"] in ("cf_challenge", "js_required"):
        row["verdict"] = "blocked"
    elif row["phones"] == 0 and row.get("phones_loose", 0) == 0:
        row["verdict"] = "no_numbers"
    else:
        row["verdict"] = "usable"
    return row


def main():
    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(audit, s): s for s in SOURCES}
        for f in as_completed(futs):
            r = f.result()
            results.append(r)
            print(f"[{r['verdict']:>12}] {r['name']:<26} {r['status']:<8} "
                  f"phones={r.get('phones', 0):<5} render={r.get('render', '-'):<12} "
                  f"guard={r.get('guard', '-') or '-':<12} embed={r.get('embeddable', '-')}")
            sys.stdout.flush()

    order = {s[0]: i for i, s in enumerate(SOURCES)}
    results.sort(key=lambda r: order.get(r["key"], 99))
    with open("/tmp/source_audit.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 84)
    print("汇总")
    print("=" * 84)
    buckets = {}
    for r in results:
        buckets.setdefault(r["verdict"], []).append(r["name"])
    for v in ("usable", "no_numbers", "needs_login", "blocked", "unreachable"):
        if v in buckets:
            print(f"{v:<12} ({len(buckets[v])}) {', '.join(buckets[v])}")
    print(f"\n完整结果已写入 /tmp/source_audit.json")


if __name__ == "__main__":
    main()
