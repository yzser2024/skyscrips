# -*- coding: utf-8 -*-
"""deep-44: Common Crawl 索引中检索 twitter.com/ucaliy（2012-2017 各期抓取）
Common Crawl 按月抓取全网，Twitter 个人页曾在其中大量出现。
"""
import os, json, time, urllib.request, urllib.error, gzip

OUT = "out_deep44"
os.makedirs(OUT, exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = "Mozilla/5.0 (compatible; research/1.0)"


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def get(url, tries=4, timeout=60):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "*/*"})
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
                time.sleep(8 + i * 10)
                continue
            return e.code, b""
        except Exception as e:
            note("    ERR %s" % str(e)[:60])
            time.sleep(5 + i * 8)
    return None, b""


st, b = get("https://index.commoncrawl.org/collinfo.json", timeout=90)
crawls = json.loads(b.decode("utf-8")) if st == 200 and b else []
note("crawl 期数 %d" % len(crawls))

targets = ["twitter.com/ucaliy", "twitter.com/ucaliy/*",
           "mobile.twitter.com/ucaliy", "www.twitter.com/ucaliy"]

hits = []
for c in crawls:
    name = c["id"]
    year = name.split("-")[2] if len(name.split("-")) > 2 else ""
    # 只查 2011-2018
    try:
        if not (2011 <= int(year) <= 2018):
            continue
    except Exception:
        continue
    api = c["cdx-api"]
    for t in targets:
        u = "%s?url=%s&output=json&limit=50" % (api, urllib.parse.quote(t))
        st, b = get(u, timeout=45)
        if st == 200 and b and b.strip():
            lines = b.decode("utf-8", "replace").strip().split("\n")
            ok = 0
            for ln in lines:
                try:
                    j = json.loads(ln)
                except Exception:
                    continue
                if j.get("status") in ("200", "301", "302"):
                    hits.append({"crawl": name, "url": j.get("url"),
                                 "ts": j.get("timestamp"), "status": j.get("status"),
                                 "filename": j.get("filename"), "offset": j.get("offset"),
                                 "length": j.get("length")})
                    ok += 1
            if ok:
                note("HIT %s %-28s %d" % (name, t, ok))
        elif st == 404:
            pass
        time.sleep(1.2)

json.dump(hits, open(OUT + "/hits.json", "w"), ensure_ascii=False, indent=1)
note("命中 %d 条" % len(hits))

# 顺带查 whotwi/favstar/twitcasting 的 Wayback
for pu in ["whotwi.com/ucaliy", "ja.whotwi.com/ucaliy",
           "favstar.fm/users/ucaliy", "twitcasting.tv/ucaliy",
           "twitcasting.tv/index.php/user/show/ucaliy"]:
    u = ("http://web.archive.org/cdx/search/cdx?url=%s&output=json&limit=200"
         % urllib.parse.quote(pu))
    st, b = get(u, timeout=60)
    rows = []
    if st == 200 and b:
        try:
            rows = json.loads(b.decode("utf-8"))[1:]
        except Exception:
            rows = []
    note("CDX %-45s %d" % (pu, len(rows)))
    if rows:
        for r in rows[:40]:
            note("    %s %s %s" % (r[1], r[2] if len(r) > 2 else "", r[0][:90]))
        json.dump(rows, open(OUT + "/cdx_%s.json" % pu.replace("/", "_"), "w"),
                  ensure_ascii=False)
    time.sleep(2)

note("done")
