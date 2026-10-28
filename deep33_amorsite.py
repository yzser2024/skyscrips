# -*- coding: utf-8 -*-
"""deep-33  amorxxx79 全站页面抓取（并发版，跳过 CDX）"""
import os, sys, json, gzip, time, threading
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

OUT = "out_deep33"
os.makedirs(OUT + "/pages", exist_ok=True)
os.makedirs(OUT + "/img", exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
LOCK = threading.Lock()
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
DEADLINE = time.time() + 55 * 60


def note(s):
    with LOCK:
        print(s); LOG.write(str(s) + "\n"); LOG.flush()


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def fetch(ts, orig, dest):
    if time.time() > DEADLINE:
        return 0
    u = "http://web.archive.org/web/%sid_/%s" % (ts, orig)
    for k in range(2):
        try:
            st, b = get(u, 25)
            if b[:2] == b"\x1f\x8b":
                try: b = gzip.decompress(b)
                except Exception: pass
            if len(b) < 30:
                return 0
            open(dest, "wb").write(b)
            return len(b)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(3 + k * 4); continue
            return 0
        except Exception:
            time.sleep(2)
    return 0


def fix(u):
    try: return u.encode("latin-1", "ignore").decode("utf-8", "ignore")
    except Exception: return u


rows = json.load(open("site-all.json"))[1:]
want = []
for r in rows:
    u, ts, sc, mt = fix(r[0]), r[1], r[2], r[3]
    if sc != "200":
        continue
    if "text/html" in mt:
        want.append((ts, u, "pages"))
    elif mt.startswith("image/"):
        want.append((ts, u, "img"))

note("== 待抓 %d（pages %d / img %d）==" % (
    len(want), sum(1 for x in want if x[2] == "pages"), sum(1 for x in want if x[2] == "img")))

done = [0]


def work(item):
    ts, u, kind = item
    name = u.split("amorxxx79/", 1)[-1] or "index"
    name = name.replace("/", "_").replace("%", "_").replace("?", "_")[:70]
    if kind == "pages":
        name = os.path.splitext(name)[0] + ".html"
    else:
        ext = os.path.splitext(name)[1] or ".bin"
        if not name.lower().endswith(ext):
            name += ext
    dest = os.path.join(OUT, kind, "%s__%s" % (name[:70], ts))
    if os.path.exists(dest) and os.path.getsize(dest) > 30:
        sz = 1
    else:
        sz = fetch(ts, u, dest)
    with LOCK:
        done[0] += 1
        if sz:
            pass
        if done[0] % 20 == 0:
            note("  %d/%d" % (done[0], len(want)))
    return 1 if sz else 0


t0 = time.time()
with ThreadPoolExecutor(max_workers=5) as ex:
    res = list(ex.map(work, want))
note("完成 ok=%d / %d  用时 %.1f 分钟" % (sum(res), len(want), (time.time() - t0) / 60))

for d in ("pages", "img"):
    p = os.path.join(OUT, d)
    if os.path.isdir(p):
        fs = os.listdir(p)
        note("%s: %d 个文件 %.2f MB" % (d, len(fs),
             sum(os.path.getsize(os.path.join(p, f)) for f in fs) / 1048576))
LOG.close()
