# -*- coding: utf-8 -*-
"""deep-36  定点取 amorxxx79 的 about/link/mylink 等页面，找推特等外链账号"""
import os, json, re, time, gzip, urllib.request, urllib.error, html as H

OUT = "out_deep36"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def note(s):
    print(s); LOG.write(str(s) + "\n"); LOG.flush()


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


TARGETS = [
    ("20090812235640", "http://www.geocities.jp/amorxxx79/about.html"),
    ("20090812235645", "http://www.geocities.jp/amorxxx79/link.html"),
    ("20090813031616", "http://www.geocities.jp/amorxxx79/mylink.html"),
    ("20080225164007", "http://www.geocities.jp/amorxxx79/with/"),
    ("20081202123539", "http://www.geocities.jp/amorxxx79/with/first.html"),
    ("20090813015956", "http://www.geocities.jp/amorxxx79/with/wsg.html"),
    ("20051214162053", "http://www.geocities.jp/amorxxx79/pabout.html"),
    ("20050322104124", "http://www.geocities.jp/amorxxx79/bodypage.html"),
    ("20050507061248", "http://www.geocities.jp/amorxxx79/kiyaku2.html"),
    ("20071226112251", "http://www.geocities.jp/amorxxx79/faq.html"),
    ("20080226134311", "http://www.geocities.jp/amorxxx79/diary.html"),
]

for ts, u in TARGETS:
    name = u.split("amorxxx79/", 1)[-1].replace("/", "_") or "index.html"
    dest = "%s/pages/%s__%s" % (OUT, name, ts)
    try:
        st, b = get("http://web.archive.org/web/%sid_/%s" % (ts, u), 40)
        if b[:2] == b"\x1f\x8b":
            b = gzip.decompress(b)
        open(dest, "wb").write(b)
        t = b.decode("cp932", "replace")
        links = re.findall(r'href="([^"]+)"', t, re.I)
        ext = sorted({x for x in links if x.lower().startswith("http") and "geocities" not in x
                      and "rocketbbs" not in x})
        note("== %s  %d bytes" % (name, len(b)))
        for x in ext[:40]:
            note("     " + x)
    except Exception as e:
        note("== %s FAIL %s" % (name, str(e)[:70]))
    time.sleep(0.8)

LOG.close()
