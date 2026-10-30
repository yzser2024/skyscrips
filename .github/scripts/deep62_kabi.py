# -*- coding: utf-8 -*-
"""deep-62: 找《聖域に黴》的音频文件
1) CDX 列出 amorxxx79 / withr17 / oneyunn79 上所有 mid/mp3/lzh/zip
2) 逐个取 id_ 原始字节（含 kabi.mid 的所有快照）
"""
import os, json, time, gzip, random, urllib.request, urllib.error, urllib.parse

OUT = "out_deep62"
os.makedirs(OUT + "/files", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True); LOG.write(s + "\n"); LOG.flush()


def fetch(url, tries=8, timeout=70):
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
                w = 25 + i * 20
                note("    %d wait %ds" % (e.code, w)); time.sleep(w); continue
            return e.code, b
        except Exception as e:
            note("    ERR " + str(e)[:70]); time.sleep(10 + i * 8)
    return None, b


PREFIXES = [
    "www.geocities.jp/amorxxx79/",
    "www.geocities.jp/withr17/",
    "oneyunn.client.jp/",
]

AUDIO_EXT = (".mid", ".midi", ".mp3", ".wav", ".lzh", ".zip", ".swf", ".rmi")

# ---------- 1. CDX ----------
rows = []
for pre in PREFIXES:
    q = ("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(pre, safe="")
         + "&matchType=prefix&output=json&fl=timestamp,original,statuscode,mimetype,length"
         + "&collapse=digest&limit=4000")
    st, b = fetch(q)
    note("CDX %s -> %s %d bytes" % (pre, st, len(b)))
    if st != 200 or not b.strip():
        continue
    try:
        d = json.loads(b.decode("utf-8", "replace"))
    except Exception as e:
        note("  json err " + str(e)[:60]); continue
    for r in d[1:]:
        ts, orig, sc, mt, ln = (r + ["", "", "", "", ""])[:5]
        rows.append({"ts": ts, "original": orig, "status": sc, "mime": mt, "len": ln})
    time.sleep(12 + random.random() * 8)

json.dump(rows, open(OUT + "/cdx_all.json", "w"), ensure_ascii=False, indent=1)
note("CDX 总条目 %d" % len(rows))

# ---------- 2. 只挑音频 ----------
audio = [r for r in rows if r["original"].lower().split("?")[0].endswith(AUDIO_EXT)]
note("音频类条目 %d" % len(audio))

# kabi 相关优先
kabi = [r for r in audio if "kabi" in r["original"].lower()]
note("含 kabi 的 %d 条: %s" % (len(kabi), [ (r["ts"], r["original"]) for r in kabi ]))

order = kabi + [r for r in audio if r not in kabi]
man = []
for r in order:
    if r["status"] not in ("200", "-"):
        continue
    name = r["original"].rstrip("/").split("/")[-1] or "index"
    ts = r["ts"]
    fn = "%s__%s" % (ts, name)
    path = OUT + "/files/" + fn
    url = "http://web.archive.org/web/%sid_/%s" % (ts, r["original"])
    st, b = fetch(url)
    head = b[:4].hex() if b else ""
    note("%s %-8s %-50s %6d %s" % (st, ts, name, len(b), head))
    if st == 200 and len(b) > 100:
        open(path, "wb").write(b)
        man.append({"file": fn, "url": r["original"], "ts": ts, "size": len(b), "magic": head})
    time.sleep(9 + random.random() * 7)

json.dump(man, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("DONE files=%d" % len(man))
