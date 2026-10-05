#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMS Hub · 英文版（/en/）生成器
==============================
双语站架构：中文版在站点根，英文版在 /en/ 子目录。
中英共用同一套渲染代码（web/assets/app.js + i18n.js，语言由 URL 前缀推导），
因此本脚本只做「SEO 层」的英文镜像：

1. 从中文页派生 /en/ 页面：静态 HTML 文案换英文、TDK/canonical 指向 /en/...
2. 给中文页与英文页都补齐 **双向 hreflang**（zh-CN / zh-Hans / en / x-default）
3. 生成英文字典驱动的 **英文国家静态页** /en/country/<iso>（H1/正文/号码列表预渲染）
4. 重新生成 sitemap.xml（含英文 URL + xhtml:link 注解）

幂等：所有注入都带 <!--en:block--> / <!--en:css--> 标记，重跑前先清空。

用法：python tools/gen-en.py
"""
import os
import re
import io
import json
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(BASE, "web")
EN = os.path.join(WEB, "en")
SITE = "https://sms.jinzhai.icu"
NOW = datetime.date.today().isoformat()

_changed = []


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    _changed.append(os.path.relpath(p, BASE))


def load_data():
    return json.loads(read(os.path.join(WEB, "data", "numbers.json")))


# ----------------------------------------------------------------------------
# 幂等标记
# ----------------------------------------------------------------------------
EN_BLOCK_RE = re.compile(r'<!--en:block-->[\s\S]*?<!--/en:block-->\s*')
EN_CSS_RE = re.compile(r'<!--en:css-->[\s\S]*?<!--/en:css-->\s*')
SEO_BLOCK_RE = re.compile(r'<!--seo:block-->[\s\S]*?<!--/seo:block-->\s*')
SEO_CSS_RE = re.compile(r'<!--seo:css-->[\s\S]*?<!--/seo:css-->\s*')
STATIC_RE = re.compile(r'<section class="cstatic"[\s\S]*?</section>\s*')
LD_RE = re.compile(r'<script type="application/ld\+json">[\s\S]*?</script>\s*')
NOSCRIPT_H1_RE = re.compile(r'<noscript>\s*<h1[\s\S]*?</noscript>\s*')

OG_IMAGE = f"{SITE}/assets/backgrounds/og-cover.png"
OG_W, OG_H = 1200, 630


def strip_all_injections(s):
    """清掉本脚本与 seo-optimize.py 注入的所有块（生成前先归一）"""
    for rx in (EN_BLOCK_RE, EN_CSS_RE, SEO_BLOCK_RE, SEO_CSS_RE, STATIC_RE, LD_RE):
        s = rx.sub("", s)
    return s


# ----------------------------------------------------------------------------
# 英文 SEO 元数据表（与中文页一一对应）
# ----------------------------------------------------------------------------
META_EN = {
    "index.html": dict(
        path="/en/", prio="1.0", freq="daily", robots="index,follow",
        title="Free Temporary Phone Numbers for SMS Verification | SMS Hub",
        desc=("Free online SMS receiver: 1100+ public temporary phone numbers from the US, "
              "UK, Canada and 20 more countries. No signup — read incoming SMS verification "
              "codes online, with live refresh and automatic code detection. Just copy and verify."),
        og_title="Free Temporary Phone Numbers for SMS Verification | SMS Hub",
        og_desc="No signup. Read SMS verification codes online. 23 countries, live refresh, automatic code detection.",
        crumb=None,
    ),
    "numbers.html": dict(
        path="/en/numbers", prio="0.9", freq="hourly", robots="index,follow",
        title="All Free Temporary Numbers — Filter by Country | SMS Hub",
        desc=("Browse every free temporary number whose SMS can be read directly on this site. "
              "Filter by country, calling code, status and activity, then copy a number to "
              "receive SMS verification codes online in real time."),
        og_title="All Free Temporary Numbers | SMS Hub",
        og_desc="Filter free temporary numbers by country and activity, then copy to receive SMS codes.",
        crumb="All numbers",
    ),
    "number.html": dict(
        path="/en/number", prio="0.6", freq="hourly", robots="index,follow",
        title="Receive SMS Online — Read Verification Codes | SMS Hub",
        desc=("Receive SMS online and read the verification code: this page waits in real time "
              "for public SMS sent to the temporary number, detects the code automatically and "
              "copies it in one tap. No signup, refreshed every 15 seconds."),
        og_title="Receive SMS Online — Read Verification Codes | SMS Hub",
        og_desc="Live SMS refresh, automatic code detection, one-tap copy.",
        crumb="Receive SMS online",
    ),
    "country.html": dict(
        path="/en/country", prio="0.8", freq="hourly", robots="index,follow",
        title="Free Phone Numbers by Country for SMS Verification | SMS Hub",
        desc=("Pick a free temporary phone number by country and read SMS verification codes "
              "online. Covering the US, UK, Canada, Ukraine and 23 countries and regions — "
              "copy a number and use it right away."),
        og_title="Free Phone Numbers by Country | SMS Hub",
        og_desc="Free temporary numbers from 23 countries for online SMS verification.",
        crumb="By country",
    ),
    "guide.html": dict(
        path="/en/guide", prio="0.7", freq="weekly", robots="index,follow",
        title="How to Use SMS Hub — Step-by-Step Guide | SMS Hub",
        desc=("SMS Hub step-by-step guide: how to pick a country and number, copy it, paste it "
              "into the target site, wait for the SMS and copy the verification code — plus "
              "troubleshooting when no code arrives, and safety notes."),
        og_title="How to Use SMS Hub — Full Guide | SMS Hub",
        og_desc="Four steps: pick → copy → paste → copy the code. With troubleshooting and safety notes.",
        crumb="Guide",
    ),
    "faq.html": dict(
        path="/en/faq", prio="0.7", freq="weekly", robots="index,follow",
        title="Free SMS Receiving FAQ — Is It Safe? No Code Arrived? | SMS Hub",
        desc=("Frequently asked questions about free SMS receiving: is it really free, why are "
              "numbers shared, what to do when no code arrives, how accurate automatic detection "
              "is, and whether it can be used for banking or other sensitive accounts."),
        og_title="Free SMS Receiving FAQ | SMS Hub",
        og_desc="Is it free, shared numbers, missing codes, sensitive accounts — answered one by one.",
        crumb="FAQ",
    ),
}


def head_block_en(key, m):
    """英文页的 canonical / hreflang / og / twitter"""
    url = SITE + m["path"]
    zh_url = SITE + (m["path"][3:] if m["path"].startswith("/en/") and len(m["path"]) > 4 else "/") if m["path"] != "/en/" else SITE + "/"
    return f'''<!--en:block-->
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="zh-CN" href="{zh_url}">
<link rel="alternate" hreflang="zh-Hans" href="{zh_url}">
<link rel="alternate" hreflang="en" href="{url}">
<link rel="alternate" hreflang="x-default" href="{zh_url}">
<meta name="robots" content="{m['robots']}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="SMS Hub">
<meta property="og:locale" content="en_US">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{m['og_title']}">
<meta property="og:description" content="{m['og_desc']}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="{OG_W}">
<meta property="og:image:height" content="{OG_H}">
<meta property="og:image:alt" content="SMS Hub — free temporary numbers for SMS verification">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{m['og_title']}">
<meta name="twitter:description" content="{m['og_desc']}">
<meta name="twitter:image" content="{OG_IMAGE}">
<meta name="twitter:image:alt" content="SMS Hub — free temporary numbers for SMS verification">
<!--/en:block-->'''


def jsonld(obj):
    return ('<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            + "</script>")


def website_ld_en():
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": f"{SITE}/#org",
                "name": "SMS Hub",
                "url": SITE + "/",
                "logo": {"@type": "ImageObject",
                         "url": f"{SITE}/assets/brand/logo.svg",
                         "width": 280, "height": 64},
            },
            {
                "@type": "WebSite",
                "@id": f"{SITE}/#website",
                "url": SITE + "/",
                "name": "SMS Hub",
                "description": "Free online SMS receiver covering 23 countries and regions.",
                "inLanguage": "en",
                "publisher": {"@id": f"{SITE}/#org"},
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": {"@type": "EntryPoint",
                               "urlTemplate": f"{SITE}/en/numbers?q={{search_term_string}}"},
                    "query-input": "required name=search_term_string",
                },
            },
        ],
    }


def breadcrumb_ld(items):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n,
             **({"item": u} if u else {})}
            for i, (n, u) in enumerate(items)
        ],
    }


# ----------------------------------------------------------------------------
# 中文页补英文 hreflang（双向配对）
# ----------------------------------------------------------------------------
# 英文静态国家页覆盖的核心国家（与 gen_en_country_pages 的 CORE 保持一致）
CORE_EN_COUNTRIES = ["US", "GB", "CA", "AU", "IN", "ZA", "SE", "NL", "DE", "FR"]


def _hreflang_pairs():
    """返回 {中文页相对路径: (中文 URL 路径, 英文 URL 路径)}"""
    pairs = {
        "index.html": ("/", "/en/"),
        "numbers.html": ("/numbers", "/en/numbers"),
        "number.html": ("/number", "/en/number"),
        "country.html": ("/country", "/en/country"),
        "guide.html": ("/guide", "/en/guide"),
        "faq.html": ("/faq", "/en/faq"),
    }
    # 中文国家静态页 /country/<iso> ↔ 英文国家静态页 /en/country/<iso>
    cd = os.path.join(WEB, "country")
    if os.path.isdir(cd):
        for f in sorted(os.listdir(cd)):
            if not f.endswith(".html"):
                continue
            iso = f[:-5].lower()
            if iso.upper() not in CORE_EN_COUNTRIES:
                continue
            pairs["country/" + f] = (f"/country/{iso}", f"/en/country/{iso}")
    return pairs


def add_hreflang_to_zh():
    """给中文页的 seo:block 补上 hreflang="en" 指向对应的英文页"""
    pairs = _hreflang_pairs()
    for fn, (zhp, enp) in pairs.items():
        p = os.path.join(WEB, fn)
        if not os.path.exists(p):
            continue
        s = read(p)
        zh_url = SITE + zhp
        en_url = SITE + enp
        # 只处理 seo:block 内部：插入 en 行
        m = SEO_BLOCK_RE.search(s)
        if not m:
            print(f"  ! {fn} 无 seo:block，跳过 hreflang 补充")
            continue
        block = m.group(0)
        if 'hreflang="en"' in block:
            continue  # 已补
        nb = block.replace(
            f'<link rel="alternate" hreflang="x-default" href="{zh_url}">',
            f'<link rel="alternate" hreflang="en" href="{en_url}">\n'
            f'<link rel="alternate" hreflang="x-default" href="{zh_url}">',
        )
        s = s[:m.start()] + nb + s[m.end():]
        write(p, s)
        print(f"  ✓ 中文页 {fn} 补 hreflang=en → {enp}")


# ----------------------------------------------------------------------------
# 生成英文静态页
# ----------------------------------------------------------------------------
def gen_en_pages():
    """从中文页派生 /en/ 页面（保留全部 JS，只换 SEO head + 静态文案标签）"""
    # 静态文案标签：中文页里的 data-i18n 会被 JS 按语言重写，
    # 因此英文页只需改 <html lang> 与 SEO head，JS 会自动渲染英文。
    for fn, m in META_EN.items():
        src = os.path.join(WEB, fn)
        if not os.path.exists(src):
            print(f"  ! 跳过不存在的 {fn}")
            continue
        s = read(src)

        # 归一：剥掉中文页注入的所有 SEO 块（英文页用自己的）
        s = strip_all_injections(s)
        s = re.sub(r'\n?<link rel="canonical"[^>]*>', "", s)
        s = re.sub(r'\n?<meta name="robots"[^>]*>', "", s)
        s = re.sub(r'\n?<meta property="og:[^>]*>', "", s)
        s = re.sub(r'\n?<meta name="twitter:[^>]*>', "", s)

        # <html lang>
        s = re.sub(r'<html[^>]*>', '<html lang="en">', s, count=1)

        # 静态 HTML 文案：给 data-i18n 元素填英文（无 JS 时也可见英文）
        s = fill_static_en(s)

        # title / description
        s = re.sub(r"<title>.*?</title>", f"<title>{m['title']}</title>", s, count=1, flags=re.S)
        if 'name="description"' in s:
            s = re.sub(r'<meta name="description" content="[^"]*">',
                       f'<meta name="description" content="{m["desc"]}">', s, count=1)
        else:
            s = s.replace("<title>", f'<meta name="description" content="{m["desc"]}">\n<title>', 1)

        # JSON-LD
        lds = []
        if fn == "index.html":
            lds.append(website_ld_en())
        elif m["crumb"]:
            lds.append(breadcrumb_ld([
                ("Home", SITE + "/en/"),
                (m["crumb"], SITE + m["path"]),
            ]))

        head = head_block_en(fn, m)
        s = s.replace("</head>", head + "\n" + "\n".join(jsonld(x) for x in lds) + "\n</head>", 1)

        # 资源路径绝对化（/en/ 是子目录，相对路径会 404）
        s = absolutize(s)

        out = os.path.join(EN, fn)
        write(out, s)
        label = m["path"][3:] if m["path"].startswith("/en") else m["path"]
        print(f"  ✓ /en{label}  ({fn})")


def absolutize(s):
    """把相对资源路径改成站点绝对路径，兼容 /en/ 子目录"""
    s = s.replace('href="assets/', 'href="/assets/')
    s = s.replace('src="assets/', 'src="/assets/')
    s = s.replace("from './assets/", "from '/assets/")
    s = s.replace('from "./assets/', 'from "/assets/')
    s = s.replace("url('assets/", "url('/assets/")
    s = s.replace('url("assets/', 'url("/assets/')
    # 站内链接：中文页里写死的 numbers.html / index.html 等 -> /en/ 相对干净 URL
    s = s.replace('href="numbers.html"', 'href="/en/numbers"')
    s = s.replace('href="index.html"', 'href="/en/"')
    s = s.replace('href="guide.html"', 'href="/en/guide"')
    s = s.replace('href="faq.html"', 'href="/en/faq"')
    s = s.replace('href="country.html', 'href="/en/country.html')
    s = s.replace('href="number.html', 'href="/en/number.html')
    return s


# ----------------------------------------------------------------------------
# 从 i18n.js 抽出英文词典，用于「静态 HTML 文案填充」
# ----------------------------------------------------------------------------
def load_en_dict():
    src = read(os.path.join(WEB, "assets", "i18n.js"))
    en_start = src.index("const EN = {")
    dic_start = src.index("const DICTS =")
    block = src[en_start:dic_start]
    pairs = {}
    for m in re.finditer(r"'([a-zA-Z][\w.\-]*)':\s*'((?:[^'\\]|\\.)*)'", block):
        val = m.group(2).replace("\\'", "'").replace('\\"', '"')
        pairs[m.group(1)] = val
    return pairs


def fill_static_en(s):
    """把 data-i18n / data-i18n-html 元素的静态内容替换为英文（无 JS 兜底）"""
    D = load_en_dict()

    def esc_html(v):
        return (v.replace("&", "&amp;").replace("<", "&lt;")
                 .replace(">", "&gt;").replace('"', "&quot;"))

    # data-i18n：替换标签内文本
    s = re.sub(r'(<([a-zA-Z0-9]+)[^>]*\sdata-i18n="([^"]+)"[^>]*>)([\s\S]*?)(</\2>)',
               lambda m: m.group(1) + esc_html(D.get(m.group(3), m.group(4))) + m.group(5), s)
    # data-i18n-html：允许内联标签
    s = re.sub(r'(<([a-zA-Z0-9]+)[^>]*\sdata-i18n-html="([^"]+)"[^>]*>)([\s\S]*?)(</\2>)',
               lambda m: m.group(1) + D.get(m.group(3), m.group(4)) + m.group(5), s)
    return s


# ----------------------------------------------------------------------------
# 英文国家静态页 /en/country/<iso>
# ----------------------------------------------------------------------------
EN_COUNTRY_INTRO = {
    "US": "The United States has the largest pool on SMS Hub. US numbers (+1) work with most "
          "services that accept a US phone number; many of them can be read directly here.",
    "GB": "United Kingdom numbers (+44) are widely accepted for one-off signups. Pick an "
          "“Available” number for the best chance of a successful delivery.",
    "CA": "Canadian numbers (+1) share the North American numbering plan and are accepted by "
          "most services that support the US and Canada.",
    "UA": "Ukrainian numbers (+380) are a large part of the pool here and often succeed for "
          "one-off verifications.",
    "DE": "German numbers (+49) are accepted by many European services and are frequently "
          "requested for temporary verification.",
    "FR": "French numbers (+33) are commonly used for European one-off signups and trials.",
    "NL": "Dutch numbers (+31) are widely accepted across European services.",
    "SE": "Swedish numbers (+46) are a reliable choice for Nordic services and trials.",
    "IN": "Indian numbers (+91) are one of the most requested for one-off signups and app trials.",
    "ZA": "South African numbers (+27) are used for regional signups and app trials.",
}


def gen_en_country_pages(data):
    tmpl_path = os.path.join(WEB, "country.html")
    tmpl = read(tmpl_path)
    tmpl = strip_all_injections(tmpl)
    tmpl = re.sub(r'\n?<link rel="canonical"[^>]*>', "", tmpl)
    tmpl = re.sub(r'\n?<meta name="robots"[^>]*>', "", tmpl)
    tmpl = absolutize(tmpl)
    tmpl = re.sub(r'<html[^>]*>', '<html lang="en">', tmpl, count=1)
    tmpl = fill_static_en(tmpl)

    countries = data.get("countries", [])
    numbers = data.get("numbers", [])
    by_iso = {}
    for n in numbers:
        by_iso.setdefault(n.get("countryCode"), []).append(n)

    # 只给核心国家生成英文静态页（用户选择：核心页 + 主要国家页）
    CORE = ["US", "GB", "CA", "AU", "IN", "ZA", "SE", "NL", "DE", "FR"]
    made = []

    for c in countries:
        iso = c.get("iso")
        if iso not in CORE:
            continue
        name_en = c.get("nameEn") or iso
        total = c.get("total", 0)
        direct = c.get("directInbox", 0)
        calling = c.get("callingCode", "")

        pool = by_iso.get(iso, [])
        s_pool = sorted(pool, key=lambda n: (0 if n.get("directInbox") else 1,
                                             -(n.get("availabilityScore") or 0)))

        title = (f"Free {name_en} Phone Numbers for SMS Verification — {total} Numbers | SMS Hub")
        desc = (f"Free {name_en} temporary phone numbers for online SMS verification: "
                f"{total} numbers in total, {direct} readable directly on this site. "
                f"No signup — copy a number and receive SMS codes online in real time.")

        items = []
        for n in s_pool[:40]:
            ph = n.get("phone", "")
            nd = n.get("directInbox")
            st = n.get("status") or "unverified"
            st_label = {"available": "Available", "low_usage": "Low usage",
                        "unverified": "Unverified"}.get(st, "Unverified")
            link = (f'{SITE}/number/{n["id"]}' if nd else (n.get("sourceUrl") or "#"))
            items.append(
                f'<li class="sp-num"><a href="{link}"'
                + ('' if nd else ' rel="noopener nofollow" target="_blank"')
                + f'><span class="ph mono">{ph}</span>'
                + f'<span class="st st-{st}">{st_label}</span></a></li>'
            )
        static_list = "\n".join(items)
        intro = EN_COUNTRY_INTRO.get(
            iso, f"The {name_en} pool holds {total} numbers, {direct} of which can be read on this site.")

        page = tmpl
        page = NOSCRIPT_H1_RE.sub("", page)

        # 钉死 JS 国家码
        page = page.replace(
            "const ISO = (sp.get('c') || 'US').toUpperCase();",
            f"const ISO = (sp.get('c') || '{iso.upper()}').toUpperCase();",
        )
        page = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", page, count=1, flags=re.S)
        page = re.sub(r'<meta name="description" content="[^"]*">',
                      f'<meta name="description" content="{desc}">', page, count=1)
        page = re.sub(r'\n?<link rel="canonical"[^>]*>', "", page)
        page = re.sub(r'\n?<link rel="alternate"[^>]*>', "", page)
        page = re.sub(r'\n?<meta property="og:[^>]*>', "", page)
        page = re.sub(r'\n?<meta name="twitter:[^>]*>', "", page)
        page = LD_RE.sub("", page)

        url = f"{SITE}/en/country/{iso.lower()}"
        zh_url = f"{SITE}/country/{iso.lower()}"
        head = f'''<!--en:block-->
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="zh-CN" href="{zh_url}">
<link rel="alternate" hreflang="zh-Hans" href="{zh_url}">
<link rel="alternate" hreflang="en" href="{url}">
<link rel="alternate" hreflang="x-default" href="{zh_url}">
<meta name="robots" content="index,follow">
<meta property="og:type" content="website">
<meta property="og:site_name" content="SMS Hub">
<meta property="og:locale" content="en_US">
<meta property="og:url" content="{url}">
<meta property="og:title" content="Free {name_en} Phone Numbers for SMS Verification | SMS Hub">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="{OG_W}">
<meta property="og:image:height" content="{OG_H}">
<meta property="og:image:alt" content="SMS Hub — free {name_en} temporary numbers">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Free {name_en} Phone Numbers for SMS Verification | SMS Hub">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{OG_IMAGE}">
<meta name="twitter:image:alt" content="SMS Hub — free {name_en} temporary numbers">
<!--/en:block-->'''
        bc = breadcrumb_ld([
            ("Home", SITE + "/en/"),
            ("All numbers", SITE + "/en/numbers"),
            (f"{name_en} numbers", url),
        ])
        d_pool = [n for n in pool if n.get("directInbox")]
        il = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": f"Free {name_en} numbers for SMS verification",
            "numberOfItems": total,
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "name": f"{name_en} number {n.get('phone','')}",
                 "url": f'{SITE}/number/{n["id"]}'}
                for i, n in enumerate(d_pool[:40])
            ],
        } if d_pool else None
        page = page.replace("</head>",
                            head + "\n" + jsonld(bc) + ("\n" + jsonld(il) if il else "") + "\n</head>", 1)

        static_block = f'''<section class="cstatic" aria-label="About {name_en} numbers">
  <h1>Free {name_en} Phone Numbers for SMS Verification</h1>
  <p>{desc}</p>
  <p>{intro}</p>
  <p class="cstatic-meta">Total numbers <b>{total}</b> · Readable on this site <b>{direct}</b> · Calling code <b>+{calling}</b></p>
  <h2>{name_en} number list</h2>
  <ul class="sp-list">
{static_list}
  </ul>
  <p class="cstatic-more"><a href="/en/numbers">Browse numbers from all countries →</a></p>
</section>
'''
        page = re.sub(r"(<main[^>]*>)", r"\1\n" + static_block.replace("\\", "\\\\"), page, count=1)

        css = '''<!--en:css-->
<style>
.cstatic{padding:32px 0 8px;max-width:900px}
.cstatic h1{font-size:30px;margin:0 0 12px;font-weight:800;letter-spacing:-.02em}
.cstatic h2{font-size:19px;margin:26px 0 12px}
.cstatic p{color:var(--text-muted);font-size:14.5px;line-height:1.75;margin:0 0 12px}
.cstatic p b{color:var(--accent)}
.cstatic-meta{font-size:13.5px!important;color:var(--text-dim)!important}
.sp-list{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px}
.sp-num a{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 12px;border-radius:8px;background:var(--surface);border:1px solid var(--border);color:var(--text);font-size:13.5px}
.sp-num a:hover{border-color:var(--border-strong)}
.sp-num .ph{font-variant-numeric:tabular-nums}
.sp-num .st{font-size:11.5px;flex:none}
.cstatic-more a{color:var(--primary);font-weight:600}
@media (max-width:767px){
  .cstatic{padding:22px 0 4px}
  .cstatic h1{font-size:23px}
  .cstatic h2{font-size:17px}
  .sp-list{grid-template-columns:1fr}
}
</style>
<!--/en:css-->'''
        page = page.replace("</head>", css + "\n</head>", 1)

        write(os.path.join(EN, "country", f"{iso.lower()}.html"), page)
        made.append(iso.lower())
        print(f"  ✓ /en/country/{iso.lower()}  ({name_en})")

    print(f"  ✓ 生成 {len(made)} 个英文国家静态页")
    return made


# ----------------------------------------------------------------------------
# sitemap（中文 + 英文 + hreflang 注解）
# ----------------------------------------------------------------------------
def gen_sitemap(data, iso_all, iso_en):
    urls = []

    def add(loc, prio, freq, lastmod=None, alts=None):
        parts = [f"  <url>\n    <loc>{loc}</loc>"]
        if lastmod:
            parts.append(f"    <lastmod>{lastmod}</lastmod>")
        if alts:
            for hl, href in alts:
                parts.append(f'    <xhtml:link rel="alternate" hreflang="{hl}" href="{href}"/>')
        parts.append(f"    <changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n  </url>")
        urls.append("\n".join(parts))

    def pair(zhp, enp, prio, freq, lastmod=None):
        zh, en = SITE + zhp, SITE + enp
        alts = [("zh-CN", zh), ("zh-Hans", zh), ("en", en), ("x-default", zh)]
        add(zh, prio, freq, lastmod, alts)
        add(en, prio, freq, lastmod, alts)

    pair("/", "/en/", "1.0", "daily", NOW)
    pair("/numbers", "/en/numbers", "0.9", "hourly", NOW)
    pair("/guide", "/en/guide", "0.7", "weekly")
    pair("/faq", "/en/faq", "0.7", "weekly")

    cty = {c.get("iso"): c for c in data.get("countries", [])}
    for iso in iso_all:
        c = cty.get(iso, {})
        prio = "0.8" if c.get("directInbox", 0) > 0 else "0.5"
        zh = f"{SITE}/country/{iso.lower()}"
        alts = [("zh-CN", zh), ("zh-Hans", zh), ("x-default", zh)]
        if iso.lower() in iso_en:
            en = f"{SITE}/en/country/{iso.lower()}"
            alts = [("zh-CN", zh), ("zh-Hans", zh), ("en", en), ("x-default", zh)]
            add(en, prio, "daily", NOW, alts)
        add(zh, prio, "daily", NOW, alts)

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
           '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    write(os.path.join(WEB, "sitemap.xml"), xml)
    print(f"  ✓ sitemap.xml（{len(urls)} 条 URL，含英文与 hreflang）")


def gen_robots():
    txt = f"""User-agent: *
