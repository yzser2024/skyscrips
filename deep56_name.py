# -*- coding: utf-8 -*-
"""deep-56: 追溯 yukari 这个名字的起点
A) CDX 列出 withr17/about.html 全部快照，挑 2014-11-16 前后各一份抓取，比对 Name 字段
B) 抓 651 站 00yukari.html 与 bbs.cgi?id=00yukari，确认这个名字 2004 年是不是她本人
"""
import os, re, json, time, gzip, random, urllib.request, urllib.error

OUT = "out_deep56"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def fetch(url, tries=6, timeout=60):
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
                w = 20 + i * 18 + random.random() * 10
                note("    %d 等待 %ds" % (e.code, int(w)))
                time.sleep(w)
                continue
            return e.code, b""
        except Exception as e:
            note("    ERR " + str(e)[:70])
            time.sleep(8 + i * 10)
    return None, b""


def cdx_all(url):
    u = ("http://web.archive.org/cdx/search/cdx?url=%s&output=json"
         "&fl=original,timestamp,statuscode,length&limit=400" % url)
    st, b = fetch(u)
    if st != 200:
        note("CDX %s -> %s" % (url, st))
        return []
    try:
        return json.loads(b.decode("utf-8", "replace"))[1:]
    except Exception:
        return []


def save(o, ts, grp):
    st, b = fetch("http://web.archive.org/web/" + ts + "id_/" + o)
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", re.sub(r"^https?://", "", o))[-80:]
    if st == 200 and len(b) > 80:
        fn = OUT + "/pages/" + grp + "__" + safe + "__" + ts + ".html"
        open(fn, "wb").write(b)
        note("OK %-8s %-14s %-50s %d" % (grp, ts, o[-50:], len(b)))
        return {"grp": grp, "url": o, "ts": ts, "file": os.path.basename(fn), "size": len(b)}
    note("-- %-8s %-14s %-50s %s" % (grp, ts, o[-50:], st))
    return None


man = []

# ---------- A) about.html 快照谱系 ----------
note("=== A) about.html 快照谱系 ===")
rows = cdx_all("music.geocities.jp/withr17/about.html")
snaps = [(r[1], r[0], r[2]) for r in rows if len(r) > 2 and str(r[2]) == "200"]
snaps.sort()
note("共 %d 份 200 快照：%s ~ %s" % (len(snaps), snaps[0][0] if snaps else "-",
                                     snaps[-1][0] if snaps else "-"))
for ts, o, _ in snaps:
    note("   " + ts)

picks = []
before = [s for s in snaps if s[0] < "20141116"]
after = [s for s in snaps if s[0] >= "20141116"]
if before:
    picks.append((before[-1][1], before[-1][0], "b_last"))     # 改名前最后一份
    picks.append((before[0][1], before[0][0], "b_first"))      # 最早一份
    if len(before) > 3:
        picks.append((before[len(before) // 2][1], before[len(before) // 2][0], "b_mid"))
if after:
    picks.append((after[0][1], after[0][0], "a_first"))        # 改名后第一份
seen = set()
for o, ts, grp in picks:
    if ts in seen:
        continue
    seen.add(ts)
    m = save(o, ts, grp)
    if m:
        man.append(m)
    time.sleep(8 + random.random() * 4)

# ---------- A2) index.html 同步比对 ----------
note("=== A2) index.html 快照 ===")
rows = cdx_all("music.geocities.jp/withr17/index.html")
s2 = sorted([(r[1], r[0]) for r in rows if len(r) > 2 and str(r[2]) == "200"])
note("共 %d 份" % len(s2))
if s2:
    b2 = [x for x in s2 if x[0] < "20141116"]
    a2 = [x for x in s2 if x[0] >= "20141116"]
    cand = []
    if b2:
        cand.append((b2[-1], "ib_last"))
    if a2:
        cand.append((a2[0], "ia_first"))
    for (ts, o), grp in cand:
        m = save(o, ts, grp)
        if m:
            man.append(m)
        time.sleep(8 + random.random() * 4)

# ---------- B) 651 站 00yukari ----------
note("=== B) 651 站 00yukari ===")
t651 = [
    ("http://www5.rocketbbs.com/651/00yukari.html", "20041108190411", "y651"),
    ("http://www5.rocketbbs.com/651/bbs.cgi?id=00yukari&mode=help", "20041118063714", "y651b"),
    ("http://www5.rocketbbs.com/651/bbs.cgi?id=00yukari&page=2", "20041116073119", "y651b"),
    ("http://www5.rocketbbs.com/651/bbs.cgi?id=00yukari&page=3", "20041227234853", "y651b"),
    ("http://www5.rocketbbs.com/651/bbs.cgi?id=00yukari&page=4", "20041227231910", "y651b"),
    ("http://www5.rocketbbs.com/651/bbs.cgi?id=00yukari&page=5", "20050109071300", "y651b"),
]
for o, ts, grp in t651:
    m = save(o, ts, grp)
    if m:
        man.append(m)
    time.sleep(8 + random.random() * 4)

json.dump(man, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done %d" % len(man))
