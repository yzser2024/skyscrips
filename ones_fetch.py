#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ONE's：抓 FC2 日记 + rocketbbs/jbbs 留言板的 Wayback 快照（原始字节）。"""
import json
import os
import time

import requests

CDX = "https://web.archive.org/cdx/search/cdx"
WB = "https://web.archive.org/web"
OUT = "out"
os.makedirs(OUT + "/diary", exist_ok=True)
os.makedirs(OUT + "/bbs", exist_ok=True)

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (personal-archive/1.0)"})


def cdx(url, match="prefix", limit=4000, tries=3):
    for i in range(tries):
        try:
            r = S.get(CDX, params={
                "url": url, "matchType": match, "output": "json",
                "fl": "timestamp,original,statuscode,mimetype,length",
                "filter": "statuscode:200", "limit": str(limit),
            }, timeout=240)
            if r.status_code != 200:
                print("  CDX %s -> %s" % (url, r.status_code), flush=True)
                time.sleep(10)
                continue
            t = r.text.strip()
            if not t:
                return []
            rows = json.loads(t)
            return rows[1:] if rows else []
        except Exception as e:
            print("  CDX 异常 %s %s" % (url, repr(e)[:100]), flush=True)
            time.sleep(10)
    return []


def grab(ts, orig, dst):
    for attempt in range(3):
        try:
            r = S.get("%s/%sid_/%s" % (WB, ts, orig), timeout=120, allow_redirects=True)
            if r.status_code == 200 and len(r.content) > 200:
                with open(dst, "wb") as f:
                    f.write(r.content)
                return len(r.content)
            time.sleep(4)
        except Exception as e:
            print("    grab err %s %s" % (orig[:60], repr(e)[:60]), flush=True)
            time.sleep(4)
    return 0


def safe(s):
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in s)[:90]


# ---------- 1. 精确 CDX：留言板 ----------
QUERIES = [
    ("rb_www1_bbs", "www1.rocketbbs.com/310/bbs.cgi?id=oneyunn"),
    ("rb_www2_bbs", "www2.rocketbbs.com/310/bbs.cgi?id=oneyunn"),
    ("rb_www5_bbs", "www5.rocketbbs.com/310/bbs.cgi?id=oneyunn"),
    ("rb_www1_page", "www1.rocketbbs.com/310/oneyunn.html"),
    ("rb_www2_page", "www2.rocketbbs.com/310/oneyunn.html"),
    ("rb_www5_page", "www5.rocketbbs.com/310/oneyunn.html"),
    ("jbbs", "yf04.com/cgi-bin/jbbs/jbbs.cgi?id=oneyunn"),
]
bbs_rows = []
for tag, u in QUERIES:
    rows = cdx(u)
    print("%-14s %-45s %d" % (tag, u, len(rows)), flush=True)
    for r in rows[:4]:
        print("   ", " | ".join(str(x) for x in r), flush=True)
    bbs_rows += [(tag,) + tuple(r) for r in rows]
    time.sleep(2)

with open(OUT + "/bbs_cdx.json", "w", encoding="utf-8") as f:
    json.dump(bbs_rows, f, ensure_ascii=False, indent=1)

# ---------- 2. 抓日记 ----------
drows = cdx("diary1.fc2.com/cgi-sys/ed.cgi/oneyunn79")
print("日记快照 %d 条" % len(drows), flush=True)
seen = set()
man = []
for ts, orig, code, mt, ln in drows:
    key = orig
    if key in seen:
        continue
    seen.add(key)
    dst = "%s/diary/%s__%s.html" % (OUT, ts, safe(orig.split("oneyunn79", 1)[-1]) or "index")
    n = grab(ts, orig, dst)
    print("  %s %-60s %d" % (ts, orig[:60], n), flush=True)
    man.append({"ts": ts, "url": orig, "bytes": n, "file": os.path.basename(dst)})
    time.sleep(1.2)

# ---------- 3. 抓留言板 ----------
seen = set()
for tag, ts, orig, code, mt, ln in bbs_rows:
    if orig in seen:
        continue
    seen.add(orig)
    dst = "%s/bbs/%s__%s__%s.html" % (OUT, tag, ts, safe(orig.split("/310/", 1)[-1]) or "index")
    n = grab(ts, orig, dst)
    print("  [%s] %s %-50s %d" % (tag, ts, orig[:50], n), flush=True)
    man.append({"ts": ts, "url": orig, "bytes": n, "file": "bbs/" + os.path.basename(dst), "tag": tag})
    time.sleep(1.2)

with open(OUT + "/manifest.json", "w", encoding="utf-8") as f:
    json.dump(man, f, ensure_ascii=False, indent=1)

ok = sum(1 for m in man if m["bytes"] > 0)
print("完成：%d / %d" % (ok, len(man)), flush=True)
