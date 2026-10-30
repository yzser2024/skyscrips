# -*- coding: utf-8 -*-
"""deep-58: 旧菜单四栏（Profile/Board/Link/Re:ONE's）目标页取证
- 精确 CDX：board.html / profile.html / diary.html / reones.html 的完整时间线（含状态码）
- 抓 reones.html(2012) / ones.html(2011) / music.html(2012) / menu.html(2011)
"""
import os, re, json, time, gzip, random, urllib.request, urllib.error

OUT = "out_deep58"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True); LOG.write(s + "\n"); LOG.flush()


def fetch(url, tries=8, timeout=60):
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


# ---------- 1. 精确 CDX ----------
PAGES = ["board.html", "profile.html", "prof.html", "diary.html", "reones.html", "ones.html"]
cdx_all = {}
for p in PAGES:
    u = ("http://web.archive.org/cdx/search/cdx?url=http://music.geocities.jp/withr17/"
         + p + "&output=json&fl=timestamp,original,statuscode,mimetype,length&limit=200")
    st, b = fetch(u, tries=6)
    rows = []
    if st == 200 and b.strip():
        try:
            rows = json.loads(b.decode("utf-8", "replace"))
            rows = rows[1:]
        except Exception as e:
            note("cdx parse err %s %s" % (p, e))
    note("CDX %-13s %s rows=%d" % (p, st, len(rows)))
    cdx_all[p] = rows
    for r in rows:
        note("      " + " | ".join(str(x) for x in r))
    time.sleep(10 + random.random() * 8)

json.dump(cdx_all, open(OUT + "/cdx_exact.json", "w"), ensure_ascii=False, indent=1)

# ---------- 2. 抓正文 ----------
T = [
    ("20120730042636", "http://music.geocities.jp/withr17/reones.html"),
    ("20111102162716", "http://music.geocities.jp/withr17/ones.html"),
    ("20120730042627", "http://music.geocities.jp/withr17/music.html"),
    ("20110926192458", "http://music.geocities.jp/withr17/menu.html"),
]
man = []
for ts, o in T:
    st, b = fetch("http://web.archive.org/web/" + ts + "id_/" + o)
    if st == 200 and len(b) > 200:
        fn = OUT + "/pages/" + o.rsplit("/", 1)[-1] + "__" + ts + ".html"
        open(fn, "wb").write(b)
        note("OK %s %s %d" % (ts, o.rsplit("/", 1)[-1], len(b)))
        man.append({"url": o, "ts": ts, "file": os.path.basename(fn), "size": len(b)})
    else:
        note("-- %s %s %s" % (ts, o.rsplit("/", 1)[-1], st))
    time.sleep(20 + random.random() * 10)

json.dump(man, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done %d" % len(man))
