#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SMS Hub · Google SEO 优化脚本
=============================
1. 为每个页面补齐 canonical / og / twitter 卡片 / hreflang
2. 注入 JSON-LD 结构化数据（WebSite / Organization / FAQPage / ItemList / BreadcrumbList）
3. 修正 robots 指令（number/numbers 放开收录，admin 保持 noindex）
4. 生成 23 个国家静态页（构建期预渲染 H1/正文，不依赖 JS）
5. 重新生成 sitemap.xml / robots.txt / 404.html

用法：python tools/seo-optimize.py
"""
import os
import re
import io
import json
import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(BASE, "web")
SITE = "https://sms.jinzhai.icu"

NOW = datetime.date.today().isoformat()

_changed = []


def read(p):
    return io.open(p, encoding="utf-8").read()


def write(p, s):
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    _changed.append(os.path.relpath(p, BASE))


def load_data():
    return json.loads(read(os.path.join(WEB, "data", "numbers.json")))


# ----------------------------------------------------------------------------
# SEO 元数据表
# ----------------------------------------------------------------------------
META = {
    "index.html": dict(
        path="/", prio="1.0", freq="daily", robots="index,follow",
        title="免费接码 - 在线接收短信验证码，无需注册 | SMS Hub",
        desc="免费接码平台 SMS Hub：提供 1100+ 个美英等 23 国临时手机号码，"
             "无需注册、在线直接查看收到的短信验证码，短信自动刷新、验证码自动识别，"
             "一键复制即可完成验证。",
        og_title="免费接码 - 在线接收短信验证码 | SMS Hub",
        og_desc="无需注册，在线接收短信验证码。覆盖 23 个国家，短信实时刷新，验证码自动识别。",
    ),
    "numbers.html": dict(
        path="/numbers", prio="0.9", freq="hourly", robots="index,follow",
        title="全部免费接码号码列表 - 按国家筛选 | SMS Hub",
        desc="浏览全部站内可直接接收短信的免费临时号码，支持按国家、区号、状态和活跃度筛选，"
             "复制号码即可在线接收短信验证码，实时刷新。",
        og_title="全部免费接码号码列表 | SMS Hub",
        og_desc="按国家与活跃度筛选免费临时号码，复制即可在线接收短信验证码。",
    ),
    "number.html": dict(
        path="/number", prio="0.6", freq="hourly", robots="index,follow",
        title="在线接收短信 - 查看短信验证码 | SMS Hub",
        desc="在线接收短信并查看验证码：在站内实时等待该临时号码收到的公开短信，系统自动识别验证码、"
             "一键复制即可完成账号验证，全程无需注册，短信每 15 秒自动刷新。",
        og_title="在线接收短信，查看短信验证码 | SMS Hub",
        og_desc="实时刷新短信、自动识别验证码，一键复制完成验证。",
    ),
    "country.html": dict(
        path="/country", prio="0.8", freq="hourly", robots="index,follow",
        title="按国家选择免费接码号码 | SMS Hub",
        desc="按国家选择免费临时手机号码，在线接收短信验证码。覆盖美国、英国、加拿大、"
             "乌克兰等 23 个国家与地区，复制号码即可使用。",
        og_title="按国家选择免费接码号码 | SMS Hub",
        og_desc="覆盖 23 个国家的免费临时号码，在线接收短信验证码。",
    ),
    "guide.html": dict(
        path="/guide", prio="0.7", freq="weekly", robots="index,follow",
        title="免费接码怎么用 - 使用指南（含图文步骤） | SMS Hub",
        desc="SMS Hub 免费接码使用指南：如何选择国家和号码、复制号码、填写到目标网站、"
             "等待短信、复制验证码，含收不到短信的排查方法与安全提示。",
        og_title="免费接码怎么用 - 完整使用指南 | SMS Hub",
        og_desc="四步完成接码：选号码 → 复制 → 填写 → 复制验证码。含排查与安全提示。",
    ),
    "faq.html": dict(
        path="/faq", prio="0.7", freq="weekly", robots="index,follow",
        title="免费接码常见问题 FAQ - 安全吗？收不到短信怎么办 | SMS Hub",
        desc="免费接码常见问题解答：真的免费吗、号码为什么是共用、收不到验证码怎么办、"
             "验证码自动识别是否准确、能否用于银行等敏感账户等。",
        og_title="免费接码常见问题 FAQ | SMS Hub",
        og_desc="是否免费、号码共用、收不到短信怎么办、能否用于敏感账户，逐个解答。",
    ),
}

IMAGE = f"{SITE}/assets/brand/logo.svg"
# og:image 必须是位图：Facebook / X / 微信等均不渲染 SVG。
# 由 tools/gen-og.js 从 hero 素材 + logo 合成 1200x630 PNG。
OG_IMAGE = f"{SITE}/assets/backgrounds/og-cover.png"
OG_W, OG_H = 1200, 630


def build_head_block(key, m):
    """生成追加到 </head> 前的 SEO 标签"""
    url = SITE + m["path"] if m["path"] != "/" else SITE + "/"
    return f'''<!--seo:block-->
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="zh-CN" href="{url}">
<link rel="alternate" hreflang="zh-Hans" href="{url}">
<link rel="alternate" hreflang="x-default" href="{url}">
<meta name="robots" content="{m['robots']}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="SMS Hub">
<meta property="og:locale" content="zh_CN">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{m['og_title']}">
<meta property="og:description" content="{m['og_desc']}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="{OG_W}">
<meta property="og:image:height" content="{OG_H}">
<meta property="og:image:alt" content="SMS Hub 免费在线接码 · 接收短信验证码">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{m['og_title']}">
<meta name="twitter:description" content="{m['og_desc']}">
<meta name="twitter:image" content="{OG_IMAGE}">
<meta name="twitter:image:alt" content="SMS Hub 免费在线接码 · 接收短信验证码">
<!--/seo:block-->'''


def jsonld(obj):
    return ('<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            + "</script>")


# 本脚本注入的所有 <script type="application/ld+json"> 都带这个标记，
# 便于重复运行时先清空再注入，避免结构化数据成倍堆积。
LD_OPEN = '<script type="application/ld+json">'
LD_RE = re.compile(r'<script type="application/ld\+json">[\s\S]*?</script>\s*')
# 本脚本注入的 head 块（canonical/hreflang/og/twitter）整段可识别
SEO_BLOCK_RE = re.compile(r'<!--seo:block-->[\s\S]*?<!--/seo:block-->\s*')
SEO_CSS_RE = re.compile(r'<!--seo:css-->[\s\S]*?<!--/seo:css-->\s*')
STATIC_RE = re.compile(r'<section class="cstatic"[\s\S]*?</section>\s*')
# country.html 模板里的 noscript H1 占位：国家静态页自带可见 H1，故生成时剥掉
NOSCRIPT_H1_RE = re.compile(r'<noscript>\s*<h1[\s\S]*?</noscript>\s*')


def strip_prev_injections(s):
    """幂等化：清掉上一次运行注入的内容，避免重复"""
    s = SEO_BLOCK_RE.sub("", s)
    s = SEO_CSS_RE.sub("", s)
    s = STATIC_RE.sub("", s)
    s = LD_RE.sub("", s)
    return s


def org_ld():
    return {
        "@type": "Organization",
        "@id": f"{SITE}/#org",
        "name": "SMS Hub",
        "alternateName": "SMS Hub 免费接码",
        "url": SITE + "/",
        "logo": {"@type": "ImageObject", "url": IMAGE, "width": 280, "height": 64},
    }


def website_ld():
    return {
        "@context": "https://schema.org",
        "@graph": [
            org_ld(),
            {
                "@type": "WebSite",
                "@id": f"{SITE}/#website",
                "url": SITE + "/",
                "name": "SMS Hub",
                "description": "免费在线接收短信验证码平台，覆盖 23 个国家与地区。",
                "inLanguage": "zh-CN",
                "publisher": {"@id": f"{SITE}/#org"},
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": {
                        "@type": "EntryPoint",
                        "urlTemplate": f"{SITE}/numbers?q={{search_term_string}}",
                    },
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
# 1. 静态页面 SEO 注入
# ----------------------------------------------------------------------------
def optimize_static_pages():
    for fn, m in META.items():
        p = os.path.join(WEB, fn)
        if not os.path.exists(p):
            print(f"  ! 跳过不存在的 {fn}")
            continue
        s = read(p)

        # 幂等：先清掉上一次注入的内容
        s = strip_prev_injections(s)

        # 移除旧的 canonical / robots（避免重复）
        s = re.sub(r'\n?<link rel="canonical"[^>]*>', "", s)
        s = re.sub(r'\n?<meta name="robots"[^>]*>', "", s)

        # 替换 title / description
        s = re.sub(r"<title>.*?</title>", f"<title>{m['title']}</title>", s, count=1, flags=re.S)
        if 'name="description"' in s:
            s = re.sub(r'<meta name="description" content="[^"]*">',
                       f'<meta name="description" content="{m["desc"]}">', s, count=1)
        else:
            s = s.replace("<title>", f'<meta name="description" content="{m["desc"]}">\n<title>', 1)

        # 移除旧的 og:*
        s = re.sub(r'\n?<meta property="og:[^>]*>', "", s)

        # 注入 head 块
        s = s.replace("</head>", build_head_block(fn, m) + "\n</head>", 1)

        # 注入 JSON-LD
        lds = []
        if fn == "index.html":
            lds.append(website_ld())
        else:
            lds.append(breadcrumb_ld([("首页", SITE + "/"), (m["og_title"].split(" | ")[0], SITE + m["path"])]))
        s = s.replace("</head>", "\n".join(jsonld(x) for x in lds) + "\n</head>", 1)
        write(p, s)
        print(f"  ✓ {fn}")


# ----------------------------------------------------------------------------
# 2. FAQ 结构化数据（从 faq.html 的问答里提取）
# ----------------------------------------------------------------------------
def optimize_faq():
    p = os.path.join(WEB, "faq.html")
    s = read(p)
    s = LD_RE.sub("", s)   # 幂等：清掉上次注入的结构化数据

    # 从页面里抓 <details>/<summary> 或 h3+p 结构
    qa = []
    # 优先 <details><summary>Q</summary>...A...</details>
    for m in re.finditer(r"<summary[^>]*>(.*?)</summary>(.*?)</details>", s, re.S):
        q = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        a = re.sub(r"<[^>]+>", " ", m.group(2)).strip()
        a = re.sub(r"\s+", " ", a)
        if q and a:
            qa.append((q, a[:600]))

    if not qa:
        # 本站 faq.html 结构：<h2>问题</h2><p>答案</p>（可能有多个 p）
        for m in re.finditer(r"<h2[^>]*>(.*?)</h2>(.*?)(?=<h2|</section|</main)", s, re.S):
            q = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            a = re.sub(r"<[^>]+>", " ", m.group(2)).strip()
            a = re.sub(r"\s+", " ", a)
            if q:
                qa.append((q, a[:700]))

    if not qa:
        # 退化：<h3>Q</h3> 后接 <p>A</p>
        for m in re.finditer(r"<h3[^>]*>(.*?)</h3>\s*(?:<p[^>]*>(.*?)</p>)?", s, re.S):
            q = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            a = re.sub(r"<[^>]+>", " ", m.group(2) or "").strip()
            if q:
                qa.append((q, re.sub(r"\s+", " ", a)[:600]))

    if not qa:
        print("  ! faq.html 未提取到问答（跳过 FAQPage）")
        return

    ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a or q}}
            for q, a in qa
        ],
    }
    s = s.replace("</head>", jsonld(ld) + "\n</head>", 1)
    write(p, s)
    print(f"  ✓ faq.html 注入 FAQPage（{len(qa)} 个问答）")


# ----------------------------------------------------------------------------
# 3. 号码列表页 ItemList
# ----------------------------------------------------------------------------
def optimize_numbers_itemlist(data):
    p = os.path.join(WEB, "numbers.html")
    s = read(p)
    s = LD_RE.sub("", s)   # 幂等
    nums = [n for n in data["numbers"] if n.get("directInbox")][:60]
    ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "站内可直接接收短信的免费号码",
        "numberOfItems": len([n for n in data["numbers"] if n.get("directInbox")]),
        "itemListOrder": "https://schema.org/ItemListOrderDescending",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "name": f"{n.get('countryNameZh','')}免费接码号码 {n.get('phone','')}",
             "url": f"{SITE}/number/{n['id']}"}
            for i, n in enumerate(nums)
        ],
    }
    s = s.replace("</head>", jsonld(ld) + "\n</head>", 1)
    write(p, s)
    print(f"  ✓ numbers.html 注入 ItemList（前 {len(nums)} 条）")


# ----------------------------------------------------------------------------
# 4. 国家静态页生成（SEO 核心：不依赖 JS）
# ----------------------------------------------------------------------------
FLAG_ISO = {  # 有内置 SVG 国旗的国家
    "US", "GB", "CA", "DE", "FR", "JP", "AU", "SG", "NL", "IT", "ES", "IN",
    "BR", "ID", "PH", "RO", "PL", "PR", "UA", "SE", "MY", "MX", "VN",
}

COUNTRY_INTRO = {
    "US": "美国是全球免费接码需求量最大的国家，也是各类海外服务的默认注册区域。"
          "本站提供大量美国临时号码，其中相当一部分可在站内直接查看短信。",
    "GB": "英国号码常用于注册英国区服务与部分欧洲平台。英国号码池数量大、更新频繁，"
          "适合需要英国本地号码验证的场景。",
    "CA": "加拿大号码与北美区号体系共用 +1，适合需要北美号码但希望避开美国号码的场景。",
    "UA": "乌克兰号码在部分小众平台上通过率较好，号码池虽小但站内可直收比例高。",
}


def gen_country_pages(data):
    """把国家页静态化：每个国家一个 HTML，首屏内容直接写进源码"""
    tmpl_path = os.path.join(WEB, "country.html")
    tmpl = read(tmpl_path)
    # country.html 自身是一个「模板 + 通用壳」，它会被 optimize_static_pages() 注入
    # 一份 /country 的 SEO 头；生成子页时先剥掉，避免把父页的 canonical/JSON-LD 复制进子页。
    tmpl = strip_prev_injections(tmpl)
    tmpl = re.sub(r'\n?<link rel="canonical"[^>]*>', "", tmpl)
    tmpl = re.sub(r'\n?<meta name="robots"[^>]*>', "", tmpl)
    countries = data.get("countries", [])
    numbers = data.get("numbers", [])

    # 按国家分组号码
    by_iso = {}
    for n in numbers:
        by_iso.setdefault(n.get("countryCode"), []).append(n)

    main_html = tmpl  # country.html 保留为「通用壳」，供 /country?c=xx 老链接用
    made = 0

    for c in countries:
        iso = c.get("iso")
        if not iso:
            continue
        name_zh = c.get("nameZh") or iso
        name_en = c.get("nameEn") or iso
        total = c.get("total", 0)
        direct = c.get("directInbox", 0)
        calling = c.get("callingCode", "")

        # 该国号码（direct 优先）
        pool = by_iso.get(iso, [])
        d_pool = [n for n in pool if n.get("directInbox")]
        s_pool = sorted(pool, key=lambda n: (0 if n.get("directInbox") else 1,
                                             -(n.get("availabilityScore") or 0)))

        title = (f"{name_zh}免费接码 - {total} 个{name_zh}临时号码在线接收短信 | SMS Hub")
        desc = (f"{name_zh}免费接码：共 {total} 个{name_zh}临时手机号码"
                f"（{direct} 个可在站内直接查看短信）。无需注册，"
                f"复制号码即可在线接收短信验证码，短信实时刷新、验证码自动识别。")

        # 静态号码列表（前 40 个，保证源码里有实体内容）
        items = []
        for i, n in enumerate(s_pool[:40]):
            ph = n.get("phone", "")
            nd = n.get("directInbox")
            st = n.get("status") or "unverified"
            st_label = {"available": "可用", "low_usage": "较少使用",
                        "unverified": "暂未验证"}.get(st, "暂未验证")
            link = (f'{SITE}/number/{n["id"]}' if nd else (n.get("sourceUrl") or "#"))
            items.append(
                f'<li class="sp-num"><a href="{link}"'
                + ('' if nd else ' rel="noopener nofollow" target="_blank"')
                + f'><span class="ph mono">{ph}</span>'
                + f'<span class="st st-{st}">{st_label}</span></a></li>'
            )

        static_list = "\n".join(items)
        intro = COUNTRY_INTRO.get(iso,
            f"{name_zh}（{name_en}）号码池共 {total} 个号码，"
            f"其中 {direct} 个可在本站内直接查看短信。")
        flag = (f'<img class="fl" src="/assets/flags/{iso.lower()}.svg" '
                f'alt="{name_zh}国旗" width="46" height="31" loading="lazy">'
                if iso in FLAG_ISO else
                f'<img class="fl" src="https://flagcdn.com/w80/{iso.lower()}.png" '
                f'alt="{name_zh}国旗" width="46" height="31" loading="lazy">')

        # 面包屑
        bc = breadcrumb_ld([
            ("首页", SITE + "/"),
            ("全部号码", SITE + "/numbers"),
            (f"{name_zh}号码", f"{SITE}/country/{iso.lower()}"),
        ])
        # ItemList
        il = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": f"{name_zh}免费接码号码",
            "numberOfItems": total,
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1,
                 "name": f"{name_zh}号码 {n.get('phone','')}",
                 "url": f'{SITE}/number/{n["id"]}'}
                for i, n in enumerate(d_pool[:40])
            ],
        } if d_pool else None

        # 用替换法把静态内容塞进模板：替换掉 JS 占位区，加 <noscript-ish> 静态段落
        # 直接生成一个独立的静态 HTML（保留 JS 增强）
        page = tmpl

        # 国家静态页自带可见 H1，剥掉模板里的 noscript 占位，避免两个 H1
        page = NOSCRIPT_H1_RE.sub("", page)

        # 关键：country 页在 /country/ 子目录下，相对路径会全部 404。
        # 统一把相对资源路径改成站点绝对路径（/assets/...），这样 CSS/JS/图标都能加载。
        page = page.replace('href="assets/', 'href="/assets/')
        page = page.replace('src="assets/', 'src="/assets/')
        page = page.replace("from './assets/", "from '/assets/")
        page = page.replace('from "./assets/', 'from "/assets/')
        page = page.replace("url('assets/", "url('/assets/")
        page = page.replace('url("assets/', 'url("/assets/')

        # title / description
        page = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", page, count=1, flags=re.S)
        page = re.sub(r'<meta name="description" content="[^"]*">',
                      f'<meta name="description" content="{desc}">', page, count=1)
        url = f"{SITE}/country/{iso.lower()}"
        page = re.sub(r'\n?<link rel="canonical"[^>]*>', "", page)
        page = re.sub(r'\n?<link rel="alternate"[^>]*>', "", page)
        page = re.sub(r'\n?<meta property="og:[^>]*>', "", page)
        page = re.sub(r'\n?<meta name="twitter:[^>]*>', "", page)
        page = LD_RE.sub("", page)

        # 关键：静态页 URL 是 /country/gb，没有 ?c= 查询串，
        # 因此要把 JS 的国家码默认值钉死成该国，否则实时块会回落到 US。
        page = page.replace(
            "const ISO = (sp.get('c') || 'US').toUpperCase();",
            f"const ISO = (sp.get('c') || '{iso.upper()}').toUpperCase();",
        )
        # 注入 head
        head = f'''<!--seo:block-->
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="zh-CN" href="{url}">
<link rel="alternate" hreflang="zh-Hans" href="{url}">
<link rel="alternate" hreflang="x-default" href="{url}">
<meta name="robots" content="index,follow">
<meta property="og:type" content="website">
<meta property="og:site_name" content="SMS Hub">
<meta property="og:locale" content="zh_CN">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="{OG_W}">
<meta property="og:image:height" content="{OG_H}">
<meta property="og:image:alt" content="{name_zh}免费接码 · SMS Hub">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{OG_IMAGE}">
<meta name="twitter:image:alt" content="{name_zh}免费接码 · SMS Hub">
<!--/seo:block-->
{jsonld(bc)}
{jsonld(il) if il else ''}'''
        page = page.replace("</head>", head + "\n</head>", 1)

        # 注入静态内容块（放在 <main> 里 JS 容器之前），保证无 JS 也可见
        static_block = f'''<section class="cstatic" aria-label="{name_zh}号码简介">
  <h1>{name_zh}免费接码号码</h1>
  <p>{desc}</p>
  <p>{intro}</p>
  <p class="cstatic-meta">号码总数 <b>{total}</b> · 站内可直接收短信 <b>{direct}</b> 个 · 国际区号 <b>+{calling}</b></p>
  <h2>{name_zh}号码列表</h2>
  <ul class="sp-list">
{static_list}
  </ul>
  <p class="cstatic-more"><a href="/numbers">查看全部国家的号码 →</a></p>
</section>
'''
        # 插入到 <main ...> 之后
        page = re.sub(r"(<main[^>]*>)", r"\1\n" + static_block.replace("\\", "\\\\"), page, count=1)

        # 静态块的 CSS
        css = '''<!--seo:css-->
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
<!--/seo:css-->'''
        page = page.replace("</head>", css + "\n</head>", 1)

        out = os.path.join(WEB, "country", f"{iso.lower()}.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        write(out, page)
        made += 1

    print(f"  ✓ 生成 {made} 个国家静态页 -> web/country/<iso>.html")
    return [c.get("iso") for c in countries if c.get("iso")]


# ----------------------------------------------------------------------------
# 5. sitemap / robots / 404
# ----------------------------------------------------------------------------
def gen_sitemap(data, isos):
    urls = []

    def add(loc, prio, freq, lastmod=None):
        urls.append(
            f"  <url>\n    <loc>{loc}</loc>\n"
            + (f"    <lastmod>{lastmod}</lastmod>\n" if lastmod else "")
            + f"    <changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n  </url>"
        )

    add(f"{SITE}/", "1.0", "daily", NOW)
    add(f"{SITE}/numbers", "0.9", "hourly", NOW)
    add(f"{SITE}/guide", "0.7", "weekly")
    add(f"{SITE}/faq", "0.7", "weekly")

    # 国家页：站内有可收号码的优先级更高
    cty = {c.get("iso"): c for c in data.get("countries", [])}
    for iso in isos:
        c = cty.get(iso, {})
        prio = "0.8" if c.get("directInbox", 0) > 0 else "0.5"
        add(f"{SITE}/country/{iso.lower()}", prio, "daily", NOW)

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>")
    write(os.path.join(WEB, "sitemap.xml"), xml)
    print(f"  ✓ sitemap.xml（{len(urls)} 条 URL）")


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

# 大站爬虫放慢（本站数据每小时更新）
User-agent: AhrefsBot
Crawl-delay: 10
User-agent: SemrushBot
Crawl-delay: 10

Sitemap: {SITE}/sitemap.xml
"""
    write(os.path.join(WEB, "robots.txt"), txt)
    print("  ✓ robots.txt")


