# -*- coding: utf-8 -*-
"""阶段1：多关键词搜索，去重，输出候选视频清单。"""
import sys, os, re, json, time, hashlib, urllib.parse, requests
from pathlib import Path
sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool

OUT_DIR = Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\可控小成功与进度评判调研\原始数据\B站")
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROXY = {"http": "http://127.0.0.1:7892", "https": "http://127.0.0.1:7892"}

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,
         12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,
         57,62,11,36,20,34,44,52]

KEYWORDS = [
    # 进度/进步追踪
    "训练日志 健身", "健身 进步记录", "学习打卡 方法", "进度可视化", "进步追踪",
    # 小目标/小成功
    "微习惯", "小目标 自律", "小胜利 心理学", "渐进式进步", "积少成多 坚持",
    # 反馈系统
    "刻意练习 反馈", "即时反馈 训练", "动作反馈 健身", "反馈回路 学习",
    # 指标设计
    "前置指标 滞后指标", "leading indicator", "训练监控 RPE", "自主调节 训练",
    "RPE 健身", "训练容量 监控",
    # 方法论依赖
    "线性计划 健身", "5x5 力量训练", "三分化 训练", "训练计划 选择",
    # 虚假进步
    "垃圾容量 健身", "无效训练", "刷指标", "伪进步 健身", "练习不等于训练",
    "Goodhart 健身", "vanity metrics",
    # 测试频率
    "PR测试 频率", "力量举 测试周期", "段位测试", "定期测试 训练",
    # 自我构建
    "自己搭建 训练系统", "个人进步 追踪 系统", "训练 数据分析",
]

def make_session(cookie):
    s = requests.Session()
    s.proxies.update(PROXY)
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Cookie": cookie,
    })
    return s

def get_wbi_keys(s):
    nav = s.get("https://api.bilibili.com/x/web-interface/nav", timeout=20).json()
    wbi = nav["data"]["wbi_img"]
    img = wbi["img_url"].rsplit("/", 1)[-1].split(".")[0]
    sub = wbi["sub_url"].rsplit("/", 1)[-1].split(".")[0]
    return "".join((img + sub)[i] for i in MIXIN)[:32]

def sign(p, mixin):
    p = dict(p)
    p["wts"] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p["w_rid"] = hashlib.md5((q + mixin).encode()).hexdigest()
    return p

def clean(t):
    return re.sub(r"<[^>]+>", "", t or "")

def search_one(s, mixin, kw, page=1):
    p = sign({"search_type": "video", "keyword": kw, "page": page, "page_size": 30,
              "order": "totalrank"}, mixin)
    r = s.get("https://api.bilibili.com/x/web-interface/wbi/search/type",
              params=p, timeout=25)
    d = r.json()
    if d.get("code") != 0:
        return None, d.get("message")
    return d.get("data", {}).get("result") or [], None

def main():
    pool = BiliCookiePool()
    print(pool.status())
    cookie = pool.get_cookie()
    s = make_session(cookie)
    mixin = get_wbi_keys(s)
    print("[ok] wbi mixin ok")

    collected = {}  # bvid -> item
    kw_log = []
    for kw in KEYWORDS:
        try:
            res, err = search_one(s, mixin, kw, page=1)
            if err:
                print(f"[err] {kw}: {err}")
                kw_log.append({"kw": kw, "n": 0, "err": err})
                time.sleep(2)
                # 换账号重试一次
                cookie = pool.get_cookie()
                s = make_session(cookie)
                mixin = get_wbi_keys(s)
                continue
            n_new = 0
            for v in res:
                bv = v.get("bvid")
                if not bv: continue
                if bv in collected:
                    collected[bv]["_from_kw"].append(kw)
                    continue
                dur = v.get("duration", "0:0")
                # duration 是 "mm:ss" 或 "hh:mm:ss"
                parts = dur.split(":")
                try:
                    dsec = sum(int(x) * (60 ** i) for i, x in enumerate(reversed(parts)))
                except:
                    dsec = 0
                collected[bv] = {
                    "bvid": bv,
                    "title": clean(v.get("title")),
                    "author": v.get("author"),
                    "play": v.get("play", 0),
                    "duration": dur,
                    "dur_s": dsec,
                    "pubdate": v.get("pubdate"),
                    "description": clean(v.get("description", "")),
                    "_from_kw": [kw],
                }
                n_new += 1
            kw_log.append({"kw": kw, "n": len(res or []), "new": n_new})
            print(f"[ok] {kw}: {len(res or [])} 条, 新增 {n_new}")
        except Exception as e:
            print(f"[exc] {kw}: {e}")
            kw_log.append({"kw": kw, "n": 0, "err": str(e)})
        time.sleep(1.5)

    out = {"total_unique": len(collected), "keywords": kw_log, "videos": list(collected.values())}
    (OUT_DIR / "搜索清单.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] 去重后 {len(collected)} 个视频")

if __name__ == "__main__":
    main()
