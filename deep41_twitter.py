# -*- coding: utf-8 -*-
"""deep-41: 推特 @ucaliy 抢救
1) CDX 查 twitter.com/ucaliy 全部快照
2) CDX 查 twilog.org/ucaliy （日本推文全存档服务）
3) 抓 twitter 各年份代表快照原文（2011-2019）
4) 抓 twilog 首页与按月分页
"""
import os, re, json, time, gzip, urllib.request, urllib.error, random

OUT = "out_deep41"
os.makedirs(OUT + "/pages", exist_ok=True)
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
                note("    %d 重试%d" % (e.code, i + 1))
                time.sleep(8 + i * 12)
                continue
            return e.code, b""
        except Exception as e:
            note("    ERR %s" % str(e)[:70])
            time.sleep(8 + i * 10)
    return None, b""


def cdx(prefix, limit=3000):
    u = ("http://web.archive.org/cdx/search/cdx?url=%s*&matchType=prefix&output=json"
         "&fl=original,timestamp,statuscode,mimetype,length&filter=statuscode:200"
         "&collapse=urlkey&limit=%d" % (prefix, limit))
    st, b = fetch(u, timeout=120)
    if st != 200 or not b:
        note("  CDX FAIL %s -> %s" % (prefix, st))
        return []
    try:
        rows = json.loads(b.decode("utf-8", "replace"))[1:]
    except Exception:
        return []
    return rows


def fix(u):
    try:
        return u.encode("latin-1").decode("utf-8")
    except Exception:
        return u


manifest = []

for pref in ["twitter.com/ucaliy", "www.twitter.com/ucaliy", "twilog.org/ucaliy",
             "twilog.org/ucaliy/"]:
    note("=== CDX %s ===" % pref)
    rows = cdx(pref)
    note("  %d 条" % len(rows))
    if not rows:
        continue
    # 按年份取样
    byyear = {}
    for r in rows:
        y = r[1][:4]
        byyear.setdefault(y, []).append(r)
    note("  年份分布: " + ", ".join("%s:%d" % (k, len(v)) for k, v in sorted(byyear.items())))

    picks = []
    for y, lst in sorted(byyear.items()):
        lst.sort(key=lambda r: r[1])
        picks.extend(lst[:1])
        if len(lst) > 2:
            picks.extend(lst[len(lst) // 2:len(lst) // 2 + 1])
        picks.extend(lst[-1:])
    seen = set()
    for r in picks:
        ts, orig = r[1], fix(r[0])
        if ts in seen:
            continue
        seen.add(ts)
        url = "http://web.archive.org/web/%sid_/%s" % (ts, orig)
        st, b = fetch(url)
        safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", re.sub(r"^https?://", "", orig))[-100:]
        if st == 200 and len(b) > 500:
            if b[:2] == b"\x1f\x8b":
                try:
                    b = gzip.decompress(b)
                except Exception:
                    pass
            fn = "%s/pages/%s__%s.html" % (OUT, safe, ts)
            open(fn, "wb").write(b)
            note("  OK  %s %s %d" % (ts, orig, len(b)))
            manifest.append({"url": orig, "ts": ts, "file": os.path.basename(fn), "size": len(b)})
        else:
            note("  FAIL %s %s -> %s %d" % (ts, orig, st, len(b)))
        time.sleep(3 + random.random() * 3)
    json.dump(rows, open(OUT + "/cdx_%s.json" % re.sub(r"[^a-z0-9]", "_", pref), "w"),
              ensure_ascii=False)

json.dump(manifest, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done %d" % len(manifest))
