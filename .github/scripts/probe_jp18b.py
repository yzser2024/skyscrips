#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第十八轮 B：补齐自站全部试听页（修复编码 bug + Wayback 限流退避）

只抓 live（现存 200 可用），Wayback 仅在 live 失败时用，且带 429 退避。
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request

OUT = "out_jp18b"
os.makedirs(OUT, exist_ok=True)
RAW = os.path.join(OUT, "raw")
os.makedirs(RAW, exist_ok=True)
LOG = open(os.path.join(OUT, "log_jp18b.txt"), "w", encoding="utf-8")


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
BUDGET = 1100


def dec(b):
    for enc in ("utf-8", "cp932", "euc-jp"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", "replace"), "utf-8/replace"


def get(url, save=None, timeout=45):
    if time.time() - T0 > BUDGET:
        return "SKIP", b"", "utf-8"
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
        log("   ERR", type(e).__name__, str(e)[:100])
        return None, b"", "utf-8"
    if save:
        open(os.path.join(RAW, save), "wb").write(b)
    _, enc = dec(b)
    return st, b, enc


PAGES = [
    "locusoftristeza.html", "pp.html", "menumenu.html", "midimidi.html",
    "musicpiano.html", "main.html", "10top.html", "10link.html",
    "lt1.html", "lt2.html", "lt3.html", "lt4.html", "lt5.html", "lt6.html",
    "lt7.html", "lt8.html", "lt9.html", "lt10.html", "lt11.html",
    "p1.html", "p2.html", "p3.html", "p4.html", "p5.html", "p6.html",
    "p7.html", "p8.html", "p9.html", "p10.html", "p11.html",
    "cc2.html", "cc3.html", "cc4.html", "cc8.html", "ccc.html",
    "album1.html", "12345.html", "index.html",
]
AUDIO = re.compile(r'\.(mp3|mid|midi|wav|m4a|ogg|aac|au)(\?|#|$)', re.I)
TID = re.compile(r'/tracks/(\d+)|tracks%2F(\d+)', re.I)

log("A. 全部试听页 live")
RESULT = []
for fn in PAGES:
    url = "http://tristeza.web.fc2.com/" + fn
    sf = "live_" + fn.replace(".html", "") + ".html"
    st, b, enc = get(url, save=sf)
    s = b.decode(enc, "replace") if b else ""
    is404 = ("404 Error" in s[:3000]) or ("Page not found" in s[:3000])
    title = re.findall(r"<title>(.*?)</title>", s, re.S)
    auds = [l for l in re.findall(r'(?:href|src|value)\s*=\s*["\']([^"\']+)["\']', s, re.I) if AUDIO.search(l)]
    tids = [a or c for a, c in TID.findall(s)]
    log("%-22s %-4s %6d enc=%-10s %-14s audio=%d tid=%s" % (
        fn, st, len(b), enc, str(title[:1])[:14], len(auds), ",".join(dict.fromkeys(tids))[:40]))
    RESULT.append({"page": fn, "status": st, "bytes": len(b), "enc": enc,
                   "title": title, "is404": is404, "audio": auds,
                   "soundcloud_track_ids": list(dict.fromkeys(tids))})
    time.sleep(0.7)

log("")
log("B. 提取全部页面正文（保存为 txt）")
TEXTS = {}
for fn in PAGES:
    sf = os.path.join(RAW, "live_" + fn.replace(".html", "") + ".html")
    if not os.path.exists(sf):
        continue
    b = open(sf, "rb").read()
    _, enc = dec(b)
    s = b.decode(enc, "replace")
    if "404 Error" in s[:3000]:
        continue
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</h[1-6]>|</li>|</tr>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    import html as H
    s = H.unescape(s)
    lines = [l.strip() for l in s.split("\n") if l.strip() and l.strip() != "&nbsp;"]
    txt = "\n".join(lines)
    TEXTS[fn] = txt
    open(os.path.join(RAW, "text_" + fn.replace(".html", "") + ".txt"), "w",
         encoding="utf-8").write(txt)
    log("  %-22s %5d chars" % (fn, len(txt)))

log("")
log("C. Wayback 补档（仅对 live 404 或 0 字节的页，带退避）")
WMAP = {
 "lt1.html":"20250920094011","lt2.html":"20250920094022","lt3.html":"20250920180721",
 "lt4.html":"20250920134922","lt5.html":"20250920142713","lt6.html":"20250920110044",
 "lt7.html":"20250920145856","lt8.html":"20250920105450","lt9.html":"20250920141627",
 "lt10.html":"20250920170112","lt11.html":"20250920104020",
 "p1.html":"20260405034353","p2.html":"20260405034353","p3.html":"20260405034353",
 "p4.html":"20260405034353","p5.html":"20260405034353","p6.html":"20260405034353",
 "p7.html":"20260405034353","p8.html":"20260405034353","p9.html":"20260405034353",
 "p10.html":"20260405034353","p11.html":"20260405034353",
}
need = [r["page"] for r in RESULT if r["status"] != 200 or r["is404"] or r["bytes"] < 500]
log("need wayback:", need)
for fn in need:
    ts = WMAP.get(fn)
    if not ts:
        continue
    live = "http://tristeza.web.fc2.com/" + fn
    wb = "https://web.archive.org/web/%sid_/%s" % (ts, live)
    for attempt in range(3):
        st, b, enc = get(wb, save="wb_" + fn.replace(".html", "") + ".html", timeout=60)
        if st == 200 and len(b) > 500:
            s = b.decode(enc, "replace")
            tids = [a or c for a, c in TID.findall(s)]
            title = re.findall(r"<title>(.*?)</title>", s, re.S)
            log("  WB %-20s 200 %6d title=%s tid=%s" % (
                fn, len(b), str(title[:1])[:30], ",".join(dict.fromkeys(tids))[:40]))
            break
        log("  WB %-20s %s (attempt %d)" % (fn, st, attempt + 1))
        time.sleep(8 + attempt * 8)

json.dump(RESULT, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
log("done in %ds" % int(time.time() - T0))
