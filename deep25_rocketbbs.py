#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deep25: 从海外节点探测 rocketbbs 651 板是否还活着，并试探 archive.org 可达性。"""
import gzip
import io
import json
import os
import ssl
import urllib.error
import urllib.request

OUT = "out_deep25"
os.makedirs(OUT, exist_ok=True)

UAS = {
    "chrome_win": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "safari_mac": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                   "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"),
    "docomo": ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
               "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"),
}

TARGETS = [
    ("www5", "http://www5.rocketbbs.com/651/oneday.html"),
    ("www5-rss", "http://www5.rocketbbs.com/651/rss/oneday.rdf"),
    ("www5-bbs", "http://www5.rocketbbs.com/651/bbs.cgi?id=oneday"),
    ("www5-root", "http://www5.rocketbbs.com/651/"),
    ("www5-top", "http://www5.rocketbbs.com/"),
    ("www-https", "https://www.rocketbbs.com/651/oneday.html"),
    ("www-root", "https://www.rocketbbs.com/"),
    ("www3", "http://www3.rocketbbs.com/651/oneday.html"),
    ("www1", "http://www1.rocketbbs.com/610/withr.html"),
]

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

log = []


def get(url, ua, timeout=45):
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en;q=0.8",
        "Connection": "close",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        b = r.read()
        if b[:2] == b"\x1f\x8b":
            try:
                b = gzip.decompress(b)
            except Exception:
                pass
        return r.status, r.geturl(), b


def main():
    # 0) 网络基线
    for name, u in [("arch", "https://archive.org/"),
                    ("google", "https://www.google.com/")]:
        try:
            st, _, b = get(u, UAS["chrome_win"], 30)
            log.append("BASELINE %-8s %s %d bytes" % (name, st, len(b)))
        except Exception as e:
            log.append("BASELINE %-8s FAIL %s" % (name, e))

    # 1) 逐个目标
    for tag, url in TARGETS:
        for uan in ("chrome_win", "safari_mac", "docomo"):
            try:
                st, real, b = get(url, UAS[uan])
                txt = b.decode("cp932", "replace")
                sig = txt[:200].replace("\n", " ")[:180]
                log.append("OK   %-10s %-12s %s %6d  %s" % (tag, uan, st, len(b), sig))
                if st == 200 and len(b) > 500:
                    fn = "%s/%s__%s.html" % (OUT, tag, uan)
                    open(fn, "wb").write(b)
                    log.append("     saved -> %s" % fn)
                    break
            except urllib.error.HTTPError as e:
                body = b""
                try:
                    body = e.read()[:200]
                except Exception:
                    pass
                log.append("ERR  %-10s %-12s HTTP %s  %s" % (
                    tag, uan, e.code, body.decode("cp932", "replace").replace("\n", " ")[:90]))
            except Exception as e:
                log.append("FAIL %-10s %-12s %s" % (tag, uan, str(e)[:90]))

    txt = "\n".join(log)
    print(txt)
    open(OUT + "/log.txt", "w", encoding="utf-8").write(txt)


if __name__ == "__main__":
    main()
