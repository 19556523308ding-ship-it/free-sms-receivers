#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回填 numbers.json 里缺失/错误的英文国名与中文名。

采集器的 COUNTRY_ISO / COUNTRY_EN 是权威来源，这里直接同步过来，
不用等下一轮全量采集。顺带修正 PR 这类表外国家（原本 nameZh=nameEn="PR"）。
用法：python tools/backfill-country-names.py
"""
import os
import io
import re
import json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(BASE, "web")
COLLECT = os.path.join(BASE, "scrapers", "collect.py")
DATA = os.path.join(WEB, "data", "numbers.json")


def parse_map(src, name):
    """从 collect.py 里抠出 XXX = { "US": (...), ... } 这类字典"""
    m = re.search(name + r"\s*=\s*\{([\s\S]*?)\n\}", src)
    if not m:
        raise SystemExit(f"未找到 {name}")
    out = {}
    for line in m.group(1).splitlines():
        mm = re.match(r'\s*"([A-Z]{2})"\s*:\s*(.+?),?\s*$', line)
        if not mm:
            continue
        iso, rest = mm.group(1), mm.group(2)
        if name == "COUNTRY_ISO":
            v = re.findall(r'"([^"]*)"', rest)
            out[iso] = (v[0], v[1] if len(v) > 1 else "", v[2] if len(v) > 2 else "")
        else:
            v = re.findall(r'"([^"]*)"', rest)
            out[iso] = v[0] if v else iso
    return out


def main():
    src = io.open(COLLECT, encoding="utf-8").read()
    zh = {k: v[0] for k, v in parse_map(src, "COUNTRY_ISO").items()}
    en = parse_map(src, "COUNTRY_EN")

    data = json.loads(io.open(DATA, encoding="utf-8").read())
    fixed_c, fixed_n = [], []

    for c in data.get("countries", []):
        iso = c.get("iso")
        if not iso:
            continue
        nz, ne = zh.get(iso), en.get(iso)
        if nz and c.get("nameZh") != nz:
            fixed_c.append(f"  {iso} nameZh {c.get('nameZh')!r} -> {nz!r}")
            c["nameZh"] = nz
        if ne and c.get("nameEn") != ne:
            fixed_c.append(f"  {iso} nameEn {c.get('nameEn')!r} -> {ne!r}")
            c["nameEn"] = ne

    for n in data.get("numbers", []):
        iso = n.get("countryCode")
        if not iso:
            continue
        nz, ne = zh.get(iso), en.get(iso)
        if nz and n.get("countryNameZh") != nz:
            n["countryNameZh"] = nz
            fixed_n.append(iso)
        if ne and n.get("countryNameEn") != ne:
            n["countryNameEn"] = ne

    io.open(DATA, "w", encoding="utf-8", newline="\n").write(
        json.dumps(data, ensure_ascii=False, indent=1))

    print("国家表修正：")
    for x in fixed_c or ["  （无需修正）"]:
        print(x)
    print(f"号码记录同步英文/中文名：{len(fixed_n)} 条")

    # 复核
    chk = json.loads(io.open(DATA, encoding="utf-8").read())
    missing = [c["iso"] for c in chk["countries"]
               if not c.get("nameEn") or c["nameEn"] == c["iso"]]
    print(f"仍缺英文名的国家：{missing or '无 ✓'}")


if __name__ == "__main__":
    main()
