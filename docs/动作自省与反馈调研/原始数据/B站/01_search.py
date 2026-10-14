# -*- coding: utf-8 -*-
"""B站搜索：动作自省与反馈主题。多关键词 wbi 搜索 -> 去重 -> 打分 -> 输出候选清单。"""
import sys, os, re, json, time, hashlib, urllib.parse, pathlib, random
import requests

sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool

OUT = pathlib.Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\动作自省与反馈调研\原始数据\B站")
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
    "健身 动作 复盘 录像",
    "自由重量 动作 自我纠正",
    "动作学习 运动技能",
    "本体感觉 训练",
    "深蹲 录像 对比",
    "卧推 动作 自查",
    "RPE 自测 训练",
    "RIR 留力",
    "健身 镜子 动作",
    "动作标准 渐进",
    "力量训练 神经适应",
    "发力感 念动一致",
    "motor learning feedback",
    "deliberate practice lifting",
    "健身 每组 纠错",
    "动作质量 评估",
    "单臂训练 本体感觉",
    "闭眼训练 健身",
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
    time.sleep(1.2)

# 打分
POS_KW = [
    ("复盘",5),("录像",4),("自查",5),("自我纠",6),("纠正",3),("纠错",5),
    ("本体感觉",6),("proprioception",6),("动作学习",5),("motor learning",5),
    ("神经适应",4),("念动",4),("发力感",3),("RPE",4),("RIR",4),
    ("深蹲",2),("卧推",2),("硬拉",2),("划船",2),("推举",2),
    ("自由重量",4),("镜子",3),("动作质量",5),("动作标准",3),
    ("渐进",2),("反馈",4),("刻意练习",6),("deliberate",6),
    ("对比",3),("视频",2),("训练日志",3),("进步",2),
]
def score(v):
    t = (v["title"] + " " + v["description"]).lower()
    sc = 0
    for k,w in POS_KW:
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
print("Top 20:")
for v in ranked[:20]:
    print(f"  {v['_score']:.1f}  {v['title'][:50]}  [{v['bvid']}] play={v['play']}")