Allow: /
Disallow: /admin
Disallow: /admin.html
Disallow: /*?c=
Disallow: /*?id=
Disallow: /*?q=
Disallow: /*?sort=
Disallow: /*?source=

# Large crawlers: slow down (data refreshes hourly)
User-agent: AhrefsBot
Crawl-delay: 10
User-agent: SemrushBot
Crawl-delay: 10

Sitemap: {SITE}/sitemap.xml
"""
    write(os.path.join(WEB, "robots.txt"), txt)
    print("  ✓ robots.txt")


def main():
    print("SMS Hub · 英文版（/en/）生成")
    print("=" * 48)
    data = load_data()

    print("\n[1/4] 中文页补 hreflang=en（双向配对）")
    add_hreflang_to_zh()

    print("\n[2/4] 生成 /en/ 英文静态页")
    gen_en_pages()

    print("\n[3/4] 生成英文国家静态页 /en/country/<iso>")
    iso_all = [c.get("iso") for c in data.get("countries", []) if c.get("iso")]
    iso_en = gen_en_country_pages(data)

    print("\n[4/4] sitemap / robots")
    gen_sitemap(data, iso_all, iso_en)
    gen_robots()

    print(f"\n共修改/生成 {len(_changed)} 个文件")


if __name__ == "__main__":
    main()
