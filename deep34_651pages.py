# -*- coding: utf-8 -*-
"""deep-34  651 站页面并发抓取（一份/路径，含查询串去重）"""
import os, sys, json, gzip, time, re, collections, threading
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

OUT = "out_deep34"
os.makedirs(OUT + "/pages", exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
LOCK = threading.Lock()
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
DEADLINE = time.time() + 60 * 60


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


rows = json.load(open("cdx_651_all.json"))[1:]
byurl = collections.defaultdict(list)
for r in rows:
    if r[2] != "200":
        continue
    u = fix(r[0])
    if re.search(r"\.(gif|jpg|jpeg|png|mid|mp3|css|js|lzh|zip|txt)$", u, re.I):
        continue
    byurl[u].append(r[1])

note("== 唯一页面 URL %d ==" % len(byurl))

todo = []
for u, tss in byurl.items():
    tss.sort()
    todo.append((tss[0], u))          # 每个 URL 只取最早一份
todo.sort(key=lambda x: x[1])

done = [0, 0]


def work(item):
    ts, u = item
    name = u.split("/651/", 1)[-1] or "index.html"
    name = re.sub(r"[^0-9A-Za-z_.\-]", "_", name)[:88]
    if not name.lower().endswith((".html", ".htm")):
        name += ".html"
    dest = "%s/pages/%s__%s" % (OUT, name[:80], ts)
    ok = 1
    if not (os.path.exists(dest) and os.path.getsize(dest) > 30):
        ok = 1 if fetch(ts, u, dest) else 0
    with LOCK:
        done[0] += 1
        done[1] += ok
        if done[0] % 30 == 0:
            note("  %d/%d ok=%d" % (done[0], len(todo), done[1]))
    return ok


t0 = time.time()
with ThreadPoolExecutor(max_workers=6) as ex:
    res = list(ex.map(work, todo))
note("完成 ok=%d / %d  %.1f 分钟" % (sum(res), len(todo), (time.time() - t0) / 60))

p = OUT + "/pages"
fs = os.listdir(p)
note("pages: %d 个文件 %.2f MB" % (len(fs),
     sum(os.path.getsize(os.path.join(p, f)) for f in fs) / 1048576))
LOG.close()
