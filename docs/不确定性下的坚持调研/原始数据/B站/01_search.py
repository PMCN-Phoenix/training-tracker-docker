# -*- coding: utf-8 -*-
"""B站搜索：不确定性下的坚持/准备/复盘/学习主题。多关键词 wbi 搜索 -> 去重 -> 打分 -> 输出候选清单。"""
import sys, os, re, json, time, hashlib, urllib.parse, pathlib, random
import requests

sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool

OUT = pathlib.Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\不确定性下的坚持调研\原始数据\B站")
OUT.mkdir(parents=True, exist_ok=True)

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,
         12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,
         57,62,11,36,20,34,44,52]

pool = BiliCookiePool()
s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
})
s.headers["Cookie"] = pool.get_cookie()

# 拿 wbi key
nav = s.get("https://api.bilibili.com/x/web-interface/nav", timeout=20).json()
wbi = nav["data"]["wbi_img"]
img = wbi["img_url"].rsplit("/",1)[-1].split(".")[0]
sub = wbi["sub_url"].rsplit("/",1)[-1].split(".")[0]
MIXIN_KEY = "".join((img+sub)[i] for i in MIXIN)[:32]

def sign(p):
    p = dict(p); p["wts"] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p["w_rid"] = hashlib.md5((q + MIXIN_KEY).encode()).hexdigest()
    return p

def refresh_cookie():
    s.headers["Cookie"] = pool.get_cookie()

KEYWORDS = [
    # 1 动机与坚持
    "长期坚持 心态",
    "备考 坚持 心态",
    "长期主义 怎么做",
    "不放弃 备考",
    "意志力 消耗 心理学",
    # 2 成长型思维/自我效能
    "成长型思维",
    "自我效能感",
    "固定型思维 成长型思维",
    "自信 建立 心理学",
    # 3 复盘方法
    "复盘 方法 学习",
    "每日复盘 怎么做",
    "复盘的意义",
    # 4 过程 vs 结果
    "过程比结果重要",
    "享受过程",
    "过程目标",
    # 5 习惯养成
    "微习惯",
    "习惯养成 科学",
    "最小行动 习惯",
    # 6 反面/争议
    "沉没成本 放弃",
    "学会放弃",
    "过度坚持 倦怠",
    "burnout 倦怠",
    # 7 不确定性心理
    "不确定性 焦虑 学习",
    "控制感 心理学",
    "努力 意义 心理学",
    # 8 坚毅
    "坚毅 grit",
    "grit 心理学",
    "动机 心理学",
]

all_vids = {}
for kw in KEYWORDS:
    for attempt in range(3):
        try:
            p = sign({"search_type":"video","keyword":kw,"page":1,"page_size":30})
            r = s.get("https://api.bilibili.com/x/web-interface/wbi/search/type",
                      params=p, timeout=25)
            if r.status_code == 412 or '"code":-412' in r.text:
                pool.report_412(); refresh_cookie(); time.sleep(2.5*(attempt+1)); continue
            d = r.json()
            res = (d.get("data") or {}).get("result") or []
            pool.report_success()
            break
        except Exception as e:
            print("retry", kw, e); time.sleep(2)
    else:
        print("FAIL", kw); continue
    n = 0
    for v in res:
        if v.get("type") != "video": continue
        bvid = v.get("bvid")
        if not bvid: continue
        title = re.sub(r"<[^>]+>", "", v.get("title") or "")
        dur = v.get("duration") or ""
        # "mm:ss" or "hh:mm:ss"
        dur_s = 0
        parts = [int(x) for x in str(dur).split(":")]
        for x in parts: dur_s = dur_s*60 + x
        if bvid not in all_vids:
            all_vids[bvid] = {
                "bvid": bvid, "title": title, "author": v.get("author"),
                "play": v.get("play") or 0, "danmaku": v.get("video_review") or 0,
                "favorites": v.get("favorites") or 0, "duration": dur_s,
                "pubdate": v.get("pubdate"), "description": (v.get("description") or "")[:300],
                "kw_hit": [kw],
            }
            n += 1
        else:
            all_vids[bvid]["kw_hit"].append(kw)
    print(f"{kw}: +{n} new (total {len(all_vids)})")
    time.sleep(1.3)

# 打分：心理学/自我提升主题
POS_KW = [
    ("复盘",5),("反思",3),("日记",2),("长期主义",6),("长期坚持",5),("坚持",2),
    ("成长型思维",7),("固定型思维",6),("自我效能",7),("grit",6),("坚毅",5),
    ("过程",3),("结果",2),("享受过程",5),("微习惯",6),("习惯",3),("最小行动",5),
    ("沉没成本",6),("放弃",4),("倦怠",5),("burnout",5),("内耗",4),
    ("焦虑",3),("不确定性",5),("控制感",5),("归因",4),("自信",3),
    ("备考",3),("考研",3),("考公",3),("意志力",4),("动机",4),
    ("心理学",3),("认知",2),("学习",2),("方法",2),("进步",2),
    ("心态",3),("不放弃",4),("努力",2),("奖励",3),
]
NEG_KW = [
    ("直播",-4),("带货",-5),("广告",-3),("课程出售",-4),("报名",-3),
]
def score(v):
    t = (v["title"] + " " + v["description"]).lower()
    sc = 0
    for k,w in POS_KW:
        if k.lower() in t: sc += w
    for k,w in NEG_KW:
        if k.lower() in t: sc += w
    p = v["play"] or 0
    sc += 3 if p > 100000 else 2 if p > 30000 else 1 if p > 5000 else 0
    if v["duration"] < 90: sc -= 2
    if v["duration"] > 3600: sc -= 1
    sc += len(v["kw_hit"]) * 1.5
    return sc

ranked = sorted(all_vids.values(), key=score, reverse=True)
for v in ranked: v["_score"] = score(v)

(OUT / "搜索清单-原始.json").write_text(
    json.dumps(ranked, ensure_ascii=False, indent=2), encoding="utf-8")

# 输出 top 40 简表
lines = ["| rank | score | title | author | play | dur | kw_hit | bvid |",
         "|---|---|---|---|---|---|---|---|"]
for i,v in enumerate(ranked[:40], 1):
    lines.append(f"| {i} | {v['_score']:.1f} | {v['title'][:40]} | {v['author']} | {v['play']} | {v['duration']}s | {','.join(v['kw_hit'])} | {v['bvid']} |")
(OUT / "搜索清单-top40.md").write_text("\n".join(lines), encoding="utf-8")
print(f"\nTOTAL unique: {len(ranked)}")
print("Top 25:")
for v in ranked[:25]:
    print(f"  {v['_score']:.1f}  {v['title'][:50]}  [{v['bvid']}] play={v['play']} dur={v['duration']}s")
