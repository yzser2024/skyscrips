#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deep26:
A. 跨目录探测 oneday 板（dir 330..999 × wwwN）—— 651 目录删了，但板 id 可能是全局的
B. 抓 610 板 withr 的 1..25 页留言
C. 查 archive.org 上有没有 rocketbbs 相关存档 item
"""
import gzip
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_deep26"
for d in ("", "/pages", "/probe"):
    os.makedirs(OUT + d, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
log = []


def get(url, timeout=40, referer=None):
    h = {"User-Agent": UA, "Accept-Language": "ja", "Connection": "close"}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        b = r.read()
        if b[:2] == b"\x1f\x8b":
            try:
                b = gzip.decompress(b)
            except Exception:
                pass
        return r.status, b


def note(s):
    print(s, flush=True)
    log.append(s)


# ---------- A: 跨目录探测 ----------
def probe_oneday():
    """核心实验：bbs.cgi 的 id 是否与目录无关。
       对照组 = withr（已知在 610 活着）；实验组 = oneday。"""
    tests = [
        ("对照", "http://www1.rocketbbs.com/610/bbs.cgi?id=withr"),
        ("实验", "http://www1.rocketbbs.com/610/bbs.cgi?id=oneday"),
        ("实验", "http://www1.rocketbbs.com/610/oneday.html"),
        ("实验", "http://www1.rocketbbs.com/610/rss/oneday.rdf"),
        ("实验", "http://www1.rocketbbs.com/610/user.cgi?mode=mobile&id=oneday"),
        ("对照", "http://www1.rocketbbs.com/610/user.cgi?mode=mobile&id=withr"),
        ("实验", "http://www5.rocketbbs.com/651/bbs.cgi?id=withr"),
        ("实验", "http://www5.rocketbbs.com/651/bbs.cgi?id=oneday"),
        ("实验", "http://www.rocketbbs.com/610/bbs.cgi?id=oneday"),
        ("实验", "http://www5.rocketbbs.com/651/"),
    ]
    for tag, url in tests:
        try:
            st, b = get(url, 25)
            txt = b.decode("cp932", "replace")
            nos = re.findall(r"No\.(\d+)", txt)
            note("A %s 200 %6d  %-58s  No.%s" % (
                tag, len(b), url.replace("http://", "")[:58],
                (nos[0] + ".." + nos[-1]) if nos else "-"))
            if len(b) > 600:
                fn = "%s/probe/%s.html" % (OUT, re.sub(r"\W+", "_", url)[-60:])
                open(fn, "wb").write(b)
        except urllib.error.HTTPError as e:
            note("A %s HTTP %-3s %-58s" % (tag, e.code, url.replace("http://", "")[:58]))
        except Exception as e:
            note("A %s FAIL  %-58s %s" % (tag, url.replace("http://", "")[:58], str(e)[:50]))


# ---------- B: 抓 610 板 ----------
def grab_withr_board():
    n = 0
    for page in range(1, 26):
        url = "http://www1.rocketbbs.com/610/bbs.cgi?id=withr&page=%d" % page
        try:
            st, b = get(url, 40, referer="http://www1.rocketbbs.com/610/withr.html")
            if st == 200 and len(b) > 800:
                open("%s/pages/p%02d.html" % (OUT, page), "wb").write(b)
                txt = b.decode("cp932", "replace")
                nos = re.findall(r"No\.(\d+)", txt)
                note("page %2d  %6d bytes  No.%s..%s" % (
                    page, len(b), nos[0] if nos else "-", nos[-1] if nos else "-"))
                n += 1
            else:
                note("page %2d  HTTP %s len=%d  停止" % (page, st, len(b)))
                break
        except Exception as e:
            note("page %2d  ERR %s" % (page, str(e)[:60]))
            break
    note("B done, pages=%d" % n)


# ---------- C: archive.org 上找 rocketbbs ----------
def probe_archive():
    q = ('https://archive.org/advancedsearch.php?q=%s&fl%%5B%%5D=identifier'
         '&fl%%5B%%5D=title&fl%%5B%%5D=item_size&rows=40&page=1&output=json'
         % urllib.parse.quote("rocketbbs"))
    try:
        st, b = get(q, 60)
        d = json.loads(b)
        docs = d.get("response", {}).get("docs", [])
        note("C  archive.org 'rocketbbs' -> %d 条" % len(docs))
        for x in docs:
            note("   %-46s %s" % (x.get("identifier"), str(x.get("title"))[:50]))
        json.dump(docs, open(OUT + "/ia_rocketbbs.json", "w"), ensure_ascii=False, indent=1)
    except Exception as e:
        note("C  FAIL %s" % str(e)[:120])

    # Wayback 的 651 全量 url 清单
    for u in ("www5.rocketbbs.com/651*", "www1.rocketbbs.com/610*"):
        api = ("http://web.archive.org/cdx/search/cdx?url=%s&matchType=prefix"
               "&fl=original,timestamp,statuscode&collapse=urlkey&limit=400&output=json"
               % urllib.parse.quote(u, safe=""))
        try:
            st, b = get(api, 90)
            rows = json.loads(b)
            note("C  wayback %s -> %d 个 url" % (u, max(0, len(rows) - 1)))
            json.dump(rows, open("%s/cdx_%s.json" % (
                OUT, u.split("/")[0]), "w"), ensure_ascii=False, indent=1)
            for r in rows[1:26]:
                note("   %s  %s" % (r[0][-70:], r[1]))
        except Exception as e:
            note("C  wayback %s FAIL %s" % (u, str(e)[:90]))


if __name__ == "__main__":
    probe_archive()
    grab_withr_board()
    probe_oneday()
    open(OUT + "/log.txt", "w", encoding="utf-8").write("\n".join(log))
