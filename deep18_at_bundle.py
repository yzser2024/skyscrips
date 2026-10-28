#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十八轮：进 Archive Team「Geocities Japan 2018」大包内部找索引。

情况：archive.org 上有 40 多个 item，命名 archiveteam_geocitiesjp_20181111xxxxxx，
单个 75-151 GB，合计约 4 TB。这是 2018-11-11 关站前的整站抓取。
单站命名的 WARC 只有 46 个（tuguhana / workplace / Playtown-Denei…），不含 amorxxx79。

要点：Archive Team 上传时通常附带 CDX 索引（*.cdx.gz 或 *.cdx），
体积远小于 WARC。只要拿到索引，grep 一次就知道 amorxxx79 在不在、在哪个 warc、
offset 多少——然后可以只下载那一段字节。

本轮：
  1. 列全部 archiveteam_geocitiesjp_* item。
  2. 对其中若干个取 metadata，看文件构成，找 cdx / index / sqlite。
  3. 有 cdx 就下载最小的那个，扫 amorxxx79 / withr17 / oneyunn。
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

OUT = "out_deep18"
UA = {"User-Agent": "Mozilla/5.0 (research)"}


def log(*a):
    print(*a, flush=True)


def get(url, timeout=120, retries=3):
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""
        except Exception:
            time.sleep(8)
    return -1, b""


def adv(q, rows=200):
    u = ("https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(q) +
         "&fl[]=identifier&fl[]=title&fl[]=item_size&fl[]=publicdate"
         "&rows=" + str(rows) + "&page=1&output=json")
    st, b = get(u)
    try:
        d = json.loads(b)
        return d["response"]["numFound"], d["response"]["docs"]
    except Exception:
        return -1, []


def main():
    os.makedirs(OUT, exist_ok=True)

    log("===== 1. 全部 archiveteam_geocitiesjp_* =====")
    num, docs = adv("identifier:archiveteam_geocitiesjp*", 300)
    log("  numFound=%s" % num)
    ids = sorted(d["identifier"] for d in docs)
    for i in ids[:60]:
        log("    ", i)
    json.dump(docs, open(os.path.join(OUT, "items.json"), "w"), ensure_ascii=False)

    if not ids:
        log("  没有找到，退回按 collection 查")
        num, docs = adv("collection:archiveteam AND geocities japan", 300)
        ids = sorted(d["identifier"] for d in docs)
        log("  numFound=%s -> %d" % (num, len(ids)))
        for i in ids[:60]:
            log("    ", i)

    log("\n===== 2. 挑几个看文件构成 =====")
    interesting = []
    for ident in ids[:6]:
        st, b = get("https://archive.org/metadata/" + ident)
        try:
            d = json.loads(b)
        except Exception:
            log("  %s metadata %s 失败" % (ident, st))
            continue
        files = d.get("files", [])
        total = sum(int(f.get("size", 0) or 0) for f in files) / 1073741824.0
        log("  %-46s 文件 %3d 个  %.1f GB" % (ident, len(files), total))
        idx = []
        for f in files:
            n = f.get("name", "")
            sz = int(f.get("size", 0) or 0)
            if re.search(r"\.cdx|index|\.sqlite|\.db$|urls|\.txt$", n, re.I):
                idx.append((n, sz))
        if idx:
            log("      发现索引类文件：")
            for n, sz in sorted(idx, key=lambda x: x[1])[:20]:
                log("        %-62s %10.2f MB" % (n[:62], sz / 1048576))
            interesting.append((ident, sorted(idx, key=lambda x: x[1])[0]))
        else:
            log("      无索引文件；前 8 个文件：")
            for f in files[:8]:
                log("        %-58s %8.1f MB  %s" %
                    (f.get("name", "")[:58],
                     int(f.get("size", 0) or 0) / 1048576, f.get("format", "")))
        json.dump(d, open(os.path.join(OUT, "meta_%s.json" % ident), "w"),
                  ensure_ascii=False)
        time.sleep(2)

    log("\n===== 3. 下载最小索引并扫描 =====")
    KEY = re.compile(rb"amorxxx79|withr17|withr79|oneyunn", re.I)
    for ident, (name, sz) in interesting:
        if sz > 800 * 1048576:
            log("  %s 的 %s 有 %.1f MB，跳过（太大）" %
                (ident, name, sz / 1048576))
            continue
        url = "https://archive.org/download/%s/%s" % (ident, urllib.parse.quote(name))
        log("  下载 %s / %s (%.1f MB)" % (ident, name, sz / 1048576))
        st, b = get(url, timeout=600, retries=2)
        log("    -> %s  %d 字节" % (st, len(b)))
        if not b:
            continue
        if name.endswith(".gz"):
            try:
                import gzip
                b = gzip.decompress(b)
            except Exception as e:
                log("    解压失败", e)
                continue
        open(os.path.join(OUT, re.sub(r"\W+", "_", ident) + ".cdx"), "wb").write(b)
        lines = b.splitlines()
        log("    行数 %d" % len(lines))
        hit = [l for l in lines if KEY.search(l)]
        log("    命中 %d 行" % len(hit))
        for l in hit[:40]:
            log("      ", l.decode("utf-8", "replace")[:160])

    log("\n完成")


if __name__ == "__main__":
    main()
