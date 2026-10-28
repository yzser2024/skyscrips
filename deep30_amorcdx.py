#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deep30: 查 amorxxx79 站下到底有哪些资源被真的存过（含图片）。"""
import gzip
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = "out_deep30"
os.makedirs(OUT, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
log = []


def note(s):
    print(s, flush=True)
    log.append(s)


def get(u, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90, context=CTX) as r:
                b = r.read()
            if b[:2] == b"\x1f\x8b":
                try:
                    b = gzip.decompress(b)
                except Exception:
                    pass
            return b
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 502, 504):
                time.sleep(6 + i * 5); continue
            raise
        except Exception:
            time.sleep(4 + i * 5)
    return b"[]"


Q = [
    ("diary-dir", "http://web.archive.org/cdx/search/cdx?url=www.geocities.jp/amorxxx79/diary"
                  "&matchType=prefix&fl=original,timestamp,statuscode,mimetype,length"
                  "&collapse=urlkey&limit=500&output=json"),
    ("site-all", "http://web.archive.org/cdx/search/cdx?url=www.geocities.jp/amorxxx79"
                 "&matchType=prefix&fl=original,timestamp,statuscode,mimetype,length"
                 "&collapse=urlkey&limit=1500&output=json"),
]

for tag, u in Q:
    try:
        b = get(u)
        rows = json.loads(b)
        note("== %-10s %d 条" % (tag, max(0, len(rows) - 1)))
        json.dump(rows, open("%s/%s.json" % (OUT, tag), "w"), ensure_ascii=False, indent=1)
        for r in rows[1:201]:
            note("   " + "  ".join(str(x) for x in r))
    except Exception as e:
        note("== %-10s FAIL %s" % (tag, str(e)[:100]))
    time.sleep(3)

open(OUT + "/log.txt", "w", encoding="utf-8").write("\n".join(log))
