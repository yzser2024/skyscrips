# -*- coding: utf-8 -*-
"""probe6: 把 instagram.com/ucaliy17 的 2020-11-01 存档整页抓下来，
解析 biography / full_name / external_url / 帖子缩略图 alt。
再顺手查同一 handle 在别处有没有。
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

OUT = "out_ua6"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    line = "%s %s" % (time.strftime("%H:%M:%S"), s)
    print(line, flush=True)
    LOG.write(line + "\n")
    LOG.flush()


def get(url, timeout=50):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(3000000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            return e.code, e.read(300000).decode("utf-8", "replace")
        except Exception:
            return e.code, ""
    except Exception as e:
        return None, str(e)[:80]


res = {}
for ts in ["20201101133102", "20201101235223"]:
    u = "http://web.archive.org/web/%sid_/https://www.instagram.com/ucaliy17/" % ts
    st, b = get(u)
    note("%s status=%s len=%d" % (ts, st, len(b or "")))
    open(OUT + "/ig_%s.html" % ts, "w", encoding="utf-8").write(b or "")
    res[ts] = {"status": st, "len": len(b or "")}
    time.sleep(8)

# 解析
for ts in res:
    p = OUT + "/ig_%s.html" % ts
    if not os.path.exists(p):
        continue
    h = open(p, encoding="utf-8", errors="replace").read()
    note("=== parse %s" % ts)
    for key in ["biography", "full_name", "external_url", "edge_followed_by",
                "edge_owner_to_timeline_media", "business_email", "category_name"]:
        for m in re.finditer(r'"%s"\s*:\s*(".*?"|\{.*?\}|[0-9]+)' % key, h):
            s = m.group(1)
            note("  %s = %s" % (key, s[:300]))
            break
    # og
    for prop in ["og:title", "og:description", "og:url", "og:image"]:
        m = re.search(r'property=["\']%s["\'][^>]+content=["\'](.*?)["\']' % prop, h, re.S)
        if m:
            note("  %s: %s" % (prop, m.group(1)[:300]))
    # 图片 alt（帖子描述）
    alts = re.findall(r'alt="([^"]{10,200})"', h)
    seen = []
    for a in alts:
        if a not in seen:
            seen.append(a)
    note("  alt(%d): %s" % (len(seen), " || ".join(seen[:8])))

json.dump(res, open(OUT + "/meta.json", "w"), ensure_ascii=False, indent=1)
note("DONE")
