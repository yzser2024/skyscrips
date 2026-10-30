# -*- coding: utf-8 -*-
"""deep-63: 抓 LOVE DISTANCE（2004-2005）与 CLOUD castle（2007）全套
- CDX 列 amorxxx79 / withr17 全站
- 优先 ld* / cc* / info / chara / story / menu 等 HTML，全取 id_ 原始字节
- 顺带取这两个企划的 MIDI（曲目本体）
"""
import os, json, time, gzip, random, urllib.request, urllib.error, urllib.parse

OUT = "out_deep63"
os.makedirs(OUT + "/files", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True); LOG.write(s + "\n"); LOG.flush()


def fetch(url, tries=8, timeout=75):
    b = b""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                if b[:2] == b"\x1f\x8b":
                    try: b = gzip.decompress(b)
                    except Exception: pass
                return r.status, b
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                w = 25 + i * 20
                note("    %d wait %ds" % (e.code, w)); time.sleep(w); continue
            return e.code, b
        except Exception as e:
            note("    ERR " + str(e)[:70]); time.sleep(10 + i * 8)
    return None, b


PREFIXES = [
    "www.geocities.jp/amorxxx79/",
    "music.geocities.jp/withr17/",
]

rows = []
for pre in PREFIXES:
    q = ("http://web.archive.org/cdx/search/cdx?url=" + urllib.parse.quote(pre, safe="")
         + "&matchType=prefix&output=json&fl=timestamp,original,statuscode,mimetype,length"
         + "&collapse=digest&limit=5000")
    st, b = fetch(q)
    note("CDX %s -> %s %d bytes" % (pre, st, len(b)))
    if st != 200 or not b.strip():
        continue
    try:
        d = json.loads(b.decode("utf-8", "replace"))
    except Exception as e:
        note("  json err " + str(e)[:60]); continue
    for r in d[1:]:
        ts, orig, sc, mt, ln = (r + ["", "", "", "", ""])[:5]
        rows.append({"ts": ts, "original": orig, "status": sc, "mime": mt, "len": ln})
    time.sleep(15 + random.random() * 10)

json.dump(rows, open(OUT + "/cdx_all.json", "w"), ensure_ascii=False, indent=1)
note("CDX 总条目 %d" % len(rows))

# ---------- 分类 ----------
HTML_EXT = (".html", ".htm", ".css", ".txt")
AUDIO_EXT = (".mid", ".midi", ".mp3", ".rmi")

KEY_HTML = ("ld", "cc", "info", "chara", "story", "menu", "top", "index", "r.", "patria", "silva")

html_rows, audio_rows = [], []
seen_url = set()
for r in rows:
    u = r["original"].split("?")[0]
    low = u.lower()
    if low.endswith(HTML_EXT):
        html_rows.append(r)
    elif low.endswith(AUDIO_EXT):
        audio_rows.append(r)
    seen_url.add(u)

note("HTML 条目 %d，音频条目 %d" % (len(html_rows), len(audio_rows)))

# 手动补一批猜测 URL（CDX 可能漏，直接撞）
GUESS = []
for i in range(0, 16):
    GUESS.append("http://www.geocities.jp/amorxxx79/cc/cc%d.html" % i)
    GUESS.append("http://music.geocities.jp/withr17/cc%d.html" % i)
for i in range(0, 16):
    GUESS.append("http://www.geocities.jp/amorxxx79/ld%d.html" % i)
for nm in ("ldmenu.html", "ldbody.html", "info.html", "chara.html", "story.html",
           "menu.html", "top.html", "r.html", "index.html",
           "cc/info.html", "cc/chara.html", "cc/story.html",
           "cc/menu.html", "cc/top.html", "cc/r.html"):
    GUESS.append("http://www.geocities.jp/amorxxx79/" + nm)
    GUESS.append("http://music.geocities.jp/withr17/" + nm)

# ---------- 抓取 ----------
man = []
done = set()


def grab(url, ts, tag):
    if url in done:
        return
    done.add(url)
    name = url.rstrip("/").split("/")[-1] or "index.html"
    host = urllib.parse.urlparse(url).netloc.replace(".", "_")
    fn = "%s__%s__%s" % (ts, host, name)
    if url.lower().endswith(AUDIO_EXT):
        fn = "%s__%s__%s" % (ts, host, name)
    wb = "http://web.archive.org/web/%sid_/%s" % (ts, url)
    st, b = fetch(wb)
    head = b[:4].hex() if b else ""
    note("%s %-14s %-6s %-52s %7d %s" % (st, ts, tag, name, len(b), head))
    if st == 200 and len(b) > 200 and not b.startswith(b"<!DOCTYPE html>\n<html>Redirect"):
        open(OUT + "/files/" + fn, "wb").write(b)
        man.append({"file": fn, "url": url, "ts": ts, "size": len(b), "magic": head, "tag": tag})
    time.sleep(9 + random.random() * 7)


# 1) HTML：先按 URL 排序，ld 优先，cc 次之
def prio(r):
    low = r["original"].lower()
    if "/ld" in low:
        return 0
    if "cc" in low:
        return 1
    if "withr17" in low:
        return 2
    return 3


html_rows.sort(key=lambda r: (prio(r), r["original"]))
for r in html_rows:
    if r["status"] not in ("200", "-"):
        continue
    grab(r["original"], r["ts"], "html")

# 2) 猜测 URL：用最近一次快照时间撞
for g in GUESS:
    if g in done:
        continue
    grab(g, "2019", "guess")

# 3) 音频
for r in audio_rows:
    if r["status"] not in ("200", "-"):
        continue
    grab(r["original"], r["ts"], "audio")

json.dump(man, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("DONE files=%d" % len(man))
