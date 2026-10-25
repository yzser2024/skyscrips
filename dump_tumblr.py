#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用无头 Chromium 抓 ucaliy.tumblr.com 的全部帖子（含无限滚动加载的历史帖）。

输出到 out/：
  p01.html ...      每次滚动的页面快照
  posts.json        提取出的帖子（时间 + 文本 + HTML）
  body.txt          整页纯文本兜底
"""

import asyncio
import json
import os
import re
import sys

from playwright.async_api import async_playwright

BASE = "https://ucaliy.tumblr.com/"
OUT = "out"

EXTRACT_JS = r"""
() => {
  const sels = ['article', '.post', '.post-wrapper', 'li.post', 'div.post'];
  let best = [];
  for (const s of sels) {
    const n = Array.from(document.querySelectorAll(s));
    if (n.length > best.length) best = n;
  }
  const pick = (n, sel) => {
    const e = n.querySelector(sel);
    return e ? (e.getAttribute('datetime') || e.innerText || '') : '';
  };
  return best.map(n => ({
    time: pick(n, 'time') || pick(n, '[datetime]'),
    text: (n.innerText || '').replace(/\n{3,}/g, '\n\n').trim(),
    html: n.innerHTML || ''
  })).filter(x => x.text || x.html);
}
"""


async def main():
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = await browser.new_context(
            user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
            locale="en-US",
            viewport={"width": 1280, "height": 900},
            java_script_enabled=True,
        )
        page = await ctx.new_page()

        print("打开首页 ...", flush=True)
        resp = await page.goto(BASE, wait_until="domcontentloaded", timeout=90000)
        print("HTTP", resp.status if resp else "?", "| title:", await page.title(), flush=True)
        await page.wait_for_timeout(5000)

        # 等 Cloudflare 挑战过去：最多 30 秒，标题变了就继续
        for i in range(15):
            t = await page.title()
            if "just a moment" not in t.lower() and "checking" not in t.lower():
                break
            await page.wait_for_timeout(2000)
        print("挑战后 title:", await page.title(), flush=True)

        posts = []
        seen = set()

        def absorb(items):
            new = 0
            for it in items:
                key = (it.get("time", "") + (it.get("text", "") or "")[:100])
                if key in seen:
                    continue
                seen.add(key)
                posts.append(it)
                new += 1
            return new

        # 首屏
        absorb(await page.evaluate(EXTRACT_JS))
        await page.screenshot(path=os.path.join(OUT, "shot1.png"), full_page=False)
        open(os.path.join(OUT, "p01.html"), "w", encoding="utf-8").write(await page.content())

        # 无限滚动
        prev_h = 0
        same = 0
        for round_no in range(1, 61):
            try:
                h = await page.evaluate("document.body.scrollHeight")
            except Exception:
                break
            if h == prev_h:
                same += 1
                if same >= 3:
                    print("高度不再增长，停止滚动", flush=True)
                    break
                await page.wait_for_timeout(2500)
                continue
            same = 0
            prev_h = h
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2500)
            new = absorb(await page.evaluate(EXTRACT_JS))
            print("滚动 %2d | 高度 %6d | 新增 %2d | 累计 %3d"
                  % (round_no, h, new, len(posts)), flush=True)
            if round_no % 10 == 0:
                open(os.path.join(OUT, "p%02d.html" % (round_no // 10 + 1)),
                     "w", encoding="utf-8").write(await page.content())

        # 分页兜底（有些主题是 /page/N 而不是无限滚动）
        for i in range(2, 16):
            try:
                r = await page.goto(BASE + "page/%d" % i, wait_until="domcontentloaded", timeout=60000)
            except Exception:
                break
            if not r or r.status >= 400:
                print("page/%d → HTTP %s，停止" % (i, r.status if r else "?"), flush=True)
                break
            await page.wait_for_timeout(3000)
            new = absorb(await page.evaluate(EXTRACT_JS))
            print("page/%d | 新增 %2d | 累计 %3d" % (i, new, len(posts)), flush=True)
            if new == 0:
                break

        # 兜底：整页文本
        try:
            body = await page.evaluate("document.body.innerText")
            open(os.path.join(OUT, "body.txt"), "w", encoding="utf-8").write(body or "")
        except Exception:
            pass

        json.dump(posts, open(os.path.join(OUT, "posts.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("总计 %d 条" % len(posts), flush=True)
        await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("失败:", repr(e), flush=True)
        sys.exit(1)
