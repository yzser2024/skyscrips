# -*- coding: utf-8 -*-
"""deep-51: 补齐三站剩余页面（withr17 曲目页与 ld 小说 / withr79 / oneyunn79 内容页）"""
import os, re, json, time, gzip, random, urllib.request, urllib.error

OUT = "out_deep51"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def fetch(url, tries=6, timeout=50):
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
                note("    retry %d #%d" % (e.code, i + 1))
                time.sleep(10 + i * 12)
                continue
            return e.code, b""
        except Exception as e:
            note("    ERR " + str(e)[:60])
            time.sleep(6 + i * 8)
    return None, b""


TARGETS = [
    ("w17", "20190326213117", "http://music.geocities.jp/withr17/"),
    ("w17", "20190330163122", "http://music.geocities.jp/withr17/about.html"),
    ("w17", "20130309050538", "http://music.geocities.jp/withr17/body.html"),
    ("w17", "20111103122638", "http://music.geocities.jp/withr17/cc/cc2.html"),
    ("w17", "20111103122648", "http://music.geocities.jp/withr17/cc/cc3.html"),
    ("w17", "20111103122657", "http://music.geocities.jp/withr17/cc/cc7.html"),
    ("w17", "20111103122632", "http://music.geocities.jp/withr17/cc/index.html"),
    ("w17", "20111103122633", "http://music.geocities.jp/withr17/cc/menu.html"),
    ("w17", "20111103122634", "http://music.geocities.jp/withr17/cc/r.html"),
    ("w17", "20111103122633", "http://music.geocities.jp/withr17/cc/top.html"),
    ("w17", "20181105032112", "http://music.geocities.jp/withr17/core.html"),
    ("w17", "20181105032109", "http://music.geocities.jp/withr17/finaltale.html"),
    ("w17", "20120730042626", "http://music.geocities.jp/withr17/first.html"),
    ("w17", "20181105032110", "http://music.geocities.jp/withr17/forgery.html"),
    ("w17", "20181105032117", "http://music.geocities.jp/withr17/fuchi.html"),
    ("w17", "20181105032116", "http://music.geocities.jp/withr17/glace.html"),
    ("w17", "20190330191936", "http://music.geocities.jp/withr17/gloomy.html"),
    ("w17", "20190308201128", "http://music.geocities.jp/withr17/index.html"),
    ("w17", "20181105032119", "http://music.geocities.jp/withr17/irodori.html"),
    ("w17", "20181105032118", "http://music.geocities.jp/withr17/jane.html"),
    ("w17", "20120113082813", "http://music.geocities.jp/withr17/kage.html"),
    ("w17", "20181105032110", "http://music.geocities.jp/withr17/kageboshi.html"),
    ("w17", "20130303141452", "http://music.geocities.jp/withr17/kisui.html"),
    ("w17", "20181105032109", "http://music.geocities.jp/withr17/koei.html"),
    ("w17", "20181105032118", "http://music.geocities.jp/withr17/konokaradade.html"),
    ("w17", "20190330191015", "http://music.geocities.jp/withr17/laissez_passer.html"),
    ("w17", "20120730042737", "http://music.geocities.jp/withr17/ld/chara.html"),
    ("w17", "20120730042649", "http://music.geocities.jp/withr17/ld/home.html"),
    ("w17", "20120730042735", "http://music.geocities.jp/withr17/ld/info.html"),
    ("w17", "20111103122453", "http://music.geocities.jp/withr17/ld/ld02.html"),
    ("w17", "20111103122536", "http://music.geocities.jp/withr17/ld/ld03.html"),
    ("w17", "20111103122555", "http://music.geocities.jp/withr17/ld/ld04.html"),
    ("w17", "20111102162431", "http://music.geocities.jp/withr17/ld/ld07.html"),
    ("w17", "20111103122613", "http://music.geocities.jp/withr17/ld/ld08.html"),
    ("w17", "20111102162544", "http://music.geocities.jp/withr17/ld/ld11.html"),
    ("w17", "20120730042650", "http://music.geocities.jp/withr17/ld/right.html"),
    ("w17", "20120730042650", "http://music.geocities.jp/withr17/ld/top.html"),
    ("w17", "20130303141621", "http://music.geocities.jp/withr17/link.html"),
    ("w17", "20190307043209", "http://music.geocities.jp/withr17/memo.html"),
    ("w17", "20120730042626", "http://music.geocities.jp/withr17/menu.html"),
    ("w17", "20181105032112", "http://music.geocities.jp/withr17/mikage.html"),
    ("w17", "20120730042627", "http://music.geocities.jp/withr17/music.html"),
    ("w17", "20181105032111", "http://music.geocities.jp/withr17/noname.html"),
    ("w17", "20111102162716", "http://music.geocities.jp/withr17/ones.html"),
    ("w17", "20120730042636", "http://music.geocities.jp/withr17/reones.html"),
    ("w17", "20181105032116", "http://music.geocities.jp/withr17/songbird.html"),
    ("w17", "20190331144107", "http://music.geocities.jp/withr17/songs.html"),
    ("w17", "20181105032119", "http://music.geocities.jp/withr17/sonohi.html"),
    ("w17", "20181105032117", "http://music.geocities.jp/withr17/takara.html"),
    ("w17", "20181117043043", "http://music.geocities.jp/withr17/wsg.html"),
    ("w79", "20050524154115", "http://www.geocities.jp/withr79/bbs.html"),
    ("w79", "20050409000119", "http://www.geocities.jp/withr79/finaltale.html"),
    ("w79", "20050417063103", "http://www.geocities.jp/withr79/first.html"),
    ("w79", "20050409002250", "http://www.geocities.jp/withr79/forgery.html"),
    ("w79", "20050418085447", "http://www.geocities.jp/withr79/index.html"),
    ("w79", "20050409003536", "http://www.geocities.jp/withr79/kage.html"),
    ("w79", "20071225190546", "http://www.geocities.jp/withr79/kisui.html"),
    ("w79", "20050409004021", "http://www.geocities.jp/withr79/koei.html"),
    ("w79", "20050418085507", "http://www.geocities.jp/withr79/link.html"),
    ("w79", "20050417062951", "http://www.geocities.jp/withr79/menu.html"),
    ("w79", "20050410043737", "http://www.geocities.jp/withr79/music.html"),
    ("w79", "20071017094444", "http://www.geocities.jp/withr79/prof.html"),
    ("w79", "20050222023358", "http://www.geocities.jp/withr79/side.html"),
    ("w79", "20070608140037", "http://www.geocities.jp/withr79/songbird.html"),
    ("w79", "20050407054924", "http://www.geocities.jp/withr79/top.html"),
    ("w79", "20050410054233", "http://www.geocities.jp/withr79/withr.html"),
    ("w79", "20071225190556", "http://www.geocities.jp/withr79/wsg.html"),
    ("ony", "20151105120927", "http://oneyunn79.client.jp/kiyaku.html"),
    ("ony", "20041220134152", "http://oneyunn79.client.jp:80/asaki.html"),
    ("ony", "20041211154305", "http://oneyunn79.client.jp:80/evenif.html"),
    ("ony", "20040805120227", "http://oneyunn79.client.jp:80/finaltale.html"),
    ("ony", "20041220134156", "http://oneyunn79.client.jp:80/honoo.html"),
    ("ony", "20050418061339", "http://oneyunn79.client.jp:80/index.html"),
    ("ony", "20041211155211", "http://oneyunn79.client.jp:80/info.html"),
    ("ony", "20041224114118", "http://oneyunn79.client.jp:80/inst.html"),
    ("ony", "20040912020256", "http://oneyunn79.client.jp:80/itukakierumono.html"),
    ("ony", "20041220133539", "http://oneyunn79.client.jp:80/kabi.html"),
    ("ony", "20041224114121", "http://oneyunn79.client.jp:80/kasi.html"),
    ("ony", "20041222023549", "http://oneyunn79.client.jp:80/kingyo.html"),
    ("ony", "20041211160049", "http://oneyunn79.client.jp:80/kiseki.html"),
    ("ony", "20041208035403", "http://oneyunn79.client.jp:80/kisui.html"),
    ("ony", "20050129101307", "http://oneyunn79.client.jp:80/kiyaku2.html"),
    ("ony", "20050131042457", "http://oneyunn79.client.jp:80/ldbody.html"),
    ("ony", "20041211074635", "http://oneyunn79.client.jp:80/legend.html"),
    ("ony", "20041211074953", "http://oneyunn79.client.jp:80/link.html"),
    ("ony", "20040609025311", "http://oneyunn79.client.jp:80/midi.html"),
    ("ony", "20041220043718", "http://oneyunn79.client.jp:80/midipage.html"),
    ("ony", "20041211154717", "http://oneyunn79.client.jp:80/momo.html"),
    ("ony", "20041206150453", "http://oneyunn79.client.jp:80/mu.html"),
    ("ony", "20041224121510", "http://oneyunn79.client.jp:80/musicbox.html"),
    ("ony", "20041211073128", "http://oneyunn79.client.jp:80/nature00.html"),
    ("ony", "20041211074049", "http://oneyunn79.client.jp:80/ours.html"),
    ("ony", "20050131002514", "http://oneyunn79.client.jp:80/overture.html"),
    ("ony", "20041211075348", "http://oneyunn79.client.jp:80/pumpkin.html"),
    ("ony", "20040805010552", "http://oneyunn79.client.jp:80/record.html"),
    ("ony", "20050207011009", "http://oneyunn79.client.jp:80/ring.html"),
    ("ony", "20041211073242", "http://oneyunn79.client.jp:80/soranikietakimihe.html"),
    ("ony", "20041211074003", "http://oneyunn79.client.jp:80/syokuzai.html"),
    ("ony", "20041206062609", "http://oneyunn79.client.jp:80/toppage.html"),
    ("ony", "20041207225446", "http://oneyunn79.client.jp:80/wordsbody.html"),
    ("ony", "20041207091833", "http://oneyunn79.client.jp:80/wordspage.html"),
    ("ony", "20041211075022", "http://oneyunn79.client.jp:80/yours.html"),
    ("ony", "20041015112427", "http://oneyunn79.client.jp:80/yume100.html"),
]

man = []
for grp, ts, o in TARGETS:
    url = "http://web.archive.org/web/" + ts + "id_/" + o
    stx, b = fetch(url)
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", re.sub(r"^https?://", "", o))[-80:]
    if stx == 200 and len(b) > 80:
        fn = OUT + "/pages/" + grp + "__" + safe + "__" + ts + ".html"
        open(fn, "wb").write(b)
        note("OK %s %-7s %-52s %d" % (grp, ts, o[-52:], len(b)))
        man.append({"grp": grp, "url": o, "ts": ts, "file": os.path.basename(fn), "size": len(b)})
    else:
        note("-- %s %-7s %-52s %s" % (grp, ts, o[-52:], stx))
    time.sleep(1.8 + random.random() * 1.4)

json.dump(man, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done %d / %d" % (len(man), len(TARGETS)))
