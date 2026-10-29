# -*- coding: utf-8 -*-
"""deep-39: 三个从未看过的站点全量 CDX 展开 + 抓取
   1) www.geocities.jp/withr79/   (kisui/songbird/wsg/link/bbs)
   2) yellow.ribbon.to/~withr/    (10 页)
   3) oneyunn79.client.jp/        (113 页，此前只看过首页)
"""
import os, re, json, time, gzip, urllib.request, urllib.error, random

OUT = "out_deep39"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def fetch(url, tries=6, timeout=45):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                wait = 20 + i * 25 + random.randint(0, 10)
                note("    %d, 等 %ds" % (e.code, wait))
                time.sleep(wait)
                continue
            return e.code, b""
        except Exception as e:
            note("    ERR %s" % str(e)[:80])
            time.sleep(10 + i * 12)
    return None, b""


def cdx_prefix(host_dir, limit=4000):
    url = ("http://web.archive.org/cdx/search/cdx?url=%s*&matchType=prefix"
           "&output=json&fl=original,timestamp,statuscode,mimetype,length"
           "&filter=statuscode:200&collapse=urlkey&limit=%d" % (host_dir, limit))
    st, b = fetch(url, tries=8, timeout=90)
    if st != 200 or not b:
        note("  CDX FAIL %s -> %s" % (host_dir, st))
        return []
    try:
        rows = json.loads(b.decode("utf-8", "replace"))
    except Exception as e:
        note("  CDX JSON ERR %s" % e)
        return []
    return rows[1:] if rows and isinstance(rows[0], list) else []


def fix(u):
    try:
        return u.encode("latin-1").decode("utf-8")
    except Exception:
        return u


HOSTS = [
    ("www.geocities.jp/withr79/", 40),
    ("yellow.ribbon.to/~withr/", 40),
    ("oneyunn79.client.jp/", 120),
]

SKIP_EXT = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".swf", ".mid", ".midi",
            ".mp3", ".wav", ".zip", ".lzh", ".css", ".js", ".ico")

manifest = []

for host, cap in HOSTS:
    note("=== %s ===" % host)
    rows = cdx_prefix(host)
    note("  CDX %d 条唯一 URL" % len(rows))
    if not rows:
        continue
    pages = []
    for r in rows:
        orig = fix(r[0])
        low = orig.lower()
        if any(low.split("?")[0].endswith(e) for e in SKIP_EXT):
            continue
        pages.append((r[1], orig, r[3] if len(r) > 3 else ""))
    # 按 URL 路径去重，取最新快照
    best = {}
    for ts, orig, mime in pages:
        key = re.sub(r"^https?://", "", orig).split("#")[0]
        if key not in best or ts > best[key][0]:
            best[key] = (ts, orig, mime)
    items = sorted(best.items(), key=lambda kv: kv[1][0])
    note("  去重后待抓 %d 页，上限 %d" % (len(items), cap))
    items = items[:cap]
    for key, (ts, orig, mime) in items:
        url = "http://web.archive.org/web/%sid_/%s" % (ts, orig)
        st, b = fetch(url)
        safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", key)[-110:]
        if st == 200 and len(b) > 150:
            if b[:2] == b"\x1f\x8b":
                try:
                    b = gzip.decompress(b)
                except Exception:
                    pass
            fn = "%s/pages/%s__%s.html" % (OUT, safe, ts)
            open(fn, "wb").write(b)
            note("  OK  %s %s %d" % (ts, key, len(b)))
            manifest.append({"host": host, "url": orig, "ts": ts,
                             "file": os.path.basename(fn), "size": len(b)})
        else:
            note("  FAIL %s %s -> %s" % (ts, key, st))
        time.sleep(2.5 + random.random() * 3)

json.dump(manifest, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done, %d pages" % len(manifest))
