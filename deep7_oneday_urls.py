#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第七轮：用多域名 + 多参数入口，把 oneday 板的第 3、4 页挖出来。

上一轮失败原因：/651/bbs.cgi 是共享路径，别人板的页面把 CDX 结果挤满了，
按前缀查 id=oneday 拿到 0 条。这轮改成逐个 URL 精确查。
"""
import itertools
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep7"
CDX = "http://web.archive.org/cdx/search/cdx"
UA = {"User-Agent": "Mozilla/5.0 (research)"}

HOSTS = ["www5.rocketbbs.com", "www.rocketbbs.com", "www2.rocketbbs.com",
         "www3.rocketbbs.com", "www4.rocketbbs.com", "www6.rocketbbs.com",
         "www7.rocketbbs.com", "rocketbbs.com"]


def cdx(url, limit=120):
    p = {"url": url, "output": "json", "matchType": "exact",
         "fl": "timestamp,original,statuscode,mimetype,length,digest",
         "limit": str(limit)}
    u = CDX + "?" + urllib.parse.urlencode(p)
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=80) as r:
                b = r.read()
            if not b.strip():
                return []
            d = json.loads(b)
            return d[1:] if d else []
        except Exception:
            time.sleep(5)
    return []


def grab(ts, url, dest, minlen=800):
    u = "https://web.archive.org/web/%sid_/%s" % (ts, url)
    for i in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=50) as r:
                b = r.read()
            if len(b) < minlen:
                return 0
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(b)
            return len(b)
        except Exception:
            time.sleep(2)
    return 0


def main():
    os.makedirs(OUT, exist_ok=True)
    hits = []

    # 各种入口形态
    variants = []
    for host in HOSTS:
        variants.append("http://%s/651/oneday.html" % host)
        for pg in range(1, 21):
            variants.append("http://%s/651/bbs.cgi?id=oneday&page=%d" % (host, pg))
        variants.append("http://%s/651/bbs.cgi?id=oneday" % host)
        variants.append("http://%s/651/user.cgi?mode=mobile&id=oneday" % host)
        variants.append("http://%s/651/rss/oneday.rdf" % host)
        for mode in ("find", "past", "log", "list", "all", "tree"):
            variants.append("http://%s/651/bbs.cgi?id=oneday&mode=%s" % (host, mode))
        # 每页条数放大
        for n in (50, 100, 200):
            variants.append("http://%s/651/bbs.cgi?id=oneday&n=%d" % (host, n))

    print("待查入口", len(variants))
    for v in variants:
        rows = [r for r in cdx(v) if r[2] == "200"]
        if not rows:
            continue
        print("HIT", v, len(rows), [r[0] for r in rows][:6])
        for ts, orig, sc, mt, ln, dg in rows:
            hits.append((v, ts, orig, int(ln or 0)))

    print("命中合计", len(hits))
    # 去重：同 URL 同 ts
    seen = set()
    ok = 0
    for v, ts, orig, ln in hits:
        if (ts, orig) in seen:
            continue
        seen.add((ts, orig))
        q = urllib.parse.parse_qs(urllib.parse.urlparse(orig).query)
        pg = (q.get("page") or ["1"])[0]
        mode = (q.get("mode") or ["-"])[0]
        name = "p%02d_%s_%s.html" % (int(pg) if pg.isdigit() else 1, mode, ts)
        n = grab(ts, orig, os.path.join(OUT, "pages", name))
        if n:
            ok += 1
            print("   saved", name, n)
    print("抓下", ok)
    json.dump(hits, open(os.path.join(OUT, "hits.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
