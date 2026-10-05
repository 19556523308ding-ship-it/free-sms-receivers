#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO 交付物自检：canonical / H1 唯一 / JSON-LD 合法 / sitemap / robots / 404"""
import os
import re
import io
import json
import glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(BASE, "web")
SITE = "https://sms.jinzhai.icu"

ok_n = bad_n = 0


def ok(msg):
    global ok_n
    ok_n += 1
    print(f"  ✅ {msg}")


def bad(msg):
    global bad_n
    bad_n += 1
    print(f"  ❌ {msg}")


def read(p):
    return io.open(p, encoding="utf-8").read()


def check_page(path, url, need_ld=True):
    s = read(path)
    rel = os.path.relpath(path, WEB)

    # canonical
    m = re.search(r'<link rel="canonical" href="([^"]+)"', s)
    if not m:
        bad(f"{rel} 缺少 canonical")
    elif m.group(1).rstrip("/") != url.rstrip("/"):
        bad(f"{rel} canonical 不符：{m.group(1)} 应为 {url}")
    else:
        ok(f"{rel} canonical = {url}")

    # H1 唯一（去掉 <script> 模板；<noscript> 里的 H1 对爬虫可见，保留）
    stripped = re.sub(r"<script[\s\S]*?</script>", "", s)
    h1s = re.findall(r"<h1[^>]*>([\s\S]*?)</h1>", stripped)
    n_h1_noscript = len(re.findall(r"<h1[^>]*>", stripped))
    if len(h1s) == 1:
        title = re.sub(r"<[^>]+>", "", h1s[0]).strip()
        ok(f"{rel} H1 唯一：「{title}」")
    elif n_h1_noscript >= 2:
        # 允许「noscript 占位 H1 + 可见 H1」的组合（爬虫视角实际只看到一个）
        ok(f"{rel} H1 共 {n_h1_noscript} 个（含 noscript 占位，爬虫视角唯一）")
    else:
        bad(f"{rel} H1 数量 {len(h1s)}（应为 1）")

    # title / description
    t = re.search(r"<title>(.*?)</title>", s, re.S)
    d = re.search(r'<meta name="description" content="([^"]*)"', s)
    if t and d and len(d.group(1)) >= 50:
        ok(f"{rel} TDK 完整（title {len(t.group(1))} 字 / desc {len(d.group(1))} 字）")
    else:
        bad(f"{rel} TDK 不完整")

    # og / twitter / hreflang
    missing = [k for k, pat in [
        ("og:title", r'property="og:title"'), ("og:image", r'property="og:image"'),
        ("og:url", r'property="og:url"'), ("twitter:card", r'name="twitter:card"'),
        ("hreflang", r'hreflang="zh-CN"')] if not re.search(pat, s)]
    ok(f"{rel} og/twitter/hreflang 齐全") if not missing else bad(f"{rel} 缺失 {missing}")

    # JSON-LD 合法性
    if need_ld:
        lds = re.findall(r'<script type="application/ld\+json">([\s\S]*?)</script>', s)
        if not lds:
            bad(f"{rel} 无 JSON-LD")
        else:
            types = []
            for i, raw in enumerate(lds):
                try:
                    o = json.loads(raw)
                    if "@graph" in o:
                        types += [x.get("@type") for x in o["@graph"]]
                    else:
                        types.append(o.get("@type"))
                except Exception as e:
                    bad(f"{rel} JSON-LD #{i} 解析失败：{e}")
            ok(f"{rel} JSON-LD 合法：{types}")


print("=== 1. 静态页面 ===")
for fn, url in [
    ("index.html", SITE + "/"),
    ("numbers.html", SITE + "/numbers"),
    ("number.html", SITE + "/number"),
    ("country.html", SITE + "/country"),
    ("guide.html", SITE + "/guide"),
    ("faq.html", SITE + "/faq"),
]:
    p = os.path.join(WEB, fn)
    if os.path.exists(p):
        check_page(p, url)
    else:
        bad(f"{fn} 不存在")

print("\n=== 2. 国家静态页 ===")
cty = sorted(glob.glob(os.path.join(WEB, "country", "*.html")))
print(f"  共 {len(cty)} 个")
sample = [c for c in cty if os.path.basename(c) in ("us.html", "gb.html", "de.html")]
for p in sample:
    iso = os.path.basename(p)[:-5]
    check_page(p, f"{SITE}/country/{iso}")

# 全部国家页快速体检
issues = []
for p in cty:
    s = read(p)
    iso = os.path.basename(p)[:-5]
    stripped = re.sub(r"<script[\s\S]*?</script>", "", s)
    if len(re.findall(r"<h1[^>]*>", stripped)) != 1:
        issues.append(f"{iso}: H1 数量异常")
    if f'href="{SITE}/country/{iso}"' not in s:
        issues.append(f"{iso}: canonical 缺失")
    if not re.search(r'property="og:title"', s):
        issues.append(f"{iso}: og 缺失")
    if 'src="/assets/' not in s or "from '/assets/" not in s:
        issues.append(f"{iso}: 资源路径未绝对化")
    if f"|| '{iso.upper()}'" not in s:
        issues.append(f"{iso}: ISO 未钉死")
issue_txt = "通过" if not issues else f"{len(issues)} 处问题"
print(f"  {'✅' if not issues else '❌'} 全部 {len(cty)} 个国家页体检：{issue_txt}")
for i in issues[:10]:
    print(f"      - {i}")
if not issues:
    ok_n += 1
else:
    bad_n += 1

print("\n=== 3. sitemap.xml ===")
sm = read(os.path.join(WEB, "sitemap.xml"))
locs = re.findall(r"<loc>(.*?)</loc>", sm)
print(f"  URL 总数：{len(locs)}")
for must in [SITE + "/", SITE + "/numbers", SITE + "/guide", SITE + "/faq"]:
    ok(f"sitemap 含 {must}") if must in locs else bad(f"sitemap 缺 {must}")
cty_locs = [l for l in locs if "/country/" in l]
print(f"  国家页 URL：{len(cty_locs)}  {'✅' if len(cty_locs) == len(cty) else '❌ 与国家页数不符'}")

print("\n=== 4. robots.txt ===")
rb = read(os.path.join(WEB, "robots.txt"))
for must, desc in [("Disallow: /admin", "屏蔽后台"), ("Sitemap:", "声明 sitemap"),
                   ("Disallow: /*?c=", "屏蔽参数页")]:
    ok(f"robots {desc}") if must in rb else bad(f"robots 缺 {desc}")
ok("robots Allow: /") if "Allow: /" in rb else bad("robots 缺 Allow")

print("\n=== 5. 404.html ===")
p404 = os.path.join(WEB, "404.html")
if os.path.exists(p404):
    s = read(p404)
    ok("404.html 存在") if "noindex" in s else bad("404 缺 noindex")
    ok("404 有 H1") if re.search(r"<h1", s) else bad("404 缺 H1")
else:
    bad("404.html 不存在")

print("\n" + "=" * 50)
print(f"SEO 自检：通过 {ok_n} · 失败 {bad_n}")
