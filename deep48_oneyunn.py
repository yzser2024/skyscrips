# -*- coding: utf-8 -*-
"""deep-48: oneyunn79.client.jp（2004 年个人站）的日记页与文字页
about.html 已证实该站有 diary / record / words / bbs / link 五个内容页。
此处只抓这几个内容页的全部快照。
"""
import os, re, json, time, gzip, urllib.request, urllib.error, random

OUT = "out_deep48"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def fetch(url, tries=6, timeout=50):
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
                note("    %d 重试%d" % (e.code, i + 1))
                time.sleep(10 + i * 12)
                continue
            return e.code, b""
        except Exception as e:
            note("    ERR %s" % str(e)[:60])
            time.sleep(6 + i * 8)
    return None, b""


def fix(u):
    try:
        return u.encode("latin-1").decode("utf-8")
    except Exception:
        return u


# 取全站 CDX（不加 filter，本地筛）
u = ("http://web.archive.org/cdx/search/cdx?url=oneyunn79.client.jp&matchType=prefix"
     "&output=json&fl=original,timestamp,statuscode,length&limit=2000")
st, b = fetch(u, timeout=120)
rows = []
if st == 200 and b:
    try:
        rows = json.loads(b.decode("utf-8", "replace"))[1:]
    except Exception:
        rows = []
note("CDX %d 条" % len(rows))
json.dump(rows, open(OUT + "/cdx.json", "w"), ensure_ascii=False)

KEY = ("diary", "record", "words", "word", "bbs", "link", "about", "menu",
       "toppage", "bodypage", "index", "log")
cand = []
for r in rows:
    if len(r) < 3 or str(r[2]) != "200":
        continue
    o = fix(r[0])
    low = o.lower()
    if any(low.split("?")[0].endswith(e) for e in
           (".jpg", ".png", ".gif", ".mid", ".mp3", ".css", ".js", ".bmp")):
        continue
    if any(k in low for k in KEY):
        cand.append((r[1], o))

note("候选 %d 条" % len(cand))
# 按路径归组，每组取最新 3 份
grp = {}
for ts, o in cand:
    k = re.sub(r"^https?://", "", o).split("#")[0]
    grp.setdefault(k, []).append((ts, o))

note("路径 %d 个" % len(grp))
for k in sorted(grp):
    note("  " + k)

manifest = []
for k in sorted(grp):
    lst = sorted(grp[k])[-3:]
    for ts, o in lst:
        url = "http://web.archive.org/web/%sid_/%s" % (ts, o)
        stx, bb = fetch(url)
        safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", k)[-90:]
        if stx == 200 and len(bb) > 100:
            fn = "%s/pages/%s__%s.html" % (OUT, safe, ts)
            open(fn, "wb").write(bb)
            note("  OK %s %s %d" % (ts, k[-50:], len(bb)))
            manifest.append({"url": o, "ts": ts, "file": os.path.basename(fn), "size": len(bb)})
        else:
            note("  -- %s %s -> %s" % (ts, k[-40:], stx))
        time.sleep(2 + random.random() * 2)

json.dump(manifest, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done %d" % len(manifest))
