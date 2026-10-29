# -*- coding: utf-8 -*-
"""deep-49: oneyunn79.client.jp 剩余全部页面（硬编码清单，不再查 CDX）"""
import os, re, json, time, gzip, urllib.request, urllib.error, random

OUT = "out_deep49"
os.makedirs(OUT + "/pages", exist_ok=True)
LOG = open(OUT + "/log.txt", "w", encoding="utf-8")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def note(s):
    print(s, flush=True)
    LOG.write(s + "\n")
    LOG.flush()


def fetch(url, tries=5, timeout=45):
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
                note("    retry " + str(e.code))
                time.sleep(8 + i * 10)
                continue
            return e.code, b""
        except Exception as e:
            note("    ERR " + str(e)[:60])
            time.sleep(5 + i * 8)
    return None, b""


TARGETS = [
    ("http://oneyunn79.client.jp/kiyaku.html", "20151105120927"),
    ("http://oneyunn79.client.jp:80/", "20050408200323"),
    ("http://oneyunn79.client.jp:80/about.html", "20041207162658"),
    ("http://oneyunn79.client.jp:80/aboutld.html", "20041211154656"),
    ("http://oneyunn79.client.jp:80/asaki.html", "20041220134152"),
    ("http://oneyunn79.client.jp:80/asakimenu.html", "20041224194507"),
    ("http://oneyunn79.client.jp:80/bana.html", "20041207163640"),
    ("http://oneyunn79.client.jp:80/battle.html", "20041224115545"),
    ("http://oneyunn79.client.jp:80/bbs.html", "20041207164722"),
    ("http://oneyunn79.client.jp:80/bgmmenu.html", "20041206145140"),
    ("http://oneyunn79.client.jp:80/bodypage.html", "20041207180433"),
    ("http://oneyunn79.client.jp:80/chaosmenu.html", "20041224194510"),
    ("http://oneyunn79.client.jp:80/character.html", "20041211154943"),
    ("http://oneyunn79.client.jp:80/child.html", "20041208062526"),
    ("http://oneyunn79.client.jp:80/childmenu.html", "20041224194514"),
    ("http://oneyunn79.client.jp:80/crescent.html", "20041211160145"),
    ("http://oneyunn79.client.jp:80/cyou.html", "20041208062947"),
    ("http://oneyunn79.client.jp:80/deepbluemenu.html", "20041224195904"),
    ("http://oneyunn79.client.jp:80/dollmenu.html", "20041224193744"),
    ("http://oneyunn79.client.jp:80/evenif.html", "20041211154305"),
    ("http://oneyunn79.client.jp:80/finaltale.html", "20040805120227"),
    ("http://oneyunn79.client.jp:80/hananosirabemenu.html", "20041224201526"),
    ("http://oneyunn79.client.jp:80/hers.html", "20041208063628"),
    ("http://oneyunn79.client.jp:80/hersmenu.html", "20041224193752"),
    ("http://oneyunn79.client.jp:80/hersormenu.html", "20041224195128"),
    ("http://oneyunn79.client.jp:80/honoo.html", "20041220134156"),
    ("http://oneyunn79.client.jp:80/honoomenu.html", "20041224194519"),
    ("http://oneyunn79.client.jp:80/index.html", "20050418061339"),
    ("http://oneyunn79.client.jp:80/info.html", "20041211155211"),
    ("http://oneyunn79.client.jp:80/inst.html", "20041224114118"),
    ("http://oneyunn79.client.jp:80/itukakierumono.html", "20040912020256"),
    ("http://oneyunn79.client.jp:80/kabi.html", "20041220133539"),
    ("http://oneyunn79.client.jp:80/kabimenu.html", "20041224193756"),
    ("http://oneyunn79.client.jp:80/kasi.html", "20041224114121"),
    ("http://oneyunn79.client.jp:80/keitomenu.html", "20041224194523"),
    ("http://oneyunn79.client.jp:80/kikannmenu.html", "20041224195132"),
    ("http://oneyunn79.client.jp:80/kingyo.html", "20041222023549"),
    ("http://oneyunn79.client.jp:80/kingyomenu.html", "20041224195136"),
    ("http://oneyunn79.client.jp:80/kiseki.html", "20041211160049"),
    ("http://oneyunn79.client.jp:80/kisui.html", "20041208035403"),
    ("http://oneyunn79.client.jp:80/kisuimenu.html", "20041224194527"),
    ("http://oneyunn79.client.jp:80/kiyaku2.html", "20050129101307"),
    ("http://oneyunn79.client.jp:80/kyuikomenu.html", "20041224195140"),
    ("http://oneyunn79.client.jp:80/ld.html", "20050131040450"),
    ("http://oneyunn79.client.jp:80/ldbody.html", "20050131042457"),
    ("http://oneyunn79.client.jp:80/ldmenu.html", "20041211072906"),
    ("http://oneyunn79.client.jp:80/legend.html", "20041211074635"),
    ("http://oneyunn79.client.jp:80/legendmenu.html", "20041224195145"),
    ("http://oneyunn79.client.jp:80/link.html", "20041211074953"),
    ("http://oneyunn79.client.jp:80/menu.html", "20041206150140"),
    ("http://oneyunn79.client.jp:80/midi.html", "20040609025311"),
    ("http://oneyunn79.client.jp:80/midimenu.html", "20041224014250"),
    ("http://oneyunn79.client.jp:80/midipage.html", "20041220043718"),
    ("http://oneyunn79.client.jp:80/minamomenu.html", "20041224195148"),
    ("http://oneyunn79.client.jp:80/momo.html", "20041211154717"),
    ("http://oneyunn79.client.jp:80/mu.html", "20041206150453"),
    ("http://oneyunn79.client.jp:80/musicbox.html", "20041224121510"),
    ("http://oneyunn79.client.jp:80/nature00.html", "20041211073128"),
    ("http://oneyunn79.client.jp:80/nature00menu.html", "20041224195908"),
    ("http://oneyunn79.client.jp:80/ours.html", "20041211074049"),
    ("http://oneyunn79.client.jp:80/oursmenu.html", "20041224193804"),
    ("http://oneyunn79.client.jp:80/outmenu.html", "20041224192931"),
    ("http://oneyunn79.client.jp:80/overture.html", "20050131002514"),
    ("http://oneyunn79.client.jp:80/pumpkin.html", "20041211075348"),
    ("http://oneyunn79.client.jp:80/pumpkinmenu.html", "20041224195527"),
    ("http://oneyunn79.client.jp:80/record.html", "20040805010552"),
    ("http://oneyunn79.client.jp:80/ring.html", "20050207011009"),
    ("http://oneyunn79.client.jp:80/skymenu.html", "20041224192934"),
    ("http://oneyunn79.client.jp:80/soranikietakimihe.html", "20041211073242"),
    ("http://oneyunn79.client.jp:80/soranikietamenu.html", "20041224201155"),
    ("http://oneyunn79.client.jp:80/soraorumenu.html", "20050128043527"),
    ("http://oneyunn79.client.jp:80/specimenofbutterfliesmenu.html", "20041224205328"),
    ("http://oneyunn79.client.jp:80/syokuzai.html", "20041211074003"),
    ("http://oneyunn79.client.jp:80/terramenu.html", "20041224194531"),
    ("http://oneyunn79.client.jp:80/toppage.html", "20041206062609"),
    ("http://oneyunn79.client.jp:80/trilogymenu.html", "20041224195530"),
    ("http://oneyunn79.client.jp:80/wordsbody.html", "20041207225446"),
    ("http://oneyunn79.client.jp:80/wordsmenu.html", "20041207225450"),
    ("http://oneyunn79.client.jp:80/wordspage.html", "20041207091833"),
    ("http://oneyunn79.client.jp:80/yotyoumenu.html", "20041224195152"),
    ("http://oneyunn79.client.jp:80/yours.html", "20041211075022"),
    ("http://oneyunn79.client.jp:80/yoursmenu.html", "20041224194535"),
    ("http://oneyunn79.client.jp:80/yume100.html", "20041015112427"),
]

man = []
for o, ts in TARGETS:
    url = "http://web.archive.org/web/" + ts + "id_/" + o
    stx, b = fetch(url)
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", re.sub(r"^https?://", "", o))[-90:]
    if stx == 200 and len(b) > 100:
        fn = OUT + "/pages/" + safe + "__" + ts + ".html"
        open(fn, "wb").write(b)
        note("OK  " + ts + " " + o[-40:] + " " + str(len(b)))
        man.append({"url": o, "ts": ts, "file": os.path.basename(fn), "size": len(b)})
    else:
        note("--  " + ts + " " + o[-38:] + " -> " + str(stx))
    time.sleep(1.8 + random.random() * 1.6)

json.dump(man, open(OUT + "/manifest.json", "w"), ensure_ascii=False, indent=1)
note("done " + str(len(man)))
