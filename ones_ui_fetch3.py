#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第三批：按已知 URL 清单直接取 Wayback 最近快照（不查 CDX），只抓这几十个文件。
web/2004id_/URL 会让 Wayback 自己挑最接近 2004 的快照，一次请求一个文件。
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ones_ui_fetch import get, flat, OUT  # noqa

EMO = ["e1", "e2", "e3", "e4", "e5", "e6"]
WEA = ["w1", "w2", "w3", "w6"]
ARR = ["next_m1", "next_m2", "prev_m1", "prev_m2", "spacer"]
IMG_D = ["2004_8/3", "2004_8/6", "2004_8/26", "2004_8/27", "2004_8/29",
         "2004_9/1", "2004_9/2", "2004_9/5", "2004_9/16", "2004_9/20",
         "2004_9/22", "2004_9/23", "2004_11/5", "2004_11/16"]
SITE = ["index.html", "toppage.html", "menu.html", "bgmmenu.html", "mu.html",
        "bodypage.html", "bbs.html", "about.html", "info.html", "midipage.html",
        "ld.html", "wordspage.html", "bana.html", "ring.html",
        "title1.jpg", "01.jpg", "023.jpg", "bbs.jpg", "ld.jpg", "ss04b.jpg",
        "film.jpg", "i_po5.gif", "terra.mid", "dollfc.jpg", "s8a.gif", "bisyounenn.jpg",
        "smile.jpg", "bump.jpg", "color.jpg", "k_3.jpg", "larclove.jpg",
        "ban_200.jpg", "waku2.gif", "navi.gif", "206.gif", "0574.jpg", "31_31_1.gif"]
JBBS = ["003/table/00.gif", "003/table/c01.gif", "003/table/c02.gif", "003/table/c03.gif",
        "003/table/c04.gif", "003/table/d02.gif", "003/table/d03.gif", "003/table/d05.gif",
        "003/line.gif", "003/banner/00.gif", "003/banner/write.gif", "003/banner/home.gif",
        "003/banner/res.gif", "003/banner/mail.gif"]


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
    os.makedirs(OUT, exist_ok=True)
    man = []
    for sub, u in targets():
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
        name = flat(u)
        p = os.path.join(OUT, sub, name)
        if os.path.exists(p) and os.path.getsize(p) > 500:
            man.append({"url": u, "file": sub + "/" + name, "skip": 1})
            continue
        b = get("https://web.archive.org/web/2004id_/" + u, tries=3)
        if b is None or len(b) < 200:
            print("  miss %s (%s)" % (u, len(b) if b else 0), flush=True)
            man.append({"url": u, "file": None, "size": 0})
            continue
        open(p, "wb").write(b)
        man.append({"url": u, "file": sub + "/" + name, "size": len(b)})
        print("  ok %7d %s" % (len(b), name), flush=True)
    json.dump(man, open(os.path.join(OUT, "manifest3.json"), "w"), ensure_ascii=False, indent=1)
    ok = sum(1 for m in man if m.get("file"))
    print("done", ok, "/", len(man))


if __name__ == "__main__":
    main()
