#!/usr/bin/env python3
"""
号码可达性探测 —— 给 direct inbox 号码补充真实的 fetch_success_rate。

为什么必须做（2026-10-05 实测发现）：
  仅凭「号码来自哪个源」判断能否站内收码是不准的。
  实测 receiveasmsonline 上有号码返回 403（如 +447400123456），
  而同国其它号码（+447097957757 / +447300650678）完全正常，
  源站国家页本身也是 200。
  也就是说：**「源可用」不等于「每个号都可用」**，必须逐号验证。

策略：轮转探测，每次跑一批（默认 40 个），
  把结果累计进 data/number-probe.json，
  采集器读取该档案给号码打上 reachable / fetch_success_rate。
  这样几轮之后，364 个号码的可达性画像就建立起来了，
  且不会对源站造成压力（走本地 reader，本身有 15s 限频）。
"""
import json
import os
import random
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data", "numbers.json")
PROBE = os.path.join(BASE, "data", "number-probe.json")
READER = "http://127.0.0.1:18620/api/sms"

# 与后端限频配合：同号码 15s，串行 + 间隔即可，无需额外节流
BATCH = int(os.environ.get("PROBE_BATCH", "40"))
GAP = float(os.environ.get("PROBE_GAP", "1.0"))


def slug_of(rec):
    """把国家 ISO 转成源站路径段。源站用全称连字符形式。"""
    return (rec.get("countryNameEn") or "").strip().lower().replace(" ", "-")


def probe(phone, slug, timeout=45):
    """
    返回 (ok, err, count)。

    关键：429 与 403 必须区分对待。
      429 = 本站 IP 限频（12 次/分钟）—— 这是「我们自己打太快」，
            不代表号码不可用，**绝不能计入失败率**，否则会把
            好号码误判成坏号码（实测首批 24 个里后 12 个全 429，
            若直接记失败，成功率会被腰斩成 50%）。
      403 = 源站拒绝该号码 —— 这才是真的不可达。
    """
    url = f"{READER}?slug={urllib.parse.quote(slug)}&phone={urllib.parse.quote(phone)}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
        if d.get("error"):
            return None, d.get("error"), 0   # None = 不确定（限流）
        return True, None, d.get("count", 0)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return None, "HTTP 429(限流)", 0   # 不算失败，也不算成功
        return False, f"HTTP {e.code}", 0
    except Exception as e:
        return None, f"{type(e).__name__}", 0  # 网络抖动同样不计入失败


def main():
    if not os.path.exists(DATA):
        print("找不到 numbers.json")
        return 1

    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)

    targets = [n for n in d["numbers"] if n.get("directInbox")]
    if not targets:
        print("没有 direct inbox 号码，无需探测")
        return 0

    probe_db = {}
    if os.path.exists(PROBE):
        try:
            with open(PROBE, encoding="utf-8") as f:
                probe_db = json.load(f)
        except Exception:
            probe_db = {}

    # 优先探测「从未探过」和「探得最久」的号码（轮转，保证覆盖全部）
    now = time.time()
    targets.sort(key=lambda n: probe_db.get(n["phone"], {}).get("lastProbeAt", 0))

    batch = targets[:BATCH]
    print(f"本轮探测 {len(batch)} / 共 {len(targets)} 个站内号码")

    ok_cnt = fail_cnt = skip_cnt = 0
    for i, rec in enumerate(batch, 1):
        phone = rec["phone"]
        slug = slug_of(rec)
        digits = phone.lstrip("+")
        ok, err, cnt = probe(digits, slug)

        prev = probe_db.get(phone, {})
        attempts = prev.get("attempts", 0)
        successes = prev.get("successes", 0)

        if ok is None:
            # 限流/网络抖动：不采样，只记录观察时间，下轮优先重试
            skip_cnt += 1
            probe_db[phone] = {
                **prev,
                "attempts": attempts,
                "successes": successes,
                "fetch_success_rate": (round(successes / attempts, 3) if attempts else None),
                "lastError": err,
                "lastProbeAt": now if False else prev.get("lastProbeAt", 0),
                "lastSeenAt": now,
                "slug": slug,
            }
        else:
            attempts += 1
            if ok:
                successes += 1
            probe_db[phone] = {
                "attempts": attempts,
                "successes": successes,
                "fetch_success_rate": round(successes / attempts, 3),
                "reachable": ok,
                "lastMessageCount": cnt if ok else prev.get("lastMessageCount", 0),
                "lastError": err,
                "lastProbeAt": now,
                "slug": slug,
            }
            if ok:
                ok_cnt += 1
            else:
                fail_cnt += 1

        mark = "OK  " if ok else ("SKIP" if ok is None else "FAIL")
        print(f"  [{i}/{len(batch)}] {mark} {phone} {rec.get('flag','')} {slug} "
              f"{'msg=' + str(cnt) if ok else err}")

        if i < len(batch):
            # 命中限流就多等一会，避免整批都被 429 吃掉
            time.sleep(GAP * (3.0 if ok is None else 1.0))

    os.makedirs(os.path.dirname(PROBE), exist_ok=True)
    with open(PROBE, "w", encoding="utf-8") as f:
        json.dump(probe_db, f, ensure_ascii=False, indent=2)

    print(f"\n本轮 成功 {ok_cnt} / 不可达 {fail_cnt} / 跳过(限流) {skip_cnt} / 共 {len(batch)}")
    print(f"档案累计 {len(probe_db)} 个号码 -> {PROBE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())