#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十八轮：TRISTEZA 自站全部试听页 + 音频链接 + 旧域 CDX

A. 39 个真实页面：现存 HTTP 与 Wayback 快照各一份，解码保存
B. 从页面提取所有音频链接（mp3/mid/midi/wav/m4a/ogg/aac）与外链
C. Wayback CDX：geocities.jp/wlstz3635 域、fc2 文件域、不带 collapse 的全量
D. 探测 note-sound 音频接口
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_jp18"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp18.txt"), "w", encoding="utf-8")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
T0 = time.time()
BUDGET = 1400
RESULT = []


def dec(b):
    for enc in ("utf-8", "cp932", "euc-jp"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", "replace"), "utf-8/replace"


def get(url, save=None, timeout=50):
    if time.time() - T0 > BUDGET:
        return "SKIP", b"", ""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            b, st = r.read(), r.status
    except urllib.error.HTTPError as e:
        try:
            b = e.read()
        except Exception:
            b = b""
        st = e.code
    except Exception as e:
        return None, ("%s: %s" % (type(e).__name__, e)).encode(), ""
    if save:
        open(os.path.join(RAW, save), "wb").write(b)
    _, enc = dec(b)
    return st, b, enc


# Wayback 映射（来自 jp17 cdx_all）
WMAP = {
 "12345.html":"20160701081556","album1.html":"20160701080014",
 "baramusic.html":"20120316070125","cc2.html":"20260409032125",
 "cc3.html":"20260409032123","cc4.html":"20260409032123","cc8.html":"20260409032125",
 "ccc.html":"20250928035351","locusoftristeza.html":"20250920094024",
 "lt1.html":"20250920094011","lt2.html":"20250920094022","lt3.html":"20250920180721",
 "lt4.html":"20250920134922","lt5.html":"20250920142713","lt6.html":"20250920110044",
 "lt7.html":"20250920145856","lt8.html":"20250920105450","lt9.html":"20250920141627",
 "lt10.html":"20250920170112","lt11.html":"20250920104020",
 "menumenu.html":"20221215085414","midimidi.html":"20221215085414",
 "musicpiano.html":"20120316070125",
 "p1.html":"20260405034353","p2.html":"20260405034353","p3.html":"20260405034353",
 "p4.html":"20260405034353","p5.html":"20260405034353","p6.html":"20260405034353",
 "p7.html":"20260405034353","p8.html":"20260405034353","p9.html":"20260405034353",
 "p10.html":"20260405034353","p11.html":"20260405034353",
 "pp.html":"20250928035351",
}
AUDIO_EXT = re.compile(r'\.(mp3|mid|midi|wav|m4a|ogg|aac|wma|au|mp2)(\?|#|$)', re.I)

log("=" * 72)
log("A. 自站试听页：现存 + Wayback 快照")
log("=" * 72)
all_links = {}
for fn, ts in WMAP.items():
    live = "http://tristeza.web.fc2.com/" + fn
    wb = "https://web.archive.org/web/%sid_/%s" % (ts, live)
    for tag, url in (("live", live), ("wb", wb)):
        sf = "%s_%s.html" % (tag, fn.replace(".html", ""))
        st, b, enc = get(url, save=sf, timeout=45)
        txt = b.decode(enc, "replace") if isinstance(b, bytes) else str(b)
        is404 = "404 Error" in txt[:3000] or "Page not found" in txt[:3000]
        links = re.findall(r'(?:href|src|data-src|value)\s*=\s*["\']([^"\']+)["\']', txt, re.I)
        auds = [l for l in links if AUDIO_EXT.search(l)]
        if auds:
            all_links.setdefault(fn, []).extend(auds)
        log("%-4s %-18s %-4s %6d  enc=%-12s audio=%d%s" % (
            tag, fn, st, len(b), enc, len(auds), " [404]" if is404 else ""))
        RESULT.append({"page": fn, "tag": tag, "url": url, "file": sf,
                       "status": st, "bytes": len(b), "enc": enc,
                       "audio_links": auds, "is404": is404})
        time.sleep(0.5)

log("")
log("音频链接总计：")
for fn, ls in all_links.items():
    for l in dict.fromkeys(ls):
        log("   %-16s %s" % (fn, l))

log("")
log("=" * 72)
log("B. Wayback CDX 补充查询")
log("=" * 72)
CDX = "https://web.archive.org/cdx/search/cdx"
qs = [
    ("cdx_geo.json", {"url": "www.geocities.jp/wlstz3635", "matchType": "prefix",
                      "output": "json", "fl": "timestamp,original,statuscode,mimetype,length",
                      "collapse": "urlkey", "limit": "10000"}),
    ("cdx_geo_audio.json", {"url": "www.geocities.jp/wlstz3635", "matchType": "prefix",
                            "output": "json", "fl": "timestamp,original,statuscode,mimetype,length",
                            "collapse": "urlkey", "filter": "original:.*\\.(mp3|mid|midi|wav|m4a)$",
                            "limit": "10000"}),
    ("cdx_fc2_all.json", {"url": "tristeza.web.fc2.com", "matchType": "domain",
                          "output": "json", "fl": "timestamp,original,statuscode,mimetype,length,digest",
                          "limit": "20000"}),
    ("cdx_blogimg.json", {"url": "blog-imgs-*.fc2.com/tristeza/*", "output": "json",
                          "fl": "timestamp,original,statuscode,mimetype,length",
                          "collapse": "urlkey", "limit": "5000"}),
]
for fn, p in qs:
    u = CDX + "?" + urllib.parse.urlencode(p)
    st, b, enc = get(u, save=fn, timeout=110)
    txt = b.decode("utf-8", "replace") if isinstance(b, bytes) else str(b)
    rows = 0
    try:
        rows = len(json.loads(txt))
    except Exception:
        pass
    log("%-20s %-4s rows=%s bytes=%d" % (fn, st, rows, len(b)))
    time.sleep(2)

log("")
log("=" * 72)
log("C. note-sound 音频接口探测")
log("=" * 72)
sounds = [
    ("rose", "5127aedb196e85a28149fad8d9976345"),
    ("scarlet", "9e228495b78a3d47e1f37a566acc7df5"),
]
for name, sid in sounds:
    for tpl in ["https://note.com/api/v2/sounds/%s",
                "https://note.com/api/v3/sounds/%s"]:
        u = tpl % sid
        st, b, enc = get(u, save="sound_%s_%s.json" % (name, tpl.split("/")[4]))
        txt = b.decode("utf-8", "replace") if isinstance(b, bytes) else str(b)
        log("%-12s %-6s %-4s %d bytes  %s" % (name, tpl.split("/")[4], st, len(b), txt[:120]))
        time.sleep(0.6)

json.dump(RESULT, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump(all_links, open(os.path.join(OUT, "audio_links.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("done in %ds" % int(time.time() - T0))
