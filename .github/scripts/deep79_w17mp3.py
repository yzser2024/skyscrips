#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抢救 withr17 全站 18 首 mp3（CDX 全部 200）。"""
import json
import os
import time
import urllib.error
import urllib.request

OUT = "out_deep79"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research; withr-archive)"}

ITEMS = [
    ("body.mp3", "20130309050546", "http://music.geocities.jp/withr17/body.mp3"),
    ("cc_amedama.mp3", "20111103122649", "http://music.geocities.jp/withr17/cc/amedama.mp3"),
    ("cc_hikari.mp3", "20111103122659", "http://music.geocities.jp/withr17/cc/hikari.mp3"),
    ("cc_nameless.mp3", "20111103122639", "http://music.geocities.jp/withr17/cc/nameless.mp3"),
    ("finaltale.mp3", "20111019015337", "http://music.geocities.jp/withr17/finaltale.mp3"),
    ("fuchi.mp3", "20130309050631", "http://music.geocities.jp/withr17/fuchi.mp3"),
    ("jane.mp3", "20111019015612", "http://music.geocities.jp/withr17/jane.mp3"),
    ("kage.mp3", "20120113082814", "http://music.geocities.jp/withr17/kage.mp3"),
    ("kisui.mp3", "20130303141500", "http://music.geocities.jp/withr17/kisui.mp3"),
    ("laissez_passer.mp3", "20130303141602", "http://music.geocities.jp/withr17/laissez_passer.mp3"),
    ("ld_crescent.mp3", "20111103122536", "http://music.geocities.jp/withr17/ld/crescent.mp3"),
    ("ld_epilogue.mp3", "20111102162545", "http://music.geocities.jp/withr17/ld/epilogue.mp3"),
    ("ld_even_if.mp3", "20111103122454", "http://music.geocities.jp/withr17/ld/even_if.mp3"),
    ("ld_kiseki.mp3", "20111103122556", "http://music.geocities.jp/withr17/ld/kiseki.mp3"),
    ("ld_require.mp3", "20111102162432", "http://music.geocities.jp/withr17/ld/require.mp3"),
    ("ld_saigonoyoru.mp3", "20111103122614", "http://music.geocities.jp/withr17/ld/saigonoyoru.mp3"),
    ("songbird.mp3", "20111019015418", "http://music.geocities.jp/withr17/songbird.mp3"),
    ("wsg.mp3", "20111103122732", "http://music.geocities.jp/withr17/wsg.mp3"),
]


def get(url, tries=4, timeout=240):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            print("HTTP", e.code, url, flush=True)
            if e.code in (429, 503, 502, 504):
                time.sleep(20 + i * 20)
                continue
            if e.code in (404, 403):
                return None
        except Exception as e:
            print("ERR", type(e).__name__, url, flush=True)
            time.sleep(10)
    return None


meta = {}
for name, ts, orig in ITEMS:
    url = "https://web.archive.org/web/%sid_/%s" % (ts, orig)
    b = get(url)
    ok = bool(b) and b[:3] == b"ID3" or (bool(b) and b[:1] == b"\xff")
    print(name, len(b) if b else None, b[:3] if b else None, "OK" if ok else "BAD", flush=True)
    if b and len(b) > 500000:
        open(os.path.join(OUT, name), "wb").write(b)
        meta[name] = {"ts": ts, "url": orig, "bytes": len(b)}
    time.sleep(2.5)

json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), ensure_ascii=False, indent=1)
print("saved", len(meta), "total", sum(v["bytes"] for v in meta.values()), flush=True)
print("done")
