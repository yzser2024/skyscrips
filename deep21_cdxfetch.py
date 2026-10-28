#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二十一轮：换 URL 形式取 megawarc 的 os.cdx.gz。

上一轮 https://archive.org/download/<item>/<file> 对 87-90 MB 的索引文件
返回 401（小文件 meta.sqlite 却正常），说明大文件走了别的重定向链。

这一轮把常见几种取法都试一遍，并打印每一步的状态码与 Location：
  1. /download/<item>/<file>
  2. /download/<item>/<file>?download=1
  3. /serve/<item>/<file>
  4. https://<server>/download/<dir>/<file>     （server/dir 取自 metadata）
  5. https://<server>/<dir>/<file>
  6. 先 HEAD 看 Content-Length，再带 Range 取前 1 MB 验证可读

任一形式成功即下载完整文件并 grep amorxxx79 / withr79 / withr17。
"""
import gzip
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep21"
UA = {"User-Agent": "Mozilla/5.0 (research)"}
KEY = re.compile(rb"amorxxx79|withr17|withr79|oneyunn", re.I)

ITEM = "archiveteam_geocitiesjp_20181111195312"
CAND = [
    "geocitiesjp_20181111195312.megawarc.warc.os.cdx.gz",
    "archiveteam_geocitiesjp_20181111195312.cdx.gz",
]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def log(*a):
    print(*a, flush=True)


def try_url(url, timeout=600, redirect=True):
    opener = urllib.request.build_opener() if redirect else \
        urllib.request.build_opener(NoRedirect)
    try:
        r = opener.open(urllib.request.Request(url, headers=UA), timeout=timeout)
        return r.status, r.read(), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, b"", e.headers.get("Location", "") if e.headers else ""
    except Exception as e:
        return -1, str(e).encode()[:200], ""


def main():
    os.makedirs(OUT, exist_ok=True)

    st, b, _ = try_url("https://archive.org/metadata/" + ITEM, 90)
    d = json.loads(b)
    server = d.get("server", "")
    d1 = d.get("d1", "")
    d2 = d.get("d2", "")
    dirp = d.get("dir", "")
    log("server=%s  d1=%s  d2=%s  dir=%s" % (server, d1, d2, dirp))

    for fn in CAND:
        log("\n===== %s =====" % fn)
        forms = [
            "https://archive.org/download/%s/%s" % (ITEM, fn),
            "https://archive.org/download/%s/%s?download=1" % (ITEM, fn),
            "https://archive.org/serve/%s/%s" % (ITEM, fn),
        ]
        if server and dirp:
            forms.append("https://%s/download/%s/%s" % (server, dirp.lstrip("/"), fn))
            forms.append("https://%s/%s/%s" % (server, dirp.lstrip("/"), fn))
        if d1 and dirp:
            forms.append("https://%s/download/%s/%s" % (d1, dirp.lstrip("/"), fn))
        for dnode in (d1, d2):
            if dnode:
                forms.append("https://%s/download/%s/%s" %
                             (dnode, dirp.lstrip("/"), fn))

        got = None
        for u in forms:
            st, b, real = try_url(u, 900)
            log("  %-96s -> %s  %d 字节" % (u[:96], st, len(b)))
            if st == 200 and len(b) > 1000000:
                got = b
                log("     ★ 成功，来自 %s" % u)
                break
            time.sleep(1)
        if not got:
            log("  全部失败")
            continue

        p = os.path.join(OUT, fn)
        open(p, "wb").write(got)
        log("  落盘 %s %.1f MB" % (p, len(got) / 1048576.0))
        try:
            raw = gzip.decompress(got)
        except Exception as e:
            log("  解压失败 %s" % e)
            continue
        log("  解压 %.1f MB" % (len(raw) / 1048576.0))
        lines = raw.splitlines()
        log("  行数 %d" % len(lines))
        if lines:
            log("  首行 %s" % lines[0].decode("utf-8", "replace")[:200])
        hit = [l for l in lines if KEY.search(l)]
        log("  命中 %d 行" % len(hit))
        for l in hit[:80]:
            log("    ", l.decode("utf-8", "replace")[:230])
        json.dump([x.decode("utf-8", "replace") for x in hit],
                  open(os.path.join(OUT, "hits.json"), "w"),
                  ensure_ascii=False, indent=1)
        if hit:
            break

    log("\n完成")


if __name__ == "__main__":
    main()
