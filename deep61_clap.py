# -*- coding: utf-8 -*-
"""deep-61: 查 webclap 拍手页（id=oneyunn）是否有存档，有则抓"""
import os, re, json, time, gzip, random, urllib.request, urllib.error
from urllib.parse import quote

OUT = "out_deep61"
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
                w = 25 + i * 20
                note("    %d wait %ds" % (e.code, w)); time.sleep(w); continue
            return e.code, b
        except Exception as e:
            note("    ERR " + str(e)[:70]); time.sleep(8 + i * 6)
    return None, b


TARGETS = [
    "http://www.webclap.com/cgi-bin/clap/clap.cgi?oneyunn",
    "http://clap.webclap.com/clap.php?id=oneyunn",
    "http://www.webclap.com/cgi-bin/clap/clap.cgi?oneyunn79",
    "http://clap.webclap.com/clap.php?id=withr",
    "http://www.webclap.com/clap/clap.cgi?oneyunn",
]
allrows = {}
for u in TARGETS:
    q = ("http://web.archive.org/cdx/search/cdx?url=" + quote(u, safe="")
         + "&output=json&fl=timestamp,original,statuscode,length&limit=50")
    st, b = fetch(q)
    rows = []
    if st == 200 and b.strip():
        try:
            rows = json.loads(b.decode("utf-8", "replace"))[1:]
        except Exception:
            pass
    note("CDX %s -> %s rows=%d" % (u, st, len(rows)))
    for r in rows:
        note("    " + " | ".join(str(x) for x in r))
    allrows[u] = rows
    time.sleep(12 + random.random() * 6)

json.dump(allrows, open(OUT + "/cdx.json", "w"), ensure_ascii=False, indent=1)

# 有 200 快照就抓最早和最晚各一份
man = []
for u, rows in allrows.items():
    ok = [r for r in rows if str(r[2]) == "200"]
    if not ok:
        continue
    for r in (ok[0], ok[-1]):
        ts = r[0]
        st, b = fetch("http://web.archive.org/web/%sid_/%s" % (ts, u))
        if st == 200 and len(b) > 100:
            fn = OUT + "/pages/clap_%s_%s.html" % (re.sub(r"\W+", "_", u)[-24:], ts)
            open(fn, "wb").write(b)
            note("OK %s %s %d" % (ts, u, len(b)))
            man.append({"url": u, "ts": ts, "file": os.path.basename(fn), "size": len(b)})
        else:
            note("-- %s %s %s" % (ts, u, st))
        time.sleep(18 + random.random() * 6)

json.dump(man, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done %d" % len(man))
