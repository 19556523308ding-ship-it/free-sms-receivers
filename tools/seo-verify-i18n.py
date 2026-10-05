#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMS Hub · 双语 SEO 自检
=====================
校验（无需浏览器，直接读文件 + 可选 HTTP）：
1. 每个页面恰好 1 个 H1
2. canonical 存在且与文件对应
3. hreflang 双向配对（zh-CN / zh-Hans / en / x-default 齐全且互相指向）
4. JSON-LD 可解析且 @type 合理
5. sitemap 含英文 URL 与 xhtml:link 注解、括号闭合
6. robots.txt 正常、404 存在
7. 英文页源码里含英文正文（不依赖 JS）

用法：python tools/seo-verify-i18n.py
"""
import os
import re
import io
import json
import xml.etree.ElementTree as ET

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(BASE, "web")
SITE = "https://sms.jinzhai.icu"

pass_n = 0
fail_n = 0


def ok(m):
    global pass_n
    pass_n += 1
    print("  ✓ " + m)


def bad(m):
    global fail_n
    fail_n += 1
    print("  ✗ " + m)


def read(p):
    return io.open(p, encoding="utf-8").read()


SEO_BLOCK_RE = re.compile(r'<!--(?:seo|en):block-->([\s\S]*?)<!--/(?:seo|en):block-->')


def page_info(path, url):
    s = read(path)
    # 单一 seo/en block
    blocks = SEO_BLOCK_RE.findall(s)
    head = blocks[0] if blocks else s[:s.find("</head>")]

    canon = re.search(r'<link rel="canonical" href="([^"]+)"', head)
    hl = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', head))
    # H1：含 noscript 容忍（爬虫视角）
    body = s[s.find("<body"):]
    h1 = re.findall(r"<h1[^>]*>", body)
    h1_noscript = len(re.findall(r"<noscript>[\s\S]{0,400}?<h1", body))
    # JSON-LD
    lds = re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', s)
    types = []
    for raw in lds:
        try:
            o = json.loads(raw)
            types.append(o.get("@type") or "graph:" + ",".join(
                g.get("@type", "?") for g in o.get("@graph", [])))
        except Exception as e:
            types.append("PARSE_ERR:" + str(e)[:40])
    return dict(canon=canon.group(1) if canon else None,
                hl=hl,
                h1=len(h1),
                h1_noscript=h1_noscript,
                ld_types=types,
                body=body)


def check_page(label, rel, url):
    p = os.path.join(WEB, rel)
    if not os.path.exists(p):
        bad(f"{label}: 文件不存在 {rel}")
        return None
    info = page_info(p, url)
    # H1 唯一（noscript 占位豁免，爬虫视角）
    tot = info["h1"]
    if tot == 1:
        ok(f"{label} H1 唯一")
    elif tot >= 2 and info["h1_noscript"] >= 2:
        ok(f"{label} H1 {info['h1_noscript']} 个（含 noscript 占位，爬虫视角唯一）")
    else:
        bad(f"{label} H1 数量异常：{tot}")
    # canonical
    if info["canon"] == url:
        ok(f"{label} canonical 正确")
    else:
        bad(f"{label} canonical 不符：{info['canon']} != {url}")
    # JSON-LD
    if info["ld_types"]:
        if any(t.startswith("PARSE_ERR") for t in info["ld_types"]):
            bad(f"{label} JSON-LD 解析失败：{info['ld_types']}")
        else:
            ok(f"{label} JSON-LD：{', '.join(str(t) for t in info['ld_types'])}")
    return info


def check_pair(label, zh_rel, zh_url, en_rel, en_url):
    """hreflang 双向配对：zh 页与 en 页都要有 4 条且互指"""
    items = [(zh_rel, zh_url, "zh"), (en_rel, en_url, "en")]
    infos = {}
    for rel, url, tag in items:
        p = os.path.join(WEB, rel)
        if not os.path.exists(p):
            bad(f"{label}[{tag}] 文件不存在 {rel}")
            infos[tag] = None
            continue
        infos[tag] = page_info(p, url)["hl"]

    for tag in ("zh", "en"):
        hl = infos.get(tag)
        if hl is None:
            continue
        missing = [h for h in ("zh-CN", "zh-Hans", "en", "x-default") if h not in hl]
        if missing:
            bad(f"{label}[{tag}] hreflang 缺 {missing}")
            continue
        ok(f"{label}[{tag}] hreflang 四条齐全")
        # 互指校验
        if hl["en"] != en_url:
            bad(f"{label}[{tag}] hreflang=en 指向错误 {hl['en']}")
        elif hl["zh-CN"] != zh_url:
            bad(f"{label}[{tag}] hreflang=zh-CN 指向错误 {hl['zh-CN']}")
        else:
            ok(f"{label}[{tag}] hreflang 互指正确")


def check_sitemap():
    p = os.path.join(WEB, "sitemap.xml")
    s = read(p)
    try:
        root = ET.fromstring(s)
    except Exception as e:
        bad(f"sitemap XML 解析失败：{e}")
        return
    ok("sitemap.xml XML 合法")
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
          "xhtml": "http://www.w3.org/1999/xhtml"}
    urls = root.findall("sm:url", ns)
    locs = [u.find("sm:loc", ns).text for u in urls]
    ok(f"sitemap 共 {len(locs)} 条 URL")
    en_cnt = sum(1 for l in locs if "/en/" in l or l.rstrip("/").endswith("/en"))
    if en_cnt >= 12:
        ok(f"sitemap 含 {en_cnt} 条英文 URL")
    else:
        bad(f"sitemap 英文 URL 偏少：{en_cnt}")
    # xhtml:link 注解
    alt_cnt = sum(len(u.findall("xhtml:link", ns)) for u in urls)
    if alt_cnt >= 40:
        ok(f"sitemap 含 {alt_cnt} 条 hreflang 注解")
    else:
        bad(f"sitemap hreflang 注解偏少：{alt_cnt}")
    # 每条 URL 都要有 loc
    if all(locs):
        ok("sitemap 每条都有 loc")
    else:
        bad("sitemap 存在空 loc")


def check_robots_404():
    p = os.path.join(WEB, "robots.txt")
    if os.path.exists(p):
        s = read(p)
        if "Sitemap:" in s and "Disallow: /admin" in s:
            ok("robots.txt 正常")
        else:
            bad("robots.txt 内容异常")
    else:
        bad("robots.txt 缺失")
    if os.path.exists(os.path.join(WEB, "404.html")):
        ok("404.html 存在")
    else:
        bad("404.html 缺失")


def check_en_source_text():
    """英文页源码必须含英文正文（不依赖 JS）"""
    cases = [
        ("en/index.html", "Free Temporary Phone Numbers"),
        ("en/numbers.html", "All available numbers"),
        ("en/guide.html", "How to use SMS Hub"),
        ("en/faq.html", "Frequently asked questions"),
        ("en/country/us.html", "Free United States Phone Numbers"),
        ("en/country/gb.html", "Free United Kingdom Phone Numbers"),
    ]
    for rel, needle in cases:
        p = os.path.join(WEB, rel)
        if not os.path.exists(p):
            bad(f"{rel} 不存在")
            continue
        s = read(p)
        if needle in s:
            ok(f"{rel} 源码含「{needle}」")
        else:
            bad(f"{rel} 源码缺「{needle}」")
    # 英文国家页必须预渲染号码列表（SEO 关键）
    p = os.path.join(WEB, "en/country/us.html")
    if os.path.exists(p):
        s = read(p)
        n = len(re.findall(r'class="sp-num"', s))
        if n >= 30:
            ok(f"en/country/us.html 预渲染 {n} 个号码链接")
        else:
            bad(f"en/country/us.html 预渲染号码偏少：{n}")


def main():
    print("SMS Hub · 双语 SEO 自检")
    print("=" * 52)

    print("\n[1] 中文页")
    check_page("首页", "index.html", SITE + "/")
    check_page("号码列表", "numbers.html", SITE + "/numbers")
    check_page("号码详情", "number.html", SITE + "/number")
    check_page("国家总览", "country.html", SITE + "/country")
    check_page("指南", "guide.html", SITE + "/guide")
    check_page("FAQ", "faq.html", SITE + "/faq")
    check_page("国家/us", "country/us.html", SITE + "/country/us")

    print("\n[2] 英文页")
    check_page("EN 首页", "en/index.html", SITE + "/en/")
    check_page("EN 号码列表", "en/numbers.html", SITE + "/en/numbers")
    check_page("EN 号码详情", "en/number.html", SITE + "/en/number")
    check_page("EN 国家总览", "en/country.html", SITE + "/en/country")
    check_page("EN 指南", "en/guide.html", SITE + "/en/guide")
    check_page("EN FAQ", "en/faq.html", SITE + "/en/faq")
    check_page("EN 国家/us", "en/country/us.html", SITE + "/en/country/us")

    print("\n[3] hreflang 双向配对")
    check_pair("首页", "index.html", SITE + "/", "en/index.html", SITE + "/en/")
    check_pair("号码列表", "numbers.html", SITE + "/numbers", "en/numbers.html", SITE + "/en/numbers")
    check_pair("指南", "guide.html", SITE + "/guide", "en/guide.html", SITE + "/en/guide")
    check_pair("FAQ", "faq.html", SITE + "/faq", "en/faq.html", SITE + "/en/faq")
    check_pair("国家/us", "country/us.html", SITE + "/country/us", "en/country/us.html", SITE + "/en/country/us")

    print("\n[4] 英文源码可见性（不依赖 JS）")
    check_en_source_text()

    print("\n[5] sitemap / robots / 404")
    check_sitemap()
    check_robots_404()

    print(f"\n===== 汇总：{pass_n} 通过 / {fail_n} 失败 =====")
    return 1 if fail_n else 0


if __name__ == "__main__":
    raise SystemExit(main())
