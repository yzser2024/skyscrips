#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探测 Wayback 里 With R / ONE's 相关站点的音频文件快照。"""

import json
import time

import requests

CDX = "https://web.archive.org/cdx/search/cdx"
WB = "https://web.archive.org/web"

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (compatible; personal-archive/1.0)"})

TARGETS = [
    "withr.y.ribbon.to",
    "oneyunn79.client.jp",
    "music.geocities.jp/withr17",
    "yf04.com",
]

AUDIO_EXT = (".mp3", ".wma", ".mid", ".midi", ".wav", ".ra", ".ogg", ".swf")

print("=== 一、按域名列出全部音频类快照 ===\n", flush=True)
hits = []
for host in TARGETS:
    try:
        r = S.get(CDX, params={
            "url": host + "/*", "matchType": "prefix", "output": "json",
            "fl": "timestamp,original,statuscode,mimetype,length",
            "filter": "statuscode:200", "collapse": "urlkey", "limit": "5000",
        }, timeout=240)
        rows = r.json() if r.status_code == 200 and r.text.strip() else []
    except Exception as e:
        print("%-28s 失败 %s" % (host, repr(e)[:80]), flush=True)
        continue
    if not rows:
        print("%-28s 无记录" % host, flush=True)
        continue
    head, data = rows[0], rows[1:]
    print("%-28s 总条目 %d" % (host, len(data)), flush=True)
    for row in data:
        d = dict(zip(head, row))
        orig = d.get("original", "")
        low = orig.lower().split("?")[0]
        if low.endswith(AUDIO_EXT) or "audio" in (d.get("mimetype") or ""):
            hits.append(d)
            print("   %s  %-8s %-10s %s" % (d.get("timestamp"), d.get("length"), d.get("mimetype", "")[:10], orig[:90]), flush=True)
    time.sleep(0.5)

print("\n=== 二、精确查 pp.mp3 的几个候选地址 ===\n", flush=True)
for u in ["withr.y.ribbon.to/pp.mp3", "music.geocities.jp/withr17/pp.mp3",
          "oneyunn79.client.jp/pp.mp3", "yf04.com/pp.mp3"]:
    try:
        r = S.get(CDX, params={"url": u, "output": "json",
                               "fl": "timestamp,original,statuscode,mimetype,length"}, timeout=120)
        txt = r.text.strip()
        print("%-38s → %s" % (u, txt[:220] if txt else "(空)"), flush=True)
    except Exception as e:
        print("%-38s → 失败 %s" % (u, repr(e)[:60]), flush=True)
    time.sleep(0.5)

json.dump(hits, open("audio_hits.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n音频类命中 %d 条，已写入 audio_hits.json" % len(hits), flush=True)

# 有快照就顺手把前 20 个下下来
for i, d in enumerate(hits[:20]):
    ts, orig = d["timestamp"], d["original"]
    name = orig.split("/")[-1].split("?")[0] or ("file%d" % i)
    try:
        r = S.get("%s/%sid_/%s" % (WB, ts, orig), timeout=180)
        if r.status_code == 200 and len(r.content) > 1000:
            open("dl_" + name, "wb").write(r.content)
            print("  下载 %s (%d bytes)" % (name, len(r.content)), flush=True)
    except Exception as e:
        print("  下载失败 %s %s" % (name, repr(e)[:60]), flush=True)
    time.sleep(0.5)
