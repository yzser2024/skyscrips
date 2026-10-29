# -*- coding: utf-8 -*-
"""deep-57: 只抓一份——改版后第一份 about.html（2014-12-28），确认 Name 字段"""
import os, re, json, time, gzip, random, urllib.request, urllib.error

OUT = "out_deep57"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True); LOG.write(s + "\n"); LOG.flush()


def fetch(url, tries=10, timeout=60):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                if b[:2] == b"\x1f\x8b":
                    try: b = gzip.decompress(b)
                    except Exception: pass
                return r.status, b
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                w = 30 + i * 25
                note("    %d wait %ds" % (e.code, w)); time.sleep(w); continue
            return e.code, b""
        except Exception as e:
            note("    ERR " + str(e)[:70]); time.sleep(10 + i * 8)
    return None, b""


T = [
    ("20141228174812", "http://music.geocities.jp/withr17/about.html"),
    ("20141228174812", "http://music.geocities.jp/withr17/songs.html"),
    ("20141228174812", "http://music.geocities.jp/withr17/memo.html"),
]
man = []
for ts, o in T:
    st, b = fetch("http://web.archive.org/web/" + ts + "id_/" + o)
    if st == 200 and len(b) > 200:
        fn = OUT + "/pages/" + o.rsplit("/", 1)[-1] + "__" + ts + ".html"
        open(fn, "wb").write(b)
        note("OK %s %s %d" % (ts, o[-14:], len(b)))
        man.append({"url": o, "ts": ts, "file": os.path.basename(fn), "size": len(b)})
    else:
        note("-- %s %s %s" % (ts, o[-14:], st))
    time.sleep(12 + random.random() * 6)

json.dump(man, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done %d" % len(man))
