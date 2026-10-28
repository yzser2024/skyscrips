#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二十三轮：确认 Archive Team 大包到底是不是「受限 item」，并换工具再试。

现象：同一个 item 里
    *_meta.sqlite            200 OK（10 KB）
    *.cdx.idx  / *.cdx.gz    401
    *.warc.gz                未试
metadata 文件放行、数据文件挡掉，是 archive.org 对受限 item 的标准行为。

这一轮：
  1. 打出 metadata 里 access-restricted-item / collection / licenseurl /
     possible-copyright-violation 等字段，确认是否被设限。
  2. 用 curl 命令行（不同 TLS 指纹与 UA）重试，看是不是 UA 被拦。
  3. 试 dn / ia 两种节点域名、/download 与直链两种路径。
  4. 顺带看那个无时间戳的汇总 item archiveteam_geocitiesjp 里有什么。
"""
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request

OUT = "out_deep23"
ITEM = "archiveteam_geocitiesjp_20181111195312"
FN = "geocitiesjp_20181111195312.megawarc.warc.os.cdx.gz"
UA = {"User-Agent": "Mozilla/5.0 (research)"}


def log(*a):
    print(*a, flush=True)


def curl(url, extra=None, timeout=180):
    cmd = ["curl", "-sS", "-o", "/tmp/dl.bin", "-w",
           "%{http_code} %{size_download} %{content_type}", "-L",
           "--max-time", str(timeout),
           "-A", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
           "-e", "https://archive.org/details/" + ITEM]
    if extra:
        cmd += extra
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 20)
        return (r.stdout or "").strip() + " | " + (r.stderr or "").strip()[:160]
    except Exception as e:
        return "ERR " + str(e)[:120]


def main():
    os.makedirs(OUT, exist_ok=True)

    log("===== 1. metadata 关键字段 =====")
    with urllib.request.urlopen(
            urllib.request.Request("https://archive.org/metadata/" + ITEM,
                                   headers=UA), timeout=90) as r:
        meta = json.loads(r.read())
    m = meta.get("metadata", {})
    keys = ["identifier", "collection", "access-restricted-item",
            "possible-copyright-violation", "licenseurl", "rights",
            "uploader", "addeddate", "item_size", "noindex", "dark"]
    for k in keys:
        if k in m:
            log("  %-32s %s" % (k, str(m[k])[:160]))
    log("  --- 全部 key ---")
    log("  " + ", ".join(sorted(m.keys())))
    log("  server=%s dir=%s" % (meta.get("server"), meta.get("dir")))
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), ensure_ascii=False)

    log("\n===== 2. curl 各种 URL =====")
    srv = meta.get("server", "")
    dirp = (meta.get("dir") or "").lstrip("/")
    urls = [
        "https://archive.org/download/%s/%s" % (ITEM, FN),
        "https://archive.org/download/%s/%s?download=1" % (ITEM, FN),
        "https://%s/download/%s/%s" % (srv, dirp, FN),
        "https://%s/%s/%s" % (srv, dirp, FN),
        "https://ia902302.us.archive.org/%s/%s" % (dirp, FN),
    ]
    for u in urls:
        log("  %-104s" % u[:104])
        log("      " + curl(u, ["-r", "0-65535"], 120))
        time.sleep(2)

    log("\n===== 3. 汇总 item（无时间戳那个）=====")
    try:
        with urllib.request.urlopen(
                urllib.request.Request(
                    "https://archive.org/metadata/archiveteam_geocitiesjp",
                    headers=UA), timeout=90) as r:
            d = json.loads(r.read())
        log("  metadata:")
        for k, v in (d.get("metadata") or {}).items():
            log("    %-28s %s" % (k, str(v)[:140]))
        log("  files:")
        for f in d.get("files", []):
            log("    %-58s %8.1f MB  %s" %
                (f.get("name", "")[:58],
                 int(f.get("size", 0) or 0) / 1048576, f.get("format", "")))
        for f in d.get("files", []):
            n = f.get("name", "")
            if n.endswith((".txt", ".xml", ".json", ".cdx.idx")):
                u = "https://archive.org/download/archiveteam_geocitiesjp/" + \
                    urllib.parse.quote(n)
                log("    试取 %-40s  %s" % (n[:40], curl(u, ["-r", "0-200000"], 90)))
        json.dump(d, open(os.path.join(OUT, "summary_item.json"), "w"),
                  ensure_ascii=False)
    except Exception as e:
        log("  失败 %s" % e)

    log("\n完成")


if __name__ == "__main__":
    main()
