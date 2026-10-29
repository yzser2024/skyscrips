# -*- coding: utf-8 -*-
"""deep-43: 经 r.jina.ai 代理读取 twilog（GitHub IP 被 twilog 429，需换出口）"""
import os, re, json, time, urllib.request, urllib.error, random, gzip

OUT = "out_deep43"
os.makedirs(OUT + "/txt", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def fetch(url, tries=4, timeout=90):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "*/*", "X-Return-Format": "markdown"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                if b[:2] == b"\x1f\x8b":
                    try:
                        b = gzip.decompress(b)
                    except Exception:
                        pass
                return r.status, b
        except urllib.error.HTTPError as e:
            note("    HTTP %d %s" % (e.code, url[-60:]))
            if e.code in (429, 503, 502, 504):
                time.sleep(15 + i * 15)
                continue
            return e.code, b""
        except Exception as e:
            note("    ERR %s" % str(e)[:60])
            time.sleep(10 + i * 10)
    return None, b""


def jina(target):
    return "https://r.jina.ai/" + target


manifest = []

# 1) 直连再试一次（可能刚才只是瞬时限流）
st, b = fetch("https://twilog.org/ucaliy", tries=2, timeout=40)
note("直连 twilog -> %s %d" % (st, len(b)))
if st == 200 and len(b) > 2000:
    open(OUT + "/txt/direct_home.html", "wb").write(b)
    note("  直连可用")
else:
    # 2) jina 代理
    st, b = fetch(jina("https://twilog.org/ucaliy"))
    note("jina twilog -> %s %d" % (st, len(b)))
    if st == 200 and b:
        open(OUT + "/txt/jina_home.md", "wb").write(b)
        head = b.decode("utf-8", "replace")[:1500]
        note("  预览: " + re.sub(r"\s+", " ", head)[:800])
        manifest.append({"url": "twilog-home", "size": len(b)})

        # 统计页
        st2, b2 = fetch(jina("https://twilog.org/ucaliy/stats"))
        note("jina stats -> %s %d" % (st2, len(b2)))
        if st2 == 200 and b2:
            open(OUT + "/txt/jina_stats.md", "wb").write(b2)
            note("  " + re.sub(r"\s+", " ", b2.decode("utf-8", "replace"))[:600])

        # 3) 推特主页经 jina（也许能拿到现账号信息）
        st3, b3 = fetch(jina("https://twitter.com/ucaliy"))
        note("jina twitter -> %s %d" % (st3, len(b3)))
        if st3 == 200 and b3:
            open(OUT + "/txt/jina_twitter.md", "wb").write(b3)

json.dump(manifest, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done")
