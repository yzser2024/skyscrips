#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deep28: 把 www5.rocketbbs.com/651/ 目录下所有 200 状态的快照抓齐。
651 板 = yukari 的个人站（不是单纯留言板），共 417 个不同 html 路径。
"""
import concurrent.futures as cf
import gzip
import json
import os
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_deep28"
os.makedirs(OUT + "/pages", exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
lock = threading.Lock()
log = []


def note(s):
    with lock:
        print(s, flush=True)
        log.append(s)


def fix(u):
    try:
        return u.encode("latin-1", "ignore").decode("utf-8", "ignore")
    except Exception:
        return u


def wb(ts, url, raw=True):
    q = urllib.parse.quote(url, safe=":/?&=%~+#_,;@!$'()*[]")
    return "http://web.archive.org/web/%s%s/%s" % (ts, "id_" if raw else "", q)


def fetch(task, tries=4):
    ts, url = task
    for i in range(tries):
        try:
            req = urllib.request.Request(wb(ts, url), headers={
                "User-Agent": UA, "Accept": "*/*", "Connection": "close"})
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                b = r.read()
            if b[:2] == b"\x1f\x8b":
                try:
                    b = gzip.decompress(b)
                except Exception:
                    pass
            return ts, url, b
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                time.sleep(4 + i * 5)
                continue
            return ts, url, None
        except Exception:
            time.sleep(2 + i * 3)
    return ts, url, None


def main():
    rows = json.load(open("cdx_651_all.json"))
    tasks, seen = [], set()
    for r in rows[1:]:
        o, ts, sc = fix(r[0]), r[1], r[2]
        if sc != "200":
            continue
        o = re.sub(r"^http://www5\.rocketbbs\.com:80/", "http://www5.rocketbbs.com/", o)
        if (ts, o) in seen:
            continue
        seen.add((ts, o))
        tasks.append((ts, o))
    note("待抓 %d 个快照 / %d 个唯一 URL" % (len(tasks), len({t[1] for t in tasks})))

    idx = {}
    done = 0
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for ts, url, b in ex.map(fetch, tasks):
            done += 1
            if b is None:
                note("[%4d/%d] MISS %s %s" % (done, len(tasks), ts, url[-50:]))
                continue
            name = re.sub(r"[^\w.\-]", "_", url.split("/651/")[-1])[:80]
            fn = "%s/pages/%s__%s.html" % (OUT, name, ts)
            open(fn, "wb").write(b)
            idx.setdefault(url, []).append({"ts": ts, "file": fn, "bytes": len(b)})
            if done % 50 == 0:
                note("  进度 %d/%d" % (done, len(tasks)))

    json.dump(idx, open(OUT + "/index.json", "w"), ensure_ascii=False, indent=1)
    note("完成：%d 个 URL，%d 个文件" % (len(idx), sum(len(v) for v in idx.values())))
    open(OUT + "/log.txt", "w", encoding="utf-8").write("\n".join(log))


if __name__ == "__main__":
    main()
