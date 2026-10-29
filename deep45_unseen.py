# -*- coding: utf-8 -*-
"""deep-45: 扫荡文档里未覆盖的站点
A amorkana.jp（与 amorxxx79 同源词，疑为她的另一站）
B oneyunn79.client.jp 全站（113 路径，此前只看过 6 页）
C withr17 的 ld/ 与 cc/ 两个故事企划子站
D rocketbbs 610 板 withr.html 及相关页
E soundcloud / note / wordpress 同名探测
"""
import os, re, json, time, gzip, urllib.request, urllib.error, random

OUT = "out_deep45"
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


def cdx(prefix, limit=1500):
    u = ("http://web.archive.org/cdx/search/cdx?url=%s*&matchType=prefix&output=json"
         "&fl=original,timestamp,statuscode,mimetype,length&filter=statuscode:200"
         "&collapse=urlkey&limit=%d" % (prefix, limit))
    st, b = fetch(u, timeout=120)
    if st != 200 or not b:
        note("  CDX FAIL %s -> %s" % (prefix, st))
        return []
    try:
        return json.loads(b.decode("utf-8", "replace"))[1:]
    except Exception:
        return []


def fix(u):
    try:
        return u.encode("latin-1").decode("utf-8")
    except Exception:
        return u


SKIP = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".swf", ".mid", ".midi", ".mp3",
        ".wav", ".zip", ".lzh", ".css", ".js", ".ico", ".woff")

manifest = []


def grab(orig, ts, tag):
    url = "http://web.archive.org/web/%sid_/%s" % (ts, orig)
    st, b = fetch(url)
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", re.sub(r"^https?://", "", orig))[-95:]
    if st == 200 and len(b) > 150:
        fn = "%s/pages/%s_%s_%s.html" % (OUT, tag, safe, ts)
        open(fn, "wb").write(b)
        note("  OK  %s %s %d" % (ts, orig[-60:], len(b)))
        manifest.append({"tag": tag, "url": orig, "ts": ts,
                         "file": os.path.basename(fn), "size": len(b)})
    else:
        note("  --  %s %s -> %s" % (ts, orig[-55:], st))
    return st


# ---------- A amorkana.jp ----------
note("=== A amorkana.jp ===")
rows = cdx("amorkana.jp/")
note("  %d 条" % len(rows))
pages = [(r[1], fix(r[0])) for r in rows
         if not any(r[0].lower().split("?")[0].endswith(e) for e in SKIP)]
best = {}
for ts, o in pages:
    k = re.sub(r"^https?://", "", o)
    if k not in best or ts > best[k][0]:
        best[k] = (ts, o)
note("  去重 %d" % len(best))
for k, (ts, o) in list(sorted(best.items(), key=lambda kv: kv[1][0]))[:25]:
    grab(o, ts, "A")
    time.sleep(2 + random.random() * 2)

# ---------- B oneyunn79.client.jp ----------
note("=== B oneyunn79.client.jp ===")
rows = cdx("oneyunn79.client.jp/")
note("  %d 条" % len(rows))
pages = [(r[1], fix(r[0])) for r in rows
         if not any(r[0].lower().split("?")[0].endswith(e) for e in SKIP)]
best = {}
for ts, o in pages:
    k = re.sub(r"^https?://", "", o)
    if k not in best or ts > best[k][0]:
        best[k] = (ts, o)
note("  去重 %d" % len(best))
for k, (ts, o) in sorted(best.items(), key=lambda kv: kv[1][0]):
    grab(o, ts, "B")
    time.sleep(2 + random.random() * 2)

# ---------- C withr17 的 ld/ 与 cc/ ----------
note("=== C withr17 ld/ cc/ ===")
for sub in ["ld", "cc"]:
    rows = cdx("music.geocities.jp/withr17/%s/" % sub)
    note("  %s %d 条" % (sub, len(rows)))
    pages = [(r[1], fix(r[0])) for r in rows
             if not any(r[0].lower().split("?")[0].endswith(e) for e in SKIP)]
    best = {}
    for ts, o in pages:
        k = re.sub(r"^https?://", "", o)
        if k not in best or ts > best[k][0]:
            best[k] = (ts, o)
    for k, (ts, o) in sorted(best.items(), key=lambda kv: kv[1][0]):
        grab(o, ts, "C")
        time.sleep(2 + random.random() * 2)

# ---------- D rocketbbs 610 ----------
note("=== D rocketbbs 610 ===")
for host in ["www1.rocketbbs.com/610/", "www5.rocketbbs.com/610/"]:
    rows = cdx(host, limit=600)
    note("  %s %d 条" % (host, len(rows)))
    pages = [(r[1], fix(r[0])) for r in rows
             if not any(r[0].lower().split("?")[0].endswith(e) for e in SKIP)]
    best = {}
    for ts, o in pages:
        k = re.sub(r"^https?://", "", o)
        if k not in best or ts > best[k][0]:
            best[k] = (ts, o)
    note("   去重 %d" % len(best))
    for k, (ts, o) in list(sorted(best.items(), key=lambda kv: kv[1][0]))[:25]:
        grab(o, ts, "D")
        time.sleep(2 + random.random() * 2)

# ---------- E 同名社交探测（直连） ----------
note("=== E 同名站点直连 ===")
for u in ["https://soundcloud.com/ucaliy", "https://soundcloud.com/withr",
          "https://note.com/ucaliy", "https://ucaliy.wordpress.com/",
          "https://amorkana.jp/", "https://www.yf04.com/"]:
    st, b = fetch(u, tries=2, timeout=30)
    note("  %-40s %s %d" % (u, st, len(b)))
    if st == 200 and len(b) > 500:
        fn = "%s/pages/E_%s.html" % (OUT, re.sub(r"[^a-zA-Z0-9]", "_", u)[-50:])
        open(fn, "wb").write(b)
    time.sleep(2)

json.dump(manifest, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done %d pages" % len(manifest))
