#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二十二轮：带会话 cookie 取索引，并先摸 .cdx.idx 的格式。

上一轮 401/403 全挡。小文件（_meta.sqlite，10 KB）能下，大文件不行，
典型是 archive.org 对未登录会话的下载限制。这一轮：

  1. 用 CookieJar 建会话：先访问 details 页拿 cookie，再带 Referer 去 download。
  2. 同时用 Range 只取前 1 MB —— 若能通，就说明限制只作用于整文件传输。
  3. 无论成败，先把 80 KB 的 *.cdx.idx 拿下来看格式。它是 megawarc 的
     SURT 前缀索引，若含 urlkey -> 行号/偏移，就能跳过下载整个 cdx。
  4. 把 _meta.sqlite 也拆开看看（9 KB 的 SQLite，可能记录分片范围）。
"""
import http.cookiejar
import json
import os
import re
import sqlite3
import time
import urllib.parse
import urllib.request

OUT = "out_deep22"
ITEM = "archiveteam_geocitiesjp_20181111195312"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Accept": "*/*",
      "Accept-Language": "en-US,en;q=0.9"}

CJ = http.cookiejar.CookieJar()
OP = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CJ))


def log(*a):
    print(*a, flush=True)


def req(url, headers=None, timeout=300, rng=None):
    h = dict(UA)
    h["Referer"] = "https://archive.org/details/" + ITEM
    if rng:
        h["Range"] = rng
    if headers:
        h.update(headers)
    try:
        r = OP.open(urllib.request.Request(url, headers=h), timeout=timeout)
        return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, b"", dict(e.headers or {})
    except Exception as e:
        return -1, str(e).encode()[:200], {}


def main():
    os.makedirs(OUT, exist_ok=True)

    log("===== 0. 建立会话 =====")
    st, b, h = req("https://archive.org/details/" + ITEM, timeout=90)
    log("  details %s %d 字节  cookie=%s" %
        (st, len(b), [c.name for c in CJ]))
    time.sleep(1)

    st, b, _ = req("https://archive.org/metadata/" + ITEM, timeout=90)
    meta = json.loads(b)
    files = meta.get("files", [])
    log("  文件数 %d  server=%s dir=%s" %
        (len(files), meta.get("server"), meta.get("dir")))
    for f in files:
        log("    %-62s %10.2f MB  %s" %
            (f.get("name", "")[:62],
             int(f.get("size", 0) or 0) / 1048576, f.get("format", "")))

    names = [f.get("name", "") for f in files]
    idx = [n for n in names if n.endswith(".cdx.idx")]
    sqlite = [n for n in names if n.endswith("_meta.sqlite")]
    big = [n for n in names if n.endswith(".os.cdx.gz")] or \
          [n for n in names if n.endswith(".cdx.gz")]

    log("\n===== 1. 取 .cdx.idx =====")
    for n in idx:
        u = "https://archive.org/download/%s/%s" % (ITEM, urllib.parse.quote(n))
        st, b, h = req(u, timeout=180)
        log("  %-58s -> %s  %d 字节" % (n[:58], st, len(b)))
        if b:
            open(os.path.join(OUT, n), "wb").write(b)
            head = b[:400]
            log("    前 400 字节 repr: %r" % head)
            # 尝试当文本读
            try:
                txt = b.decode("utf-8")
                lines = txt.splitlines()
                log("    文本行数 %d" % len(lines))
                for l in lines[:15]:
                    log("      ", l[:160])
            except Exception as e:
                log("    非文本：%s" % e)

    log("\n===== 2. 大文件：完整 / Range 各试一次 =====")
    for n in big[:1]:
        u = "https://archive.org/download/%s/%s" % (ITEM, urllib.parse.quote(n))
        st, b, h = req(u, rng="bytes=0-1048575", timeout=180)
        log("  Range 0-1MB  %-40s -> %s %d 字节  CL=%s" %
            (n[-40:], st, len(b), h.get("Content-Range")))
        time.sleep(2)

    log("\n===== 3. 拆 _meta.sqlite =====")
    for n in sqlite:
        u = "https://archive.org/download/%s/%s" % (ITEM, urllib.parse.quote(n))
        st, b, _ = req(u, timeout=180)
        log("  %-58s -> %s %d 字节" % (n[:58], st, len(b)))
        if not b:
            continue
        p = os.path.join(OUT, n)
        open(p, "wb").write(b)
        try:
            con = sqlite3.connect(p)
            cur = con.cursor()
            tabs = [r[0] for r in cur.execute(
                "select name from sqlite_master where type='table'")]
            log("    表：%s" % tabs)
            for t in tabs:
                cols = [d[1] for d in cur.execute("pragma table_info(%s)" % t)]
                log("      %s 列=%s" % (t, cols))
                for row in cur.execute("select * from %s limit 8" % t):
                    log("        ", str(row)[:200])
            con.close()
        except Exception as e:
            log("    sqlite 打开失败：%s" % e)

    log("\n完成")


if __name__ == "__main__":
    main()
