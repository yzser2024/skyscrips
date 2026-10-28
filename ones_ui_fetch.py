#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓 ONE's 母站全站 + FC2 日记素材 + yf04 jbbs 素材，用于复原原始 UI。
输出 out_ui/<host>/<flattened name>，并写 manifest.json。
"""
import json
import os
import re
import time
import urllib.request
import urllib.error
import urllib.parse

OUT = "out_ui"
CDX = "http://web.archive.org/cdx/search/cdx"


def get(url, tries=6, timeout=90):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (archive-research)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            print("  retry %d %s %s" % (i + 1, url[:90], e), flush=True)
            time.sleep(15 + 10 * i)
    print("  FAIL", url, last, flush=True)
    return None


def cdx(url, match="prefix", filt="statuscode:200", limit=4000):
    q = "%s?url=%s&matchType=%s&output=json&fl=original,timestamp,mimetype,statuscode&filter=%s&limit=%d" % (
        CDX, urllib.parse.quote(url, safe=""), match, filt, limit)
    for i in range(6):
        b = get(q, tries=1)
        if b:
            try:
                rows = json.loads(b.decode("utf-8", "replace"))
                return rows[1:] if rows else []
            except Exception:
                pass
        time.sleep(20 + 10 * i)
    return []


def flat(url):
    s = re.sub(r"^https?://", "", url)
    s = re.sub(r"[^0-9A-Za-z._-]", "_", s)
    s = re.sub(r"_{2,}", "_", s)
    return s[-120:]


def grab(rows, sub, want=None, newest_only=True):
    """rows: [original, ts, mime, status]. 每个 original 取最新快照。"""
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    best = {}
    for r in rows:
        if len(r) < 4 or r[3] != "200":
            continue
        u, ts = r[0], r[1]
        if want and not re.search(want, u):
            continue
        if u not in best or ts > best[u]:
            best[u] = ts
    man = []
    for u, ts in sorted(best.items()):
        name = flat(u)
        p = os.path.join(OUT, sub, name)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            man.append({"url": u, "ts": ts, "file": sub + "/" + name, "skip": 1})
            continue
        b = get("https://web.archive.org/web/%sid_/%s" % (ts, u))
        if b is None:
            continue
        open(p, "wb").write(b)
        man.append({"url": u, "ts": ts, "file": sub + "/" + name, "size": len(b)})
        print("  ok %7d %s" % (len(b), name), flush=True)
    return man


def main():
    os.makedirs(OUT, exist_ok=True)
    man = []
    print("=== CDX oneyunn79.client.jp", flush=True)
    r = cdx("oneyunn79.client.jp", "domain")
    print("  rows", len(r), flush=True)
    man += grab(r, "site")
    print("=== CDX diary1.fc2.com/img", flush=True)
    r = cdx("diary1.fc2.com/img/", "prefix")
    print("  rows", len(r), flush=True)
    man += grab(r, "fc2img")
    print("=== CDX yf04.com/cgi-bin/jbbs/003", flush=True)
    r = cdx("yf04.com/cgi-bin/jbbs/003/", "prefix")
    print("  rows", len(r), flush=True)
    man += grab(r, "jbbsskin")
    json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), ensure_ascii=False, indent=1)
    print("total", len(man))


if __name__ == "__main__":
    import urllib.parse
    main()
