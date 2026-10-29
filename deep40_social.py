# -*- coding: utf-8 -*-
"""deep-40: 社交账号指纹探测
对候选 handle 做 twitter/instagram/x 的 CDX 精确查询；
再对 ucaliy.tumblr.com 做前缀查询看有无外链页。
"""
import json, time, urllib.request, urllib.error, random, os

OUT = "out_deep40"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def fetch(url, tries=8, timeout=60):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                note("    %d 重试 %d" % (e.code, i + 1))
                time.sleep(8 + i * 12)
                continue
            return e.code, b""
        except Exception as e:
            note("    ERR %s" % str(e)[:70])
            time.sleep(8 + i * 10)
    return None, b""


HANDLES = ["ucaliy", "ucaliy79", "yukari", "oneyunn", "oneyunn79", "amorxxx79",
           "withr79", "withr17", "yun79", "yukari715", "yn715", "ucariy",
           "ukari", "yu_kari", "with_r"]

PLAT = ["twitter.com/", "x.com/", "instagram.com/", "www.instagram.com/"]

res = {}
for h in HANDLES:
    for p in PLAT:
        u = "http://web.archive.org/cdx/search/cdx?url=%s%s&output=json&fl=original,timestamp,statuscode&limit=50" % (p, h)
        st, b = fetch(u)
        key = p + h
        if st == 200 and b:
            try:
                rows = json.loads(b.decode("utf-8", "replace"))
            except Exception:
                rows = []
            rows = rows[1:] if rows and isinstance(rows[0], list) else []
            if rows:
                res[key] = rows
                note("HIT  %-34s %d 条 %s..%s" % (key, len(rows), rows[0][1], rows[-1][1]))
            else:
                note("--   %s" % key)
        else:
            note("FAIL %s -> %s" % (key, st))
        time.sleep(2 + random.random() * 2)

# tumblr 外链
for path in ["ucaliy.tumblr.com/", "ucaliy.tumblr.com/archive"]:
    u = ("http://web.archive.org/cdx/search/cdx?url=%s*&matchType=prefix&output=json"
         "&fl=original,timestamp,statuscode&filter=statuscode:200&collapse=urlkey&limit=500" % path)
    st, b = fetch(u, timeout=90)
    if st == 200 and b:
        try:
            rows = json.loads(b.decode("utf-8", "replace"))[1:]
        except Exception:
            rows = []
        res["tumblr:" + path] = rows
        note("tumblr %-30s %d 条" % (path, len(rows)))

json.dump(res, open(OUT + "/hits.json", "w"), ensure_ascii=False, indent=1)
note("done")
