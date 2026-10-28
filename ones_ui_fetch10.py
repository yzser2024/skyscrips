#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补抓 BBS 皮肤：jbbs 的 003/*（线、表格、按钮）、rocketbbs 站徽、板背景。
先 CDX 列存档，再按魔数校验下载。只为确认真图是否存在。
"""
import json
import os
import time
import urllib.parse
import urllib.request

OUT = "out_ui/skin"
CDX = "http://web.archive.org/cdx/search/cdx"

TARGETS = [
    # jbbs 皮肤（相对 http://yf04.com/cgi-bin/jbbs/）
    "http://yf04.com/cgi-bin/jbbs/003/line.gif",
    "http://yf04.com/cgi-bin/jbbs/003/table/00.gif",
    "http://yf04.com/cgi-bin/jbbs/003/table/a02.gif",
    "http://yf04.com/cgi-bin/jbbs/003/table/a03.gif",
    "http://yf04.com/cgi-bin/jbbs/003/table/c01.gif",
    "http://yf04.com/cgi-bin/jbbs/003/table/c02.gif",
    "http://yf04.com/cgi-bin/jbbs/003/table/c03.gif",
    "http://yf04.com/cgi-bin/jbbs/003/table/c04.gif",
    "http://yf04.com/cgi-bin/jbbs/003/table/c05.gif",
    "http://yf04.com/cgi-bin/jbbs/003/table/d02.gif",
    "http://yf04.com/cgi-bin/jbbs/003/table/d03.gif",
    "http://yf04.com/cgi-bin/jbbs/003/table/d05.gif",
    "http://yf04.com/cgi-bin/jbbs/003/banner/00.gif",
    "http://yf04.com/cgi-bin/jbbs/003/banner/back.gif",
    "http://yf04.com/cgi-bin/jbbs/003/banner/home.gif",
    "http://yf04.com/cgi-bin/jbbs/003/banner/mail.gif",
    "http://yf04.com/cgi-bin/jbbs/003/banner/next.gif",
    "http://yf04.com/cgi-bin/jbbs/003/banner/write.gif",
    # 板背景
    "http://oneyunn79.client.jp/film.jpg",
    "http://oneyunn79.client.jp/film.gif",
]


def cdx(url):
    q = {"url": url, "output": "json", "matchType": "prefix",
         "fl": "timestamp,original,statuscode,mimetype,length",
         "collapse": "urlkey", "limit": "300"}
    u = CDX + "?" + urllib.parse.urlencode(q)
    for i in range(5):
        try:
            with urllib.request.urlopen(u, timeout=60) as r:
                d = json.load(r)
            return d[1:] if d else []
        except Exception as e:
            print("cdx retry", i, url, e)
            time.sleep(8)
    return []


def is_img(b):
    return (b.startswith(b"GIF8") or b.startswith(b"\xff\xd8\xff")
            or b.startswith(b"\x89PNG") or b[:4] == b"RIFF")


def grab(ts, url, dest):
    for tmpl in ("https://web.archive.org/web/%sid_/%s", "https://web.archive.org/web/%sif_/%s"):
        u = tmpl % (ts, url)
        try:
            with urllib.request.urlopen(u, timeout=40) as r:
                b = r.read()
            if len(b) < 60 or not is_img(b):
                print("  notimg", len(b), url)
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, "wb").write(b)
            print("ok", len(b), url)
            return True
        except Exception as e:
            print("  err", type(e).__name__, url)
            time.sleep(2)
    return False


def main():
    os.makedirs(OUT, exist_ok=True)
    report = []
    for url in TARGETS:
        rows = cdx(url)
        got = None
        for ts, orig, sc, mt, ln in rows:
            if sc == "200" and orig.split("?")[0] == url:
                got = (ts, orig)
        rel = url.split("://", 1)[1].replace("/", "__")
        dest = os.path.join(OUT, rel)
        line = {"url": url, "cdx": len(rows), "hit": bool(got)}
        if got:
            line["ts"] = got[0]
            line["saved"] = grab(got[0], url, dest)
        else:
            print("nohit", url)
        report.append(line)
    open("out_ui/skin_report.json", "w").write(json.dumps(report, ensure_ascii=False, indent=1))
    ok = sum(1 for r in report if r.get("saved"))
    print("=== 命中 %d / 目标 %d，落盘 %d" % (sum(1 for r in report if r["hit"]), len(TARGETS), ok))
    for r in report:
        print("%-6s %-4s %s" % ("saved" if r.get("saved") else "MISS", r["cdx"], r["url"]))


if __name__ == "__main__":
    main()
