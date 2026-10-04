#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二轮深挖：对首页抓不到号码的源，定位其真实列表页；
对能抓到的源，实测详情页短信正文是否公开可读。
产出 /tmp/source_deep.json
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
GAP = 1.3
_last = {}


def get(url, timeout=25, referer=None):
    host = re.sub(r"https?://([^/]+).*", r"\1", url)
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


def guard_of(html):
    g = [(r"(?i)just a moment|checking your browser|attention required", "cf_challenge"),
         (r"(?i)need to (login|sign up|log in)|please log ?in|register to view", "login_wall"),
         (r"(?i)captcha|recaptcha|hcaptcha|turnstile|aliyuncaptcha|单击此处验证|人机验证", "captcha")]
    for p, l in g:
        if re.search(p, html):
            return l
    return ""


# ---------- A. 深挖列表页 ----------
FIND_PAGES = [
    ("mytempsms", "MyTempSMS", "https://mytempsms.com/",
     ["/countries", "/numbers", "/en", "/us", "/usa"]),
    ("sevsim", "7sim.net", "https://7sim.net/",
     ["/en", "/numbers", "/countries"]),
    ("freephonenum", "FreePhoneNum", "https://freephonenum.com/",
     ["/numbers", "/en", "/all"]),
    ("smstome", "SMSToMe", "https://smstome.com/",
     ["/receive-sms-online", "/numbers", "/en"]),
    ("instantnum", "InstantNum", "https://instantnum.com/",
     ["/numbers", "/en", "/us"]),
    ("receivesms", "ReceiveSMS.co", "https://receivesms.co/",
     ["/free-phone-numbers", "/numbers", "/all-active-phone-numbers"]),
    ("receivetmp", "ReceiveTmpSMS", "https://receive-temp-sms.com/",
     ["/numbers", "/en"]),
    ("smsrecvonline", "SMSReceiverOnline", "https://smsreceiveronline.com/",
     ["/numbers", "/en"]),
    ("rso", "ReceiveSMSOnline", "https://receive-sms-online.info/",
     ["/sms-receive-free", "/countries"]),
    ("smsdock", "SMSDock", "https://smsdock.net/", ["/numbers", "/free"]),
]

PHONE_RE = re.compile(r"\+?\d{9,15}")


def norm(d):
    d = re.sub(r"\D", "", d)
    return d if 9 <= len(d) <= 15 else ""


def find_list_pages():
    out = []
    for key, name, home, cands in FIND_PAGES:
        best = None
        for c in cands:
            url = (home.rstrip("/") + c)
            try:
                st, html, _, _ = get(url)
            except Exception as e:
                out.append({"key": key, "try": url, "status": f"{type(e).__name__}"})
                continue
            g = guard_of(html)
            # 提取像号码的链接
            links = set()
            for m in re.finditer(r'href="([^"]*?)"', html):
                href = m.group(1)
                seg = href.rstrip("/").split("/")[-1]
                d = norm(seg)
                if d and 9 <= len(d) <= 15:
                    links.add((d, href))
            loose = {norm(x) for x in PHONE_RE.findall(html)}
            loose = {x for x in loose if 9 <= len(x) <= 15}
            rec = {"key": key, "name": name, "try": url, "status": st,
                   "bytes": len(html), "guard": g,
                   "linked_phones": len(links), "loose_phones": len(loose)}
            out.append(rec)
            print(f"  {name:<22} {c:<26} {st} linked={len(links):<4} loose={len(loose):<4} {g or 'OK'}")
            sys.stdout.flush()
            score = len(links) * 3 + len(loose)
            if not g and st == 200 and score > 0 and (best is None or score > best[0]):
                best = (score, url, list(links)[:8])
            if len(links) > 3:
                break
        if best:
            out.append({"key": key, "name": name, "BEST_LIST": best[1],
                        "samples": best[2], "note": "候选列表页"})
            print(f"  >>> {name} 最佳列表页: {best[1]}")
    return out


# ---------- B. 详情页正文实测 ----------
DETAIL_TESTS = [
    ("temporary-phone-number.com", "https://temporary-phone-number.com/"),
    ("sms-online.co", "https://www.sms-online.co/receive-free-sms"),
    ("asms.ai", "https://asms.ai/"),
    ("smsdock.net", "https://smsdock.net/"),
    ("getsms.uk", "https://getsms.uk/"),
    ("receiveasmsonline.com", "https://receiveasmsonline.com/united-states/"),
]

DETAIL_PATTERNS = [
    re.compile(r'href="([^"]*?/(\+?\d{9,15})/?)"'),
    re.compile(r'href="([^"]*?(\+?\d{9,15})[^"]*)"'),
]


def probe_details():
    rows = []
    for name, listurl in DETAIL_TESTS:
        print(f"\n--- {name} ---")
        try:
            st, html, _, _ = get(listurl)
        except Exception as e:
            print(f"  列表页失败 {type(e).__name__}")
            rows.append({"name": name, "error": type(e).__name__})
            continue

        phones = []
        for pat in DETAIL_PATTERNS:
            for href, *rest in pat.findall(html):
                d = norm(rest[0] if rest else "")
                if d:
                    phones.append((d, href))
        # 去重保序
        seen, uniq = set(), []
        for d, h in phones:
            if d not in seen:
                seen.add(d)
                uniq.append((d, h))
        print(f"  列表页 {st}, 提取 {len(uniq)} 个号码链接")
        row = {"name": name, "list": listurl, "found": len(uniq)}
        if not uniq:
            rows.append(row)
            continue

        readable = 0
        checked = 0
        for d, href in uniq[:3]:
            durl = href if href.startswith("http") else (
                listurl.rstrip("/").rsplit("/", 1)[0] + href if href.startswith("/")
                else listurl.rstrip("/") + "/" + href)
            try:
                s2, h2, hd2, _ = get(durl, referer=listurl)
            except Exception as e:
                print(f"    {d}: {type(e).__name__}")
                continue
            checked += 1
            g = guard_of(h2)
            body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", h2)
            vis = re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", body))
            kw = len(re.findall(r"(?i)verification code|your code|one[- ]time|OTP|passcode|"
                                r"security code|验证码|is your .* code", vis))
            digits = re.findall(r"\b(\d{4,8})\b", vis)
            xfo = hd2.get("X-Frame-Options", "")
            ok = (not g) and (kw > 0 or len(digits) > 2)
            if ok:
                readable += 1
            print(f"    {d}: {s2} guard={g or '-'} kw={kw} digits={len(digits)} "
                  f"xfo={xfo or '-'} => {'✅可读' if ok else '❌无正文'}")
            row.setdefault("details", []).append(
                {"phone": d, "status": s2, "guard": g, "kw": kw,
                 "digits": len(digits), "xfo": xfo, "readable": ok, "url": durl})
            sys.stdout.flush()
            time.sleep(1.5)
        row["checked"] = checked
        row["readable"] = readable
        rows.append(row)
    return rows


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    data = {}
    if mode in ("all", "list"):
        print("=" * 84)
        print("[A] 深挖列表页")
        print("=" * 84)
        data["list_pages"] = find_list_pages()
    if mode in ("all", "detail"):
        print("\n" + "=" * 84)
        print("[B] 详情页短信正文实测")
        print("=" * 84)
        data["details"] = probe_details()

    with open("/tmp/source_deep.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("\n已写入 /tmp/source_deep.json")
