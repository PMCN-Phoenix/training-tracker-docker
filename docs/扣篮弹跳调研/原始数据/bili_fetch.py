# -*- coding: utf-8 -*-
"""
B 站深蹲/弹跳/扣篮主题调研：搜索 -> 打分 -> 精选 -> 拿 aid/cid -> 抓 AI 字幕
"""
import os, sys, re, json, time, urllib.parse, hashlib, pathlib

ROOT = pathlib.Path(r"D:\11.project\iwen-codex\codex-list\training-tracker-docker\docs\扣篮弹跳调研\原始数据\B站")
ROOT.mkdir(parents=True, exist_ok=True)

# 复用 cookie 池
sys.path.insert(0, r"D:\11.project\iwen-codex\bilibili-cookies")
from cookie_manager import BiliCookiePool
import requests

MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,
         12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,
         57,62,11,36,20,34,44,52]

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
pool = BiliCookiePool()

def refresh_cookie():
    s.headers["Cookie"] = pool.get_cookie()

refresh_cookie()

# 拿 wbi img/sub
nav = s.get("https://api.bilibili.com/x/web-interface/nav", timeout=20).json()
wbi = nav["data"]["wbi_img"]
img = wbi["img_url"].rsplit("/", 1)[-1].split(".")[0]
sub = wbi["sub_url"].rsplit("/", 1)[-1].split(".")[0]
MIXIN_KEY = "".join((img + sub)[i] for i in MIXIN)[:32]

def sign(p):
    p = dict(p)
    p["wts"] = str(int(time.time()))
    q = urllib.parse.urlencode(sorted(p.items()))
    p["w_rid"] = hashlib.md5((q + MIXIN_KEY).encode()).hexdigest()
    return p

KEYWORDS = [
    "弹跳训练", "垂直纵跳", "扣篮训练", "深蹲转爆发", "力量翻 教学",
    "高翻 教学", "深度跳 训练", "箱跳 训练", "蹲跳 训练",
    "纵跳 训练计划", "弹跳 科学", "plyometric 中文", "深蹲 1RM 弹跳",
    "助跑摸高 训练", "原地摸高 训练"
]

def search_kw(kw, pages=2):
    out = []
    for pn in range(1, pages+1):
        for attempt in range(3):
            try:
                q = sign({"search_type": "video", "keyword": kw, "page": pn, "page_size": 30})
                r = s.get("https://api.bilibili.com/x/web-interface/wbi/search/type",
                          params=q, timeout=25)
                if r.status_code == 412 or '"code":-412' in r.text:
                    pool.report_412(); refresh_cookie(); time.sleep(2.5); continue
                d = r.json()
                results = (d.get("data") or {}).get("result") or []
                for v in results:
                    out.append({
                        "bvid": v.get("bvid"),
                        "title": re.sub(r"<[^>]+>", "", v.get("title") or ""),
                        "author": v.get("author"),
                        "play": v.get("play") or 0,
                        "duration": v.get("duration") or "",
                        "pubdate": v.get("pubdate"),
                        "desc": (v.get("description") or "")[:200],
                        "_kw": kw
                    })
                break
            except Exception as e:
                print(f"  search err {kw} p{pn} try{attempt}: {e}")
                time.sleep(2)
        time.sleep(1.2)
    return out

print("=== 开始搜索 ===")
all_videos = {}
for kw in KEYWORDS:
    print(f"搜索: {kw}")
    vs = search_kw(kw, pages=2)
    print(f"  -> {len(vs)} 条")
    for v in vs:
        if v["bvid"]:
            all_videos[v["bvid"]] = v

print(f"\n去重后: {len(all_videos)} 个视频")

# 打分
KEY_POS = [("扣篮",8),("弹跳",8),("纵跳",8),("深蹲",6),("爆发",6),("高翻",5),("力量翻",5),
           ("深度跳",5),("箱跳",4),("助跑",3),("摸高",5),("plyometric",6),("垂直",4)]
NEG = ["教学 入门","减脂","瑜伽","拉伸放松","小姐姐"]

def score(v):
    t = (v["title"] + " " + v["desc"]).lower()
    sc = 0
    for k,w in KEY_POS:
        if k.lower() in t: sc += w
    for k in NEG:
        if k.lower() in t: sc -= 3
    p = v["play"] or 0
    if p > 200000: sc += 3
    elif p > 50000: sc += 2
    elif p > 10000: sc += 1
    # 时长：解析 mm:ss
    d = v["duration"]
    try:
        if ":" in d:
            parts = d.split(":")
            sec = int(parts[0])*60 + int(parts[1]) if len(parts)==2 else int(parts[0])*3600+int(parts[1])*60+int(parts[2])
            if sec < 60: sc -= 2
            elif sec > 1800: sc += 1.5  # 长视频信息量高
    except: pass
    return sc

