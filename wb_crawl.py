#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wayback Machine 归档爬取工具
============================

把 web.archive.org 上的历史快照抓成本地可离线浏览的静态站。

三个子命令：
  list   只查快照清单（先看看这站被存了多少页）
  fetch  抓整站（HTML + 图片 + CSS + JS，自动改成相对链接）
  page   抓单个页面 + 它的资源

示例：
  python wb_crawl.py list  example.com
  python wb_crawl.py fetch example.com --limit 20
  python wb_crawl.py fetch example.com --workers 4 --delay 0.5
  python wb_crawl.py page  http://example.com/about.html

依赖：requests（pip install requests）
"""

import argparse
import hashlib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote, urljoin, urlsplit

try:
    import requests
except ImportError:
    sys.exit("缺少依赖，请先执行：  pip install requests")

# ---------------------------------------------------------------- 常量

UA = ("Mozilla/5.0 (compatible; personal-site-archiver/1.0; "
      "archiving for personal offline reading)")
CDX_API = "https://web.archive.org/cdx/search/cdx"
WAYBACK = "https://web.archive.org/web"

# 匹配 web.archive.org/web/20190101000000id_/ 这类前缀
WB_PREFIX = re.compile(r"^https?://web\.archive\.org/web/\d{1,14}(?:[a-z]{2}_)?/", re.I)

# 属性改写：href / src / action / poster / data-src
ATTR_RE = re.compile(r"(?i)(\s(?:href|src|action|poster|data-src|data-original)\s*=\s*)(['\"])(.*?)\2")

# CSS 里的 url(...)
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)", re.I)

# 视为页面的扩展名
PAGE_EXT = {"", ".html", ".htm", ".xhtml", ".shtml",
            ".php", ".asp", ".aspx", ".jsp", ".cgi", ".pl"}

# Windows 文件名非法字符
BAD_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')

# ---------------------------------------------------------------- 网络层

class Throttle(object):
    """全局限速：两次请求之间至少间隔 delay 秒。"""

    def __init__(self, delay=0.4):
        self.delay = max(0.0, float(delay))
        self.lock = threading.Lock()
        self.last = 0.0

    def wait(self):
        if self.delay <= 0:
            return
        with self.lock:
            gap = time.time() - self.last
            if gap < self.delay:
                time.sleep(self.delay - gap)
            self.last = time.time()


_session = requests.Session()
_session.headers.update({
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,image/*,*/*;q=0.8",
    "Accept-Language": "ja,en;q=0.8,zh;q=0.6",
})
_adapter = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=16, max_retries=0)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)
_throttle = Throttle(0.4)


def http_get(url, params=None, tries=4, timeout=90):
    """带限速与指数退避的 GET。返回 Response 或 None。"""
    for i in range(tries):
        _throttle.wait()
        try:
            r = _session.get(url, params=params, timeout=timeout)
        except requests.ConnectionError as e:
            print("    连不上（第 %d 次）：%s" % (i + 1, str(e)[:120]), flush=True)
            if i == 0:
                print("    提示：archive.org 在部分地区需要代理，可加 --proxy http://127.0.0.1:7890", flush=True)
            time.sleep(2 * (i + 1))
            continue
        except requests.RequestException as e:
            print("    网络错误（第 %d 次）：%s" % (i + 1, str(e)[:120]), flush=True)
            time.sleep(3 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            wait = 5 * (i + 1)
            print("    HTTP %d，退避 %ds ..." % (r.status_code, wait), flush=True)
            time.sleep(wait)
            continue
        return r
    return None


def decode_body(resp):
    """按 Content-Type / meta charset 解码 HTML。"""
    ctype = resp.headers.get("Content-Type", "")
    m = re.search(r"charset=([\w\-]+)", ctype, re.I)
    enc = m.group(1) if m else None
    if not enc:
        m2 = re.search(rb"<meta[^>]+charset=[\"']?([\w\-]+)", resp.content[:8192], re.I)
        if m2:
            enc = m2.group(1).decode("ascii", "ignore")
    for cand in (enc, "utf-8", "shift_jis", "euc-jp", "gb18030"):
        if not cand:
            continue
        try:
            return resp.content.decode(cand)
        except (LookupError, UnicodeDecodeError):
            continue
    return resp.content.decode("utf-8", "replace")


# ---------------------------------------------------------------- 工具函数

def normalize_domain(s):
    s = s.strip().strip("'\"")
    s = re.sub(r"^https?://", "", s, flags=re.I)
    return s.rstrip("/")


def url_to_path(url):
    """URL → 本地相对路径。"""
    p = urlsplit(url)
    path = unquote(p.path or "/")
    if path.endswith("/"):
        path += "index.html"
    segs = [s for s in path.split("/") if s not in ("", ".", "..")]
    if not segs:
        segs = ["index.html"]
    segs = [BAD_CHARS.sub("_", s) for s in segs]
    last = segs[-1]
    if os.path.splitext(last)[1].lower() in PAGE_EXT:
        if os.path.splitext(last)[1] == "":
            segs[-1] = last + ".html"
    if p.query:
        h = hashlib.md5(p.query.encode("utf-8")).hexdigest()[:8]
        name, ext = os.path.splitext(segs[-1])
        segs[-1] = "%s__%s%s" % (name, h, ext)
    # Windows 路径长度保护
    if len(segs[-1]) > 120:
        name, ext = os.path.splitext(segs[-1])
        segs[-1] = name[:100] + "_" + hashlib.md5(segs[-1].encode("utf-8")).hexdigest()[:8] + ext
    return os.path.join(*segs)


def write_bytes(dst, data):
    d = os.path.dirname(dst)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(dst, "wb") as f:
        f.write(data)


def save_json(path, obj):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def resolve_target(tgt, page_url, page_rel, hosts, page_ts, found):
    """把 HTML 里的一个链接/资源地址改成相对路径；返回新值。"""
    t = tgt.strip()
    if not t:
        return tgt
    low = t.lower()
    if t.startswith("#") or low.startswith(("data:", "javascript:", "mailto:",
                                            "tel:", "about:", "blob:", "ftp:")):
        return tgt
    if WB_PREFIX.match(t):
        t = WB_PREFIX.sub("", t)
    try:
        absu = urljoin(page_url, t.replace("&amp;", "&"))
    except Exception:
        return tgt
    p = urlsplit(absu)
    if p.scheme not in ("http", "https"):
        return tgt
    if p.netloc.lower() not in hosts:
        return tgt
    rel = url_to_path(absu)
    found[absu] = (page_ts, rel)
    out_rel = os.path.relpath(rel, os.path.dirname(page_rel) or ".").replace(os.sep, "/")
    return out_rel


# ---------------------------------------------------------------- CDX 清单

def cdx_list(domain, limit=None, latest=False, from_year=None, to_year=None, prefix=True):
    """查 CDX 索引，返回 [{url, ts, mime, size}, ...]。

    默认 collapse=urlkey：每个 URL 只留一条（最早快照）。
    latest=True：不加 collapse，本地按 URL 取时间戳最大的那条（慢，但拿到最新版）。
    """
    domain = normalize_domain(domain)
    params = [
        ("url", domain + "/*" if prefix else domain),
        ("output", "json"),
        ("fl", "timestamp,original,statuscode,mimetype,length"),
        ("filter", "statuscode:200"),
    ]
    if not latest:
        params.append(("collapse", "urlkey"))
    if from_year:
        params.append(("from", str(from_year)))
    if to_year:
        params.append(("to", str(to_year) + "1231"))
    if limit and not latest:
        params.append(("limit", str(limit)))

    print("查询 CDX 索引：%s%s" % (domain, "/*" if prefix else ""), flush=True)
    r = http_get(CDX_API, params=params, timeout=240)
    if r is None:
        sys.exit("CDX 查询失败（网络问题或被限流），稍后重试或把 --delay 调大")
    if r.status_code != 200:
        sys.exit("CDX 返回 HTTP %d：%s" % (r.status_code, r.text[:200]))
    text = r.text.strip()
    if not text:
        return []
    try:
        rows = json.loads(text)
    except ValueError:
        sys.exit("CDX 返回的不是 JSON（可能被限流）：%s" % text[:200])
    if not rows:
        return []
    head = rows[0]
    out = {}
    for row in rows[1:]:
        d = dict(zip(head, row))
        ts, orig = d.get("timestamp", ""), d.get("original", "")
        if not orig:
            continue
        item = {"url": orig, "ts": ts, "mime": d.get("mimetype", ""),
                "size": d.get("length", "")}
        if latest:
            old = out.get(orig)
            if old is None or ts > old["ts"]:
                out[orig] = item
        else:
            out.setdefault(orig, item)
    items = sorted(out.values(), key=lambda x: x["url"])
    if limit:
        items = items[:limit]
    return items


# ---------------------------------------------------------------- fetch

def cmd_fetch(args):
    domain = normalize_domain(args.domain)
    root = urlsplit("http://" + domain).netloc.lower()
    hosts = {root}
    if root.startswith("www."):
        hosts.add(root[4:])
    else:
        hosts.add("www." + root)

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    man_path = os.path.join(out, "manifest.json")

    items = None
    if args.resume:
        items = load_json(man_path)
    if not items:
        items = cdx_list(domain, limit=args.limit, latest=args.latest,
                         from_year=args.from_year, to_year=args.to_year)
        save_json(man_path, items)
    if args.limit:
        items = items[:args.limit]
    print("快照清单：%d 个 URL" % len(items))
    if not items:
        print("没有可用快照（可能是 robots 限制、域名写错，或该站从未被归档）")
        return

    pages, assets = [], {}
    for it in items:
        rel = url_to_path(it["url"])
        ext = os.path.splitext(rel)[1].lower()
        if ext in PAGE_EXT:
            pages.append((it["url"], it["ts"], rel))
        else:
            assets[it["url"]] = (it["ts"], rel)
    print("页面 %d 个，直接资源 %d 个" % (len(pages), len(assets)))

    stats = {"ok": 0, "skip": 0, "fail": 0}
    lock = threading.Lock()
    discovered = {}

    def fetch_page(u, ts, rel):
        dst = os.path.join(out, rel)
        if args.resume and os.path.exists(dst) and os.path.getsize(dst) > 0:
            with lock:
                stats["skip"] += 1
            return
        src = "%s/%sid_/%s" % (WAYBACK, ts, u)
        r = http_get(src)
        if r is None or r.status_code != 200:
            with lock:
                stats["fail"] += 1
            return
        ctype = r.headers.get("Content-Type", "").lower()
        if not ctype.startswith("text/") and "html" not in ctype:
            write_bytes(dst, r.content)
            with lock:
                stats["ok"] += 1
            return
        html = decode_body(r)
        found = {}

        def repl(m):
            attr, q, tgt = m.group(1), m.group(2), m.group(3)
            new = resolve_target(tgt, u, rel, hosts, ts, found)
            return "%s%s%s%s" % (attr, q, new, q)

        html2 = ATTR_RE.sub(repl, html)
        write_bytes(dst, html2.encode("utf-8"))
        with lock:
            stats["ok"] += 1
            discovered.update(found)

    print("开始抓取页面 ...", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(fetch_page, u, ts, rel) for u, ts, rel in pages]
        for i, f in enumerate(as_completed(futs), 1):
            f.result()
            if i % 20 == 0 or i == len(futs):
                print("  页面 %d/%d  ok=%d skip=%d fail=%d"
                      % (i, len(futs), stats["ok"], stats["skip"], stats["fail"]), flush=True)

    if args.pages_only:
        print("已跳过资源下载（--pages-only）")
    else:
        todo = dict(discovered)
        for u, v in assets.items():
            todo.setdefault(u, v)
        seen = set()
        print("开始下载资源（图片/CSS/JS）...", flush=True)
        for rnd in range(1, 4):
            batch = {u: v for u, v in todo.items() if u not in seen}
            if not batch:
                break
            print("  第 %d 轮：%d 个" % (rnd, len(batch)), flush=True)

            def fetch_asset(u, ts, rel):
                dst = os.path.join(out, rel)
                if args.resume and os.path.exists(dst) and os.path.getsize(dst) > 0:
                    with lock:
                        stats["skip"] += 1
                    return {}
                src = "%s/%sid_/%s" % (WAYBACK, ts, u)
                r = http_get(src, timeout=120)
                if r is None or r.status_code != 200:
                    with lock:
                        stats["fail"] += 1
                    return {}
                body = r.content
                new = {}
                if rel.lower().endswith(".css"):
                    text = decode_body(r)

                    def crepl(m):
                        q, t = m.group(1), m.group(2).strip()
                        if t.lower().startswith(("data:", "#")):
                            return m.group(0)
                        try:
                            absu = urljoin(u, t)
                        except Exception:
                            return m.group(0)
                        pp = urlsplit(absu)
                        if pp.netloc.lower() not in hosts:
                            return m.group(0)
                        nrel = url_to_path(absu)
                        new[absu] = (ts, nrel)
                        orel = os.path.relpath(nrel, os.path.dirname(rel) or ".").replace(os.sep, "/")
                        return "url(%s%s%s)" % (q or "", orel, q or "")

                    body = CSS_URL_RE.sub(crepl, text).encode("utf-8")
                write_bytes(dst, body)
                with lock:
                    stats["ok"] += 1
                return new

            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                futs = {ex.submit(fetch_asset, u, v[0], v[1]): u for u, v in batch.items()}
                for f in as_completed(futs):
                    u = futs[f]
                    seen.add(u)
                    try:
                        extra = f.result() or {}
                    except Exception:
                        extra = {}
                    for eu, ev in extra.items():
                        if eu not in seen and eu not in todo:
                            todo[eu] = ev

    report = {"domain": domain, "pages": len(pages), "assets": len(assets),
              "ok": stats["ok"], "skip": stats["skip"], "fail": stats["fail"],
              "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    save_json(os.path.join(out, "_report.json"), report)
    print("\n完成：成功 %d，跳过 %d（已存在），失败 %d"
          % (stats["ok"], stats["skip"], stats["fail"]))
    print("输出目录：%s" % out)
    print("打开 %s 即可离线浏览" % os.path.join(out, "index.html"))


def cmd_list(args):
    items = cdx_list(args.domain, limit=args.limit, latest=args.latest,
                     from_year=args.from_year, to_year=args.to_year)
    if not items:
        print("没有查到快照")
        return
    print("共 %d 个 URL" % len(items))
    for it in items[:30]:
        print("  %s  %s" % (it["ts"], it["url"]))
    if len(items) > 30:
        print("  ... 其余 %d 条省略" % (len(items) - 30))
    out = args.out or "urls.txt"
    with open(out, "w", encoding="utf-8") as f:
        for it in items:
            f.write("%s\t%s\n" % (it["ts"], it["url"]))
    save_json(os.path.splitext(out)[0] + ".json", items)
    print("清单已写入：%s" % out)


def cmd_page(args):
    url = args.url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    ts = args.ts
    if not ts:
        r = http_get(CDX_API, params=[("url", url), ("output", "json"),
                                      ("fl", "timestamp,original,statuscode"),
                                      ("filter", "statuscode:200"), ("limit", "-1")],
                     timeout=120)
        if r is None or r.status_code != 200:
            sys.exit("查询该 URL 的快照失败")
        try:
            rows = r.json()
        except ValueError:
            sys.exit("CDX 返回异常（可能被限流）")
        if len(rows) < 2:
            sys.exit("该 URL 没有可用快照")
        ts = rows[-1][0]
        print("使用最新快照：%s" % ts)
    # 复用 fetch 逻辑：构造一个只含该 URL 的临时 manifest
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    items = [{"url": url, "ts": ts, "mime": "text/html", "size": ""}]
    save_json(os.path.join(out, "manifest.json"), items)
    ns = argparse.Namespace(**vars(args))
    ns.domain = urlsplit(url).netloc
    ns.limit = None
    ns.latest = False
    ns.resume = False
    ns.from_year = None
    ns.to_year = None
    cmd_fetch(ns)


# ---------------------------------------------------------------- CLI

def main():
    ap = argparse.ArgumentParser(
        description="Wayback Machine 归档爬取工具：把历史快照抓成本地离线站",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="例：python wb_crawl.py fetch example.com --limit 20 --workers 4")
    sub = ap.add_subparsers(dest="cmd")

    def add_common(p):
        p.add_argument("domain", help="域名，如 example.com（可带路径前缀 blog.example.com）")
        p.add_argument("--limit", type=int, default=None, help="最多抓多少个 URL")
        p.add_argument("--latest", action="store_true",
                       help="每个 URL 取最新快照（默认取最早，速度更快）")
        p.add_argument("--from", dest="from_year", default=None, help="起始年份，如 2007")
        p.add_argument("--to", dest="to_year", default=None, help="结束年份，如 2019")
        p.add_argument("--delay", type=float, default=0.4,
                       help="两次请求的最小间隔秒数，默认 0.4；被限流就调大")
        p.add_argument("--workers", type=int, default=4, help="并发线程数，默认 4")
        p.add_argument("--proxy", default=None,
                       help="HTTP 代理，如 http://127.0.0.1:7890（部分地区访问 archive.org 需要）")
        p.add_argument("-o", "--out", default="site", help="输出目录，默认 site")

    p1 = sub.add_parser("list", help="只导出快照清单")
    add_common(p1)

    p2 = sub.add_parser("fetch", help="抓整站")
    add_common(p2)
    p2.add_argument("--pages-only", action="store_true", help="只抓 HTML，不下载图片/CSS")
    p2.add_argument("--no-resume", dest="resume", action="store_false",
                    help="不跳过已存在文件，全部重抓")
    p2.set_defaults(resume=True)

    p3 = sub.add_parser("page", help="抓单个页面")
    p3.add_argument("url", help="页面 URL")
    p3.add_argument("--ts", default=None, help="指定快照时间戳，如 20190101000000")
    p3.add_argument("--delay", type=float, default=0.4)
    p3.add_argument("--workers", type=int, default=4)
    p3.add_argument("--proxy", default=None, help="HTTP 代理，如 http://127.0.0.1:7890")
    p3.add_argument("-o", "--out", default="site")
    p3.add_argument("--pages-only", action="store_true")
    p3.set_defaults(resume=False, limit=None)

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return
    _throttle.delay = max(0.0, args.delay)
    if getattr(args, "proxy", None):
        _session.proxies.update({"http": args.proxy, "https": args.proxy})
    if getattr(args, "workers", 4) < 1:
        args.workers = 1
    if args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "fetch":
        cmd_fetch(args)
    else:
        cmd_page(args)


if __name__ == "__main__":
    main()
