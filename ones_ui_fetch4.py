#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第四批：快速版。单 URL 查 CDX 拿时间戳，再取原字节。
每个请求 15 秒超时、失败不重试，宁可少拿也不拖住整批。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_ui"
UA = {"User-Agent": "Mozilla/5.0 (archive-research)"}


def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        return None


def cdx_ts(url):
    q = ("http://web.archive.org/cdx/search/cdx?url=%s&output=json&fl=timestamp,statuscode"
         "&filter=statuscode:200&limit=-3" % urllib.parse.quote(url, safe=""))
    b = fetch(q)
    if not b:
        return None
    try:
        rows = json.loads(b.decode("utf-8", "replace"))
    except Exception:
        return None
    if len(rows) < 2:
        return None
    return rows[-1][0]


def flat(url):
    s = re.sub(r"^https?://", "", url)
    s = re.sub(r"[^0-9A-Za-z._-]", "_", s)
    return re.sub(r"_{2,}", "_", s)[-120:]


EMO = ["e1", "e2", "e3", "e4", "e5", "e6"]
WEA = ["w1", "w2", "w3", "w6"]
ARR = ["next_m1", "next_m2", "prev_m1", "prev_m2", "spacer"]
IMG_D = ["2004_8/3", "2004_8/6", "2004_8/26", "2004_8/27", "2004_8/29",
         "2004_9/1", "2004_9/2", "2004_9/5", "2004_9/16", "2004_9/20",
         "2004_9/22", "2004_9/23", "2004_11/5", "2004_11/16"]
SITE = ["index.html", "toppage.html", "menu.html", "bgmmenu.html", "mu.html",
        "bodypage.html", "bbs.html", "about.html", "midipage.html",
        "ld.html", "wordspage.html", "bana.html", "ring.html",
        "title1.jpg", "01.jpg", "023.jpg", "bbs.jpg", "ld.jpg", "ss04b.jpg",
        "film.jpg", "i_po5.gif"]
JBBS = ["003/table/00.gif", "003/table/c01.gif", "003/table/c02.gif", "003/table/c03.gif",
        "003/table/c04.gif", "003/table/d02.gif", "003/table/d03.gif", "003/table/d05.gif",
        "003/line.gif", "003/banner/00.gif", "003/banner/write.gif", "003/banner/home.gif"]


def targets():
    out = []
    for e in EMO:
        out.append(("fc2img", "http://diary1.fc2.com/img/emotion/%s.gif" % e))
    for w in WEA:
        out.append(("fc2img", "http://diary1.fc2.com/img/weather/%s.gif" % w))
    for a in ARR:
        out.append(("fc2img", "http://diary1.fc2.com/img/%s.gif" % a))
    for d in IMG_D:
        out.append(("fc2user", "http://diary1.fc2.com/user/oneyunn79/img/%s.jpg" % d))
    for s in SITE:
        out.append(("site", "http://oneyunn79.client.jp/" + s))
    for j in JBBS:
        out.append(("jbbsskin", "http://yf04.com/cgi-bin/jbbs/" + j))
    return out


def main():
    man = []
    t0 = time.time()
    for sub, u in targets():
        if time.time() - t0 > 900:
            print("time budget reached", flush=True)
            break
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
        name = flat(u)
        p = os.path.join(OUT, sub, name)
        if os.path.exists(p) and os.path.getsize(p) > 500:
            man.append({"url": u, "file": sub + "/" + name, "skip": 1})
            continue
        ts = cdx_ts(u)
        if not ts:
            print("  no cdx", u, flush=True)
            continue
        b = fetch("https://web.archive.org/web/%sid_/%s" % (ts, u), timeout=20)
        if not b or len(b) < 100:
            print("  miss", u, len(b) if b else 0, flush=True)
            continue
        open(p, "wb").write(b)
        man.append({"url": u, "ts": ts, "file": sub + "/" + name, "size": len(b)})
        print("  ok %7d %s" % (len(b), name), flush=True)
    json.dump(man, open(os.path.join(OUT, "manifest4.json"), "w"), ensure_ascii=False, indent=1)
    print("done", len([m for m in man if m.get("file")]), "/", len(targets()))


if __name__ == "__main__":
    main()
