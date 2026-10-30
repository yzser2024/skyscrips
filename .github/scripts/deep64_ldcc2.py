# -*- coding: utf-8 -*-
"""deep-64: 只补 LOVE DISTANCE 与 CLOUD castle 的页面（聚焦版，快速）
目标目录：
  music.geocities.jp/withr17/ld/     LD 各章（2008-2013 有 11 页记录）
  music.geocities.jp/withr17/cc/     CC 各章（2011 快照）
  www.geocities.jp/amorxxx79/cc/     CC 原点
  www.geocities.jp/amorxxx79/ld/     LD 原点
"""
import os, json, time, gzip, random, urllib.request, urllib.error, urllib.parse

OUT = "out_deep64"
os.makedirs(OUT + "/files", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True); LOG.write(s + "\n"); LOG.flush()


def fetch(url, tries=6, timeout=70):
    b = b""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                if b[:2] == b"\x1f\x8b":
                    try: b = gzip.decompress(b)
                    except Exception: pass
                return r.status, b
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                w = 20 + i * 15
                note("    %d wait %ds" % (e.code, w)); time.sleep(w); continue
            return e.code, b
        except Exception as e:
            note("    ERR " + str(e)[:60]); time.sleep(8 + i * 6)
    return None, b


PREFIXES = [
    "music.geocities.jp/withr17/ld/",
    "music.geocities.jp/withr17/cc/",
    "www.geocities.jp/amorxxx79/cc/",
    "www.geocities.jp/amorxxx79/ld/",
]

rows = []
for pre in PREFIXES:
    q = ("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(pre, safe="")
         + "&matchType=prefix&output=json&fl=timestamp,original,statuscode,mimetype,length"
         + "&collapse=digest&limit=500")
    st, b = fetch(q)
    note("CDX %s -> %s %d B" % (pre, st, len(b)))
    if st != 200 or not b.strip():
        time.sleep(10); continue
    try:
        d = json.loads(b.decode("utf-8", "replace"))
    except Exception as e:
        note("  json err " + str(e)[:50]); continue
    for r in d[1:]:
        rows.append(dict(zip(("ts", "original", "status", "mime", "len"), (r + [""]*5)[:5])))
    time.sleep(10 + random.random() * 6)

json.dump(rows, open(OUT + "/cdx.json", "w"), ensure_ascii=False, indent=1)
note("CDX 总条目 %d" % len(rows))
for r in rows:
    note("  CDX %s %s %s" % (r["status"], r["ts"], r["original"]))

# 抓：HTML + CSS + MIDI，按时间序（早的先，保证拿到原始版）
rows.sort(key=lambda r: (r["original"], r["ts"]))
man, done = [], set()
for r in rows:
    if r["status"] not in ("200", "-"):
        continue
    u = r["original"]
    if u in done:
        continue
    done.add(u)
    name = u.rstrip("/").split("/")[-1] or "index.html"
    host = urllib.parse.urlparse(u).netloc.replace(".", "_")
    path = urllib.parse.urlparse(u).path.strip("/").replace("/", "__")
    fn = "%s__%s" % (r["ts"], path or name)
    st, b = fetch("http://web.archive.org/web/%sid_/%s" % (r["ts"], u))
    head = b[:4].hex() if b else ""
    note("%s %-14s %-40s %7d %s" % (st, r["ts"], name, len(b), head))
    if st == 200 and len(b) > 150:
        open(OUT + "/files/" + fn, "wb").write(b)
        man.append({"file": fn, "url": u, "ts": r["ts"], "size": len(b), "magic": head})
    time.sleep(8 + random.random() * 6)

json.dump(man, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("DONE files=%d" % len(man))