ranked = sorted(all_videos.values(), key=score, reverse=True)
for v in ranked[:25]:
    v["_score"] = score(v)

# 保存搜索清单
with open(ROOT / "搜索清单.json", "w", encoding="utf-8") as f:
    json.dump(ranked, f, ensure_ascii=False, indent=2)

print("\n=== Top 25 ===")
for v in ranked[:25]:
    print(f"[{v['_score']:.1f}] {v['bvid']} | {v['title'][:40]} | play={v['play']} | {v['duration']}")

# 选 top 15
PICKS = ranked[:15]

# 拿 aid/cid（网页 HTML）
def get_aid_cid(bvid):
    url = f"https://www.bilibili.com/video/{bvid}/"
    for attempt in range(3):
        try:
            r = s.get(url, headers={"Referer": "https://www.bilibili.com/"}, timeout=25)
            t = r.text
            m = (re.search(r'window\.__INITIAL_STATE__=(.*?);\(function', t, re.S)
                 or re.search(r'window\.__INITIAL_STATE__=(.*?);\s*</script>', t, re.S))
            if not m:
                return None
            vd = json.loads(m.group(1))["videoData"]
            return {
                "aid": vd["aid"],
                "cid": vd["cid"],
                "title": vd["title"],
                "owner": vd["owner"]["name"],
                "duration": vd["duration"],
                "desc": vd.get("desc","")[:500],
                "pages": [{"cid": p["cid"], "part": p.get("part",""), "duration": p.get("duration",0)} for p in vd.get("pages",[])]
            }
        except Exception as e:
            print(f"  aid/cid err {bvid}: {e}")
            time.sleep(2)
    return None

print("\n=== 拿 aid/cid + 抓字幕 ===")
results = {}
for v in PICKS:
    bv = v["bvid"]
    info = get_aid_cid(bv)
    if not info:
        print(f"  ! {bv} 拿不到 aid/cid")
        continue
    print(f"\n[{bv}] {info['title'][:40]} | aid={info['aid']} cid={info['cid']} | dur={info['duration']}s")

    # 抓字幕（每 P）
    subs_all = []
    pages = info["pages"] if len(info["pages"])>1 else [{"cid": info["cid"], "part": "P1", "duration": info["duration"]}]
    for pg in pages:
        cid = pg["cid"]
        for attempt in range(4):
            try:
                q = sign({"bvid": bv, "cid": str(cid), "web_location": "333.1007"})
                r = s.get("https://api.bilibili.com/x/player/wbi/v2",
                          params=q,
                          headers={"Referer": f"https://www.bilibili.com/video/{bv}/"},
                          timeout=20)
                if r.status_code == 412:
                    pool.report_412(); refresh_cookie(); time.sleep(3); continue
                d = r.json()
                sub_list = ((d.get("data") or {}).get("subtitle") or {}).get("subtitles") or []
                if not sub_list:
                    break
                # 选语言
                pick = None
                for pref in ["zh-Hans","zh-CN","zh","ai-zh"]:
                    for x in sub_list:
                        if x.get("lan")==pref:
                            pick = x; break
                    if pick: break
                if not pick:
                    pick = sub_list[0]
                u = pick.get("subtitle_url") or ""
                if not u:
                    time.sleep(4); continue
                if u.startswith("//"): u = "https:"+u
                body = s.get(u, headers={"Referer": f"https://www.bilibili.com/video/{bv}/"}, timeout=25).json().get("body",[])
                subs_all.append({"part": pg.get("part","P1"), "lang": pick.get("lan"), "segments": body})
                print(f"    P {pg.get('part','?')}: {len(body)} 段字幕")
                break
            except Exception as e:
                print(f"    sub err try{attempt}: {e}")
                time.sleep(3)
        time.sleep(1.5)

    results[bv] = {"meta": v, "info": info, "subs": subs_all}
    # 落盘单文件
    with open(ROOT / f"{bv}.json", "w", encoding="utf-8") as f:
        json.dump(results[bv], f, ensure_ascii=False, indent=2)

with open(ROOT / "_summary.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n=== 完成 ===")
print(f"共抓 {len(results)} 个视频")
for bv, r in results.items():
    total_seg = sum(len(s['segments']) for s in r['subs'])
    print(f"  {bv} | {r['info']['title'][:35]} | 字幕段数={total_seg}")
