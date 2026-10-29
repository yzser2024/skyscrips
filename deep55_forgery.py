# -*- coding: utf-8 -*-
"""deep-52: withr17 曲目独立页（歌词页）剩余 19 张，慢速抓取避 429"""
import os, re, json, time, gzip, random, urllib.request, urllib.error

OUT = "out_deep55"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BASE = "http://music.geocities.jp/withr17/"


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def fetch(url, tries=5, timeout=60):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                if b[:2] == b"\x1f\x8b":
                    try:
                        b = gzip.decompress(b)
                    except Exception:
                        pass
                return r.status, b
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                w = 90 + i * 40 + random.random() * 20
                note("    %d 等待 %ds" % (e.code, int(w)))
                time.sleep(w)
                continue
            return e.code, b""
        except Exception as e:
            note("    ERR " + str(e)[:60])
            time.sleep(10 + i * 10)
    return None, b""


TARGETS = [
    ("forgery", "20181105032110"),
]

man = []
for name, ts in TARGETS:
    o = BASE + name + ".html"
    stx, b = fetch("http://web.archive.org/web/" + ts + "id_/" + o)
    if stx == 200 and len(b) > 200:
        fn = OUT + "/pages/" + name + "__" + ts + ".html"
        open(fn, "wb").write(b)
        note("OK %-16s %s %d" % (name, ts, len(b)))
        man.append({"name": name, "ts": ts, "size": len(b)})
    else:
        note("-- %-16s %s %s" % (name, ts, stx))
    time.sleep(35 + random.random() * 10)

json.dump(man, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done %d / %d" % (len(man), len(TARGETS)))
