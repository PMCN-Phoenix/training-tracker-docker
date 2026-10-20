# -*- coding: utf-8 -*-
"""EZ 杆 vs 哑铃弯举换算 · B站多关键词搜索与打分"""
import requests, time, json, re, hashlib, urllib.parse, sys, os

sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,
         12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,
         57,62,11,36,20,34,44,52]

OUT = r"D:\11.project\iwen-codex\codex-list\EZ杆哑铃换算-B站原始数据"
os.makedirs(OUT, exist_ok=True)

pool = BiliCookiePool()
s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
})

def login():
    s.headers["Cookie"] = pool.get_cookie()
    nav = s.get("https://api.bilibili.com/x/web-interface/nav", timeout=20).json()
    if nav.get("code") != 0 or not nav["data"].get("isLogin"):
        s.headers["Cookie"] = pool.get_cookie()
        nav = s.get("https://api.bilibili.com/x/web-interface/nav", timeout=20).json()
    w = nav["data"]["wbi_img"]
    img = w["img_url"].rsplit("/", 1)[-1].split(".")[0]
    sub = w["sub_url"].rsplit("/", 1)[-1].split(".")[0]
    return "".join((img + sub)[i] for i in MIXIN)[:32]

MIX = login()

def sign(p):
    p = dict(p); p["wts"] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p["w_rid"] = hashlib.md5((q + MIX).encode()).hexdigest()
    return p

KEYWORDS = [
    "EZ杆 哑铃 弯举 对比", "哑铃弯举 EZ杆 区别", "杠铃弯举 哑铃弯举 哪个好",
    "哑铃弯举 重量 换算", "杠铃 哑铃 重量换算", "弯举 重量 选择 新手",
    "EZ杆 和 直杆 区别", "二头弯举 用哑铃还是杠铃", "哑铃弯举 优点",
    "杠铃弯举 缺点", "哑铃 单臂 弯举 交替", "二头肌 训练 器械 选择",
    "哑铃弯举 教学", "弯举 1RM 测试", "barbell vs dumbbell curl",
]

def dur_s(t):
    try:
        parts = [int(x) for x in t.split(":")]
        return parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0] * 3600 + parts[1] * 60 + parts[2]
    except Exception:
        return 0

allv = {}
for i, kw in enumerate(KEYWORDS, 1):
    try:
        p = sign({"search_type": "video", "keyword": kw, "page": 1, "page_size": 30})
        r = s.get("https://api.bilibili.com/x/web-interface/wbi/search/type", params=p, timeout=25)
        if r.status_code == 412 or '"-412"' in r.text:
            pool.report_412(); time.sleep(5); continue
        pool.report_success()
        res = (r.json().get("data") or {}).get("result") or []
        n0 = len(allv)
        for v in res:
            if v.get("type") != "video":
                continue
            bv = v.get("bvid")
            if not bv:
                continue
            allv.setdefault(bv, {
                "bvid": bv,
                "title": re.sub(r"<[^>]+>", "", v.get("title", "")),
                "author": v.get("author", ""),
                "play": v.get("play") or 0,
                "danmaku": v.get("video_review") or 0,
                "duration": v.get("duration", ""),
                "pubdate": v.get("pubdate"),
                "desc": (v.get("description") or "")[:300],
                "kw": [],
            })
            allv[bv]["kw"].append(kw)
        print(f"[{i}/{len(KEYWORDS)}] {kw:<22} 结果 {len(res):>2} | 新增 {len(allv)-n0:>2} | 累计 {len(allv)}")
    except Exception as e:
        print(f"[{i}] {kw} ERR {type(e).__name__}: {e}")
    time.sleep(1.5)

print(f"\n去重后总数：{len(allv)}")

def score(v):
    t = (v["title"] + " " + v["desc"] + " " + v["author"]).lower()
    sc = 0.0
    for k, w in [("ez", 5), ("哑铃", 6), ("杠铃", 5), ("弯举", 5), ("二头", 4), ("bicep", 5),
                 ("对比", 5), ("区别", 5), ("换算", 7), ("选择", 3),
                 ("标准", 2.5), ("教学", 2), ("细节", 2), ("技巧", 2), ("错误", 2)]:
        if k in t:
            sc += w
    p = v["play"]
    sc += 3 if p > 500000 else 2 if p > 100000 else 1 if p > 30000 else -1.5
    d = dur_s(v["duration"])
    if d < 60: sc -= 2
    elif d > 480: sc -= 0.5
    if len(v["kw"]) >= 3: sc += 1.5
    return round(sc, 2)

for v in allv.values():
    v["score"] = score(v)

ranked = sorted(allv.values(), key=lambda x: -x["score"])
with open(os.path.join(OUT, "search_raw.json"), "w", encoding="utf-8") as f:
    json.dump(ranked, f, ensure_ascii=False, indent=1)

print("\n=== TOP 35 ===")
for v in ranked[:35]:
    print(f"{v['score']:>5} | {v['play']:>8} | {v['duration']:>7} | {v['bvid']} | {v['title'][:44]} | {v['author']}")
