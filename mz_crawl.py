#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mz_crawl.py —— 直连抓活站 mahoutukai.mizubasyou.com（诗歌站），拿原始 HTML
用途：确认页面里到底引用了什么 BGM（是否有 withR / ONE's 的 mid、mp3）
"""
import os
import re
import json
import time
import urllib.parse
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

ROOT = "https://mahoutukai.mizubasyou.com/"
HOST = "mahoutukai.mizubasyou.com"
OUT = "site/mahoutukai"

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"})

MEDIA = (".mid", ".midi", ".mp3", ".wav", ".m4a", ".ogg", ".swf", ".wma", ".zip", ".lzh")
PAGES = (".html", ".htm", ".php", ".cgi", "")


def dec(b):
    for e in ("utf-8", "cp932", "shift_jis", "euc_jp"):
        try:
            return b.decode(e), e
        except Exception:
            continue
    return b.decode("utf-8", "replace"), "?"


def to_txt(t):
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|tr|li|h[1-6]|table|blockquote)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"')):
        t = t.replace(a, b)
    lines = [re.sub(r"[ \t\u3000]+", " ", l).strip() for l in t.split("\n")]
    return "\n".join([l for l in lines if l])


def path_of(url):
    p = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(p.path) or "/"
    if path.endswith("/"):
        path += "index.html"
    parts = [x for x in path.lstrip("/").split("/") if x not in ("", ".", "..")]
    parts = [re.sub(r'[\\:*?"<>|\x00-\x1f]', "_", x) for x in parts] or ["index.html"]
    if p.query:
        parts[-1] += "__q_" + re.sub(r"[^A-Za-z0-9]+", "_", p.query)[:50]
    return os.path.join(*parts)


def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            r = S.get(url, timeout=40, allow_redirects=True)
            if r.status_code == 200:
                return r
            last = "HTTP %d" % r.status_code
            if r.status_code in (403, 404):
                return r
        except Exception as e:
            last = repr(e)[:120]
        time.sleep(1 + i * 2)
    print("  FAIL %s %s" % (url, last), flush=True)
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    seen = set()
    queue = deque([ROOT])
    pages = {}
    media = set()
    log = []

    while queue and len(seen) < 400:
        batch = []
        while queue and len(batch) < 8:
            u = queue.popleft()
            u = u.split("#")[0]
            if u in seen:
                continue
            seen.add(u)
            batch.append(u)

        with ThreadPoolExecutor(max_workers=6) as ex:
            futs = {ex.submit(get, u): u for u in batch}
            for fu in as_completed(futs):
                u = futs[fu]
                r = fu.result()
                if r is None:
                    log.append({"url": u, "status": "fail"})
                    continue
                rel = path_of(r.url)
                dst = os.path.join(OUT, rel)
                os.makedirs(os.path.dirname(dst) or OUT, exist_ok=True)
                ctype = r.headers.get("content-type", "")
                open(dst, "wb").write(r.content)
                log.append({"url": u, "final": r.url, "status": r.status_code,
                            "type": ctype, "size": len(r.content), "file": rel})

                if "html" not in ctype and not rel.lower().endswith((".html", ".htm", "")):
                    continue
                t, enc = dec(r.content)
                open(dst + ".txt", "w", encoding="utf-8").write(to_txt(t))
                pages[u] = {"enc": enc, "file": rel}

                # 收集链接（兼容不带引号的写法 href=./xxx.html）
                for m in re.finditer(r'(?:href|src|data-src|background)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', t, re.I):
                    raw = (m.group(1) or m.group(2) or m.group(3) or "").strip()
                    if raw.startswith(("mailto:", "javascript:", "#", "tel:")):
                        continue
                    full = urllib.parse.urljoin(r.url, raw)
                    low = full.lower().split("?")[0]
                    host2 = urllib.parse.urlsplit(full).netloc
                    if host2 != HOST:
                        # 外链媒体（可能指向 oneyunn79 / geocities 的 mid）也记下来
                        if low.endswith(MEDIA):
                            media.add(full)
                            log.append({"url": u, "external_media": full})
                        continue
                    if low.endswith(MEDIA):
                        media.add(full)
                    elif low.endswith((".html", ".htm", ".php", ".cgi", "/")) or "." not in low.rsplit("/", 1)[-1]:
                        if full not in seen:
                            queue.append(full)

                # 记录 embed / bgsound / audio 详情
                for m in re.finditer(r"<(embed|bgsound|audio|object|iframe)\b[^>]*>", t, re.I):
                    log.append({"url": u, "tag": m.group(0)[:300]})

    # 下载媒体
    print("媒体文件 %d 个" % len(media), flush=True)
    for u in sorted(media):
        r = get(u)
        if r is None or r.status_code != 200:
            log.append({"url": u, "status": "media-fail"})
            continue
        dst = os.path.join(OUT, path_of(u))
        host3 = urllib.parse.urlsplit(u).netloc
        if host3 and host3 != HOST:
            dst = os.path.join(OUT, "_ext", host3, path_of(u))
        os.makedirs(os.path.dirname(dst) or OUT, exist_ok=True)
        open(dst, "wb").write(r.content)
        log.append({"url": u, "status": 200, "size": len(r.content),
                    "file": os.path.relpath(dst, OUT), "type": "media"})

    json.dump(log, open(os.path.join(OUT, "_log.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("页面 %d，媒体 %d" % (len(pages), len(media)))


if __name__ == "__main__":
    main()
