# -*- coding: utf-8 -*-
"""deep-38: 抓 withr17 的关键页（about/index/songs/菜单），目标是 finding 改名后的新名字。"""
import os, re, json, time, gzip, urllib.request, urllib.error, random

OUT = "out_deep38"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def fetch(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                wait = 15 + i * 20 + random.randint(0, 8)
                note("    %d, 等 %ds" % (e.code, wait))
                time.sleep(wait)
                continue
            return e.code, b""
        except Exception as e:
            note("    ERR %s" % e)
            time.sleep(8 + i * 10)
    return None, b""


CDX = ("http://web.archive.org/cdx/search/cdx?url=%s&output=json"
       "&fl=original,timestamp,statuscode,length&filter=statuscode:200&limit=200")


def cdx_list(path):
    st, b = fetch(CDX % ("music.geocities.jp/withr17/" + path))
    if st != 200 or not b:
        return []
    try:
        rows = json.loads(b.decode("utf-8", "replace"))
    except Exception:
        return []
    return rows[1:] if rows and isinstance(rows[0], list) else []


TARGETS = ["about.html", "index.html", "songs.html", "ones.html", "reones.html",
           "link.html", "first.html", "menu.html", "music.html", "core.html",
           "gloomy.html", "laissez_passer.html"]

for path in TARGETS:
    rows = cdx_list(path)
    note("CDX %-20s %d 条 200" % (path, len(rows)))
    if not rows:
        continue
    # 只抓最新 3 份
    rows = sorted(rows, key=lambda r: r[1])[-3:]
    for r in rows:
        ts = r[1]
        url = "http://web.archive.org/web/%sid_/http://music.geocities.jp/withr17/%s" % (ts, path)
        st, b = fetch(url)
        if st == 200 and len(b) > 200:
            fn = "%s/pages/%s__%s.html" % (OUT, re.sub(r"[^a-zA-Z0-9_.]", "_", path), ts)
            open(fn, "wb").write(b)
            note("  OK  %s  %d bytes" % (ts, len(b)))
        else:
            note("  FAIL %s  %s" % (ts, st))
        time.sleep(3 + random.random() * 3)

note("done")
