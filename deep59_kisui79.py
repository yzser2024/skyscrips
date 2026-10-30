# -*- coding: utf-8 -*-
"""deep-59: 分馆 withr79 的 kisui.html / wsg.html —— 看 2005 年那版「既遂」有没有署名与日期"""
import os, json, time, gzip, random, urllib.request, urllib.error

OUT = "out_deep59"
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


# 1) 先查 withr79 的 CDX，拿到准确路径与时间戳
for host in ("music.geocities.jp/withr79", "www.geocities.jp/withr79"):
    u = ("http://web.archive.org/cdx/search/cdx?url=http://%s&matchType=prefix"
         "&output=json&fl=timestamp,original,statuscode,length&collapse=urlkey&limit=200" % host)
    st, b = fetch(u)
    rows = []
    if st == 200 and b.strip():
        try:
            rows = json.loads(b.decode("utf-8", "replace"))[1:]
        except Exception:
            pass
    note("CDX %-28s %s rows=%d" % (host, st, len(rows)))
    for r in rows:
        note("   " + " | ".join(str(x) for x in r))
    json.dump(rows, open(OUT + "/cdx_%s.json" % host.replace("/", "_"), "w"),
              ensure_ascii=False, indent=1)
    time.sleep(12 + random.random() * 6)

# 2) 按已知猜测抓两页（若 CDX 已给出更准的 ts，以 CDX 为准人工复核）
T = [
    ("2013", "http://music.geocities.jp/withr79/kisui.html"),
    ("2013", "http://music.geocities.jp/withr79/wsg.html"),
]
man = []
for ts, o in T:
    st, b = fetch("http://web.archive.org/web/" + ts + "id_/" + o)
    if st == 200 and len(b) > 200:
        fn = OUT + "/pages/" + o.rsplit("/", 1)[-1].replace(".html", "") + ".html"
        open(fn, "wb").write(b)
        note("OK %s %s %d" % (ts, o.rsplit("/", 1)[-1], len(b)))
        man.append({"url": o, "file": os.path.basename(fn), "size": len(b)})
    else:
        note("-- %s %s %s" % (ts, o.rsplit("/", 1)[-1], st))
    time.sleep(20 + random.random() * 8)

json.dump(man, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done %d" % len(man))
