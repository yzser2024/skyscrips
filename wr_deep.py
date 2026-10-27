#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wr_deep.py —— With R / ONE's 相关旧站深度抓取（在 GitHub Actions 上跑，因为沙箱连不上 archive.org）

目标（来自《WithR寻找线索文档》）：
  07  www.geocities.jp/amorxxx79/        ONE's 别馆（文档称在此找到 final.mid/hanabira.mid/tudure.mid）
  12  www.geocities.jp/withr79/          早期 With R 站
  01  www1.rocketbbs.com/610/withr.html  With R BBS
  09  www5.rocketbbs.com/651/oneday.html ONE's 日记
  10  www1.rocketbbs.com/310/oneyunn.html ONE's BBS

做法：CDX 列出全部快照 → 每个 URL 取最新 200 快照（HTML 另取最早一份做对照）→ 用 id_ 模式取原始字节
产出：site/<target>/... 原始文件 + site/_manifest.json + site/_report.json
"""
import os
import re
import sys
import json
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

CDX = "http://web.archive.org/cdx/search/cdx"
WAY = "https://web.archive.org/web/%sid_/%s"

TARGETS = [
    {"id": "07_amorxxx79", "label": "ONE's 别馆 amorxxx79",
     "prefixes": ["www.geocities.jp/amorxxx79", "geocities.jp/amorxxx79",
                  "www.geocities.co.jp/amorxxx79", "geocities.co.jp/amorxxx79"]},
    {"id": "12_withr79", "label": "With R 早期站 withr79",
     "prefixes": ["www.geocities.jp/withr79", "geocities.jp/withr79",
                  "www.geocities.co.jp/withr79", "geocities.co.jp/withr79"]},
    {"id": "01_rocketbbs_withr", "label": "With R BBS (rocketbbs 610)",
     "prefixes": ["www1.rocketbbs.com/610/withr"]},
    {"id": "09_rocketbbs_oneday", "label": "ONE's 日记 (rocketbbs 651)",
     "prefixes": ["www5.rocketbbs.com/651/oneday"]},
    {"id": "10_rocketbbs_oneyunn", "label": "ONE's BBS (rocketbbs 310)",
     "prefixes": ["www1.rocketbbs.com/310/oneyunn"]},
]

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (compatible; wr-deep/1.0)"})


def cdx(prefix, tries=4):
    """列出一个 URL 前缀下的全部快照"""
    params = {
        "url": prefix,
        "matchType": "prefix",
        "output": "json",
        "limit": "40000",
        "fl": "timestamp,original,mimetype,statuscode,digest,length",
    }
    last = None
    for i in range(tries):
        try:
            r = S.get(CDX, params=params, timeout=120)
            if r.status_code == 200:
                txt = r.text.strip()
                if not txt:
                    return []
                rows = json.loads(txt)
                if not rows:
                    return []
                head = rows[0]
                out = []
                for row in rows[1:]:
                    d = dict(zip(head, row))
                    out.append(d)
                return out
            last = "HTTP %d" % r.status_code
        except Exception as e:
            last = repr(e)
        time.sleep(2 + i * 3)
    print("  CDX 失败 %s : %s" % (prefix, last), flush=True)
    return []


def safe_path(original):
    """把原始 URL 映射成安全文件路径"""
    p = urllib.parse.urlsplit(original)
    host = p.netloc.replace(":", "_")
    path = urllib.parse.unquote(p.path)
    if path.endswith("/") or path == "":
        path += "index.html"
    path = path.lstrip("/")
    parts = [x for x in path.split("/") if x not in ("", ".", "..")]
    if not parts:
        parts = ["index.html"]
    if p.query:
        parts[-1] = parts[-1] + "__q_" + re.sub(r"[^A-Za-z0-9]+", "_", p.query)[:60]
    parts = [re.sub(r'[\\:*?"<>|\x00-\x1f]', "_", x) for x in parts]
    return os.path.join(host, *parts)


def fetch_one(target_dir, item, tag):
    """下载单个快照，返回结果字典"""
    url = item["original"]
    ts = item["timestamp"]
    src = WAY % (ts, url)
    dst = os.path.join(target_dir, tag, safe_path(url))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return {"url": url, "ts": ts, "path": dst, "ok": True, "skip": True, "size": os.path.getsize(dst)}
    last = None
    for i in range(4):
        try:
            r = S.get(src, timeout=180, allow_redirects=True)
            if r.status_code == 200 and r.content:
                with open(dst, "wb") as f:
                    f.write(r.content)
                return {"url": url, "ts": ts, "path": dst, "ok": True,
                        "size": len(r.content), "ctype": r.headers.get("content-type", "")}
            if r.status_code == 404:
                return {"url": url, "ts": ts, "path": dst, "ok": False, "err": "404"}
            last = "HTTP %d" % r.status_code
        except Exception as e:
            last = repr(e)[:120]
        time.sleep(1.5 + i * 2)
    return {"url": url, "ts": ts, "path": dst, "ok": False, "err": last}


def html_to_txt(raw, out_path):
    """粗抽纯文本（HTML 用）"""
    for enc in ("utf-8", "cp932", "shift_jis", "euc_jp"):
        try:
            t = raw.decode(enc)
            break
        except Exception:
            continue
    else:
        t = raw.decode("utf-8", "replace")
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|tr|li|h[1-6]|table)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    lines = [re.sub(r"[ \t\u3000]+", " ", l).strip() for l in t.split("\n")]
    lines = [l for l in lines if l]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return len(lines)


def main():
    limit = int(os.environ.get("LIMIT", "0") or 0)
    workers = int(os.environ.get("WORKERS", "8") or 8)
    only = os.environ.get("ONLY", "").strip()

    os.makedirs("site", exist_ok=True)
    manifest = []
    report = []

    for t in TARGETS:
        if only and t["id"] not in only:
            continue
        tid = t["id"]
        print("\n########## %s  %s" % (tid, t["label"]), flush=True)
        rows = []
        for p in t["prefixes"]:
            got = cdx(p)
            print("  CDX %-40s -> %d 条" % (p, len(got)), flush=True)
            rows.extend(got)
        if not rows:
            report.append({"target": tid, "label": t["label"], "cdx": 0, "saved": 0})
            continue

        # 只留 200，按 urlkey 分组
        ok = [r for r in rows if str(r.get("statuscode")) in ("200", "-")]
        groups = {}
        for r in ok:
            key = r["original"]
            groups.setdefault(key, []).append(r)

        picked = []
        for url, lst in groups.items():
            lst.sort(key=lambda x: x["timestamp"])
            picked.append(lst[-1])                       # 最新
            if len(lst) > 1:
                first = lst[0]
                if int(first["timestamp"][:8]) < int(lst[-1]["timestamp"][:8]) - 10000:
                    picked.append(first)                 # 明显更早的一份，放 _early
        if limit:
            picked = picked[:limit]
        print("  去重后 URL %d 个，待下载快照 %d 个" % (len(groups), len(picked)), flush=True)

        latest_ids = {id(lst[-1]) for lst in groups.values()}
        jobs = [(it, "" if id(it) in latest_ids else "_early") for it in picked]

        tdir = os.path.join("site", tid)
        results = []
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(fetch_one, tdir, it, tag): (it, tag) for it, tag in jobs}
            for n, fu in enumerate(as_completed(futs), 1):
                res = fu.result()
                res["target"] = tid
                results.append(res)
                if n % 25 == 0 or n == len(jobs):
                    done = sum(1 for x in results if x.get("ok"))
                    print("    进度 %d/%d  成功 %d" % (n, len(jobs), done), flush=True)

        # 抽文本
        txt_n = 0
        for res in results:
            if not res.get("ok"):
                continue
            p = res["path"]
            low = p.lower()
            if low.endswith((".html", ".htm", ".cgi", ".txt", ".log", ".css", ".js")):
                try:
                    raw = open(p, "rb").read()
                    html_to_txt(raw, p + ".txt")
                    txt_n += 1
                except Exception:
                    pass
            manifest.append({"target": tid, "url": res["url"], "ts": res["ts"],
                             "file": os.path.relpath(p, "site"), "size": res.get("size", 0),
                             "ctype": res.get("ctype", "")})

        saved = sum(1 for x in results if x.get("ok"))
        print("  完成：成功 %d / %d，文本抽取 %d" % (saved, len(jobs), txt_n), flush=True)
        report.append({"target": tid, "label": t["label"], "cdx": len(rows),
                       "urls": len(groups), "snapshots": len(jobs), "saved": saved})

    with open("site/_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    with open("site/_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("\n==== 汇总 ====")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
