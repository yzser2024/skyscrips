# -*- coding: utf-8 -*-
"""deep-60: 分馆 www.geocities.jp/withr79 的准确快照
kisui(既遂) / wsg / prof(Profile!) / menu / first / link / music / withr
"""
import os, json, time, gzip, random, urllib.request, urllib.error

OUT = "out_deep60"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True); LOG.write(s + "\n"); LOG.flush()


def fetch(url, tries=10, timeout=60):
    b = b""
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
                w = 30 + i * 20
                note("    %d wait %ds" % (e.code, w)); time.sleep(w); continue
            return e.code, b
        except Exception as e:
            note("    ERR " + str(e)[:70]); time.sleep(10 + i * 8)
    return None, b


T = [
    ("20071225190546", "kisui.html"),
    ("20071225190556", "wsg.html"),
    ("20071017094444", "prof.html"),
    ("20050417062951", "menu.html"),
    ("20050417063103", "first.html"),
    ("20050418085507", "link.html"),
    ("20050410043737", "music.html"),
    ("20050410054233", "withr.html"),
]
man = []
for ts, name in T:
    o = "http://www.geocities.jp/withr79/" + name
    st, b = fetch("http://web.archive.org/web/" + ts + "id_/" + o)
    if st == 200 and len(b) > 150:
        fn = OUT + "/pages/" + name + "__" + ts + ".html"
        open(fn, "wb").write(b)
        note("OK %s %s %d" % (ts, name, len(b)))
        man.append({"url": o, "ts": ts, "file": os.path.basename(fn), "size": len(b)})
    else:
        note("-- %s %s %s" % (ts, name, st))
    time.sleep(18 + random.random() * 8)

json.dump(man, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done %d/%d" % (len(man), len(T)))