def gen_404():
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>页面不存在 404 | SMS Hub 免费接码</title>
<meta name="robots" content="noindex,follow">
<meta name="theme-color" content="#070B12">
<link rel="icon" href="/assets/brand/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/app.css">
<style>
.nf{{min-height:62vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:60px 20px}}
.nf img{{width:170px;height:auto;margin-bottom:18px}}
.nf h1{{font-size:30px;margin:0 0 10px;font-weight:800}}
.nf p{{color:var(--text-muted);margin:0 0 24px;font-size:15px}}
.nf .acts{{display:flex;gap:12px;flex-wrap:wrap;justify-content:center}}
</style>
</head>
<body>
<header class="hd" id="hd"></header>
<main class="wrap nf">
  <img src="/assets/empty/empty-search.svg" alt="">
  <h1>没有找到这个页面</h1>
  <p>链接可能已失效，或者号码已被移除。你可以回到首页重新选一个号码。</p>
  <div class="acts">
    <a class="btn btn-primary" href="/">回到首页</a>
    <a class="btn" href="/numbers">查看全部号码</a>
    <a class="btn" href="/guide">使用指南</a>
  </div>
</main>
<footer class="ft" id="ft"></footer>
<nav class="bnav" id="bnav" aria-label="底部导航"></nav>
<script type="module">
import {{ renderChrome, renderFooter }} from '/assets/app.js';
renderChrome();
renderFooter();
</script>
</body>
</html>'''
    write(os.path.join(WEB, "404.html"), html)
    print("  ✓ 404.html")


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def main():
    print("SMS Hub · Google SEO 优化")
    print("=" * 48)
    data = load_data()

    print("\n[1/5] 静态页面 TDK / canonical / og / hreflang")
    optimize_static_pages()

    print("\n[2/5] 结构化数据")
    optimize_faq()
    optimize_numbers_itemlist(data)

    print("\n[3/5] 国家静态页生成")
    isos = gen_country_pages(data)

    print("\n[4/5] sitemap / robots / 404")
    gen_sitemap(data, isos)
    gen_robots()
    gen_404()

    print("\n[5/5] 完成")
    print(f"共修改/生成 {len(_changed)} 个文件")


if __name__ == "__main__":
    main()
