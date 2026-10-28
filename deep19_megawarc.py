#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十九轮：从 Archive Team 的 megawarc 索引里把 amorxxx79 挖出来。

上一轮确认：43 个 item，每个都带
    geocitiesjp_<ts>.megawarc.warc.os.cdx.gz   约 90 MB，带 offset + 文件名
    archiveteam_geocitiesjp_<ts>.cdx.gz        约 87 MB，常规 cdx

os.cdx 每行形如：
    urlkey timestamp original statuscode mimetype digest length offset filename

有了 offset 和 filename，就能对该 warc 发一个 HTTP Range 请求，只下那几 KB，
解 gzip 拿到原始抓取记录——不用下 74 GB。

站点按 urlkey 排序，amorxxx79 以 a 开头，应该在第一个分片里。
先扫前 3 个分片，命中就打印 offset，并实际把记录取下来验证。
"""
import gzip
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep19"
UA = {"User-Agent": "Mozilla/5.0 (research)"}
KEY = re.compile(rb"amorxxx79|withr17|withr79|oneyunn", re.I)

ITEMS = [
    "archiveteam_geocitiesjp_20181111195312",
    "archiveteam_geocitiesjp_20181111195313",
    "archiveteam_geocitiesjp_20181111195314",
    "archiveteam_geocitiesjp_20181111195315",
]


def log(*a):
    print(*a, flush=True)


def fetch(url, timeout=900, retries=2, headers=None):
    h = dict(UA)
    if headers:
        h.update(headers)
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h),
                                        timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""
        except Exception as e:
            log("    重试 %d %s" % (i + 1, type(e).__name__))
            time.sleep(10)
    return -1, b""


def meta(ident):
    st, b = fetch("https://archive.org/metadata/" + ident, 120, 2)
    try:
        return json.loads(b)
    except Exception:
        return {}


def main():
    os.makedirs(OUT, exist_ok=True)
    found = []

    for ident in ITEMS:
        d = meta(ident)
        files = d.get("files", [])
        names = [f.get("name", "") for f in files]
        cdx = [n for n in names if n.endswith(".os.cdx.gz")]
        if not cdx:
            log("%s 无 os.cdx.gz，跳过" % ident)
            continue
        name = cdx[0]
        url = "https://archive.org/download/%s/%s" % (ident, urllib.parse.quote(name))
        log("\n== %s / %s" % (ident, name))
        st, b = fetch(url)
        log("   下载 %s  %d 字节" % (st, len(b)))
        if not b:
            continue
        try:
            raw = gzip.decompress(b)
        except Exception as e:
            log("   解压失败", e)
            continue
        log("   解压后 %.1f MB" % (len(raw) / 1048576.0))
        open(os.path.join(OUT, ident + ".os.cdx"), "wb").write(raw)

        lines = raw.splitlines()
        log("   行数 %d" % len(lines))
        if lines:
            log("   首行 %s" % lines[0].decode("utf-8", "replace")[:180])
            log("   末行 %s" % lines[-1].decode("utf-8", "replace")[:180])
        hit = [l for l in lines if KEY.search(l)]
        log("   命中 %d 行" % len(hit))
        for l in hit[:60]:
            s = l.decode("utf-8", "replace")
            log("     ", s[:220])
        if hit:
            found.append((ident, name, hit))
            break  # 找到了就不必再扫后面的分片

    json.dump([[i, n, [x.decode("utf-8", "replace") for x in h]]
               for i, n, h in found],
              open(os.path.join(OUT, "hits.json"), "w"),
              ensure_ascii=False, indent=1)
    log("\n命中分片 %d 个" % len(found))


if __name__ == "__main__":
    main()
