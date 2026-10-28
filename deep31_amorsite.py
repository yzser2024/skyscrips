# -*- coding: utf-8 -*-
"""deep-31  amorxxx79 全站页面抓取 + diary/ 图片 CDX 复查"""
import os, sys, json, gzip, time, urllib.request, urllib.error, urllib.parse

OUT = "out_deep31"
os.makedirs(OUT + "/pages", exist_ok=True)
os.makedirs(OUT + "/img", exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")


def note(s):
    print(s); LOG.write(str(s) + "\n"); LOG.flush()


def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def cdx(url, extra=""):
    q = ("http://web.archive.org/cdx/search/cdx?url=%s&output=json&fl=original,timestamp,"
         "statuscode,mimetype,length&limit=3000&%s" % (urllib.parse.quote(url, safe=""), extra))
    for k in range(3):
        try:
            st, b = get(q, 90)
            if b[:1] in (b"[", b"{"):
                return json.loads(b.decode("utf-8", "replace"))
        except Exception as e:
            note("  cdx retry %d %s" % (k, e))
            time.sleep(3 + k * 4)
    return []


def fetch(ts, orig, dest, strip=True):
    """取 Wayback 原始字节（id_ = 不改写）"""
    u = "http://web.archive.org/web/%sid_/%s" % (ts, orig)
    for k in range(3):
        try:
            st, b = get(u, 60)
            if b[:2] == b"\x1f\x8b":
                try: b = gzip.decompress(b)
                except Exception: pass
            if len(b) < 40:
                return 0
            open(dest, "wb").write(b)
            return len(b)
        except urllib.error.HTTPError as e:
            if e.code in (503, 429):
                time.sleep(4 + k * 5); continue
            return 0
        except Exception:
            time.sleep(2 + k * 3)
    return 0


# ---------- 1) diary/ 目录图片 CDX 复查 ----------
note("== 1) diary/ 图片 CDX ==")
for pfx in ["www.geocities.jp/amorxxx79/diary/", "www.geocities.jp/amorxxx79/diary"]:
    rows = cdx(pfx + "*", "matchType=prefix")
    note("  prefix %s -> %d 条" % (pfx, max(0, len(rows) - 1)))
    if len(rows) > 1:
        for r in rows[1:]:
            note("     " + "  ".join(str(x) for x in r))
    time.sleep(2)

# ---------- 2) 全站 200 状态 html + 图片 ----------
rows = json.load(open("site-all.json"))[1:]
def fix(u):
    try: return u.encode("latin-1", "ignore").decode("utf-8", "ignore")
    except Exception: return u

want = []
for r in rows:
    u, ts, sc, mt = fix(r[0]), r[1], r[2], r[3]
    if sc != "200":
        continue
    if "text/html" in mt:
        want.append((ts, u, "html"))
    elif mt.startswith("image/"):
        want.append((ts, u, "img"))

note("== 2) 待抓 %d 条（html %d / img %d）==" % (
    len(want), sum(1 for x in want if x[2] == "html"), sum(1 for x in want if x[2] == "img")))

n_ok = 0
for i, (ts, u, kind) in enumerate(want, 1):
    name = u.split("amorxxx79/", 1)[-1] or "index"
    name = name.replace("/", "_").replace("%", "_").replace("?", "_")[:70]
    ext = ".html" if kind == "html" else os.path.splitext(name)[1] or ".bin"
    if kind == "html":
        name = os.path.splitext(name)[0] + ".html"
    dest = os.path.join(OUT, "pages" if kind == "html" else "img", "%s__%s" % (name, ts))
    if os.path.exists(dest) and os.path.getsize(dest) > 40:
        n_ok += 1; continue
    sz = fetch(ts, u, dest)
    if sz:
        n_ok += 1
    if i % 20 == 0:
        note("  %d/%d  ok=%d" % (i, len(want), n_ok))
    time.sleep(0.6)
note("抓取完成 ok=%d / %d" % (n_ok, len(want)))

for d in ("pages", "img"):
    p = os.path.join(OUT, d)
    if os.path.isdir(p):
        note("%s: %d 个文件 %.1f MB" % (d, len(os.listdir(p)),
             sum(os.path.getsize(os.path.join(p, f)) for f in os.listdir(p)) / 1048576))
LOG.close()
